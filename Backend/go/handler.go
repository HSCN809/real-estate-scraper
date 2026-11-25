package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"math/rand"
	"net"
	"net/http"
	"net/url"
	"strings"
	"sync"
	"time"

	"github.com/rs/zerolog/log"
)

// ProxyHandler handles incoming proxy requests
type ProxyHandler struct {
	config     *Config
	clientPool *ClientPool
	tlsManager *TLSFingerprintManager

	// Rate limiting
	rateLimiter *RateLimiter

	// Allowed origins for CORS
	allowedOrigins []string
}

// RateLimiter implements token bucket rate limiting
type RateLimiter struct {
	mu      sync.Mutex
	tokens  map[string]*tokenBucket
	rate    int           // requests per second
	burst   int           // max burst size
	cleanup time.Duration // cleanup interval
}

type tokenBucket struct {
	tokens    float64
	lastTime  time.Time
	maxTokens float64
}

// NewRateLimiter creates a new rate limiter
func NewRateLimiter(rate int, burst int) *RateLimiter {
	rl := &RateLimiter{
		tokens:  make(map[string]*tokenBucket),
		rate:    rate,
		burst:   burst,
		cleanup: 5 * time.Minute,
	}

	// Start cleanup goroutine
	go rl.cleanupExpired()

	return rl
}

// Allow checks if a request from the given IP is allowed
func (rl *RateLimiter) Allow(ip string) bool {
	rl.mu.Lock()
	defer rl.mu.Unlock()

	bucket, exists := rl.tokens[ip]
	if !exists {
		bucket = &tokenBucket{
			tokens:    float64(rl.burst),
			lastTime:  time.Now(),
			maxTokens: float64(rl.burst),
		}
		rl.tokens[ip] = bucket
	}

	// Add tokens based on elapsed time
	now := time.Now()
	elapsed := now.Sub(bucket.lastTime).Seconds()
	bucket.tokens += elapsed * float64(rl.rate)
	if bucket.tokens > bucket.maxTokens {
		bucket.tokens = bucket.maxTokens
	}
	bucket.lastTime = now

	// Check if request is allowed
	if bucket.tokens >= 1 {
		bucket.tokens--
		return true
	}

	return false
}

// cleanupExpired removes expired entries
func (rl *RateLimiter) cleanupExpired() {
	ticker := time.NewTicker(rl.cleanup)
	defer ticker.Stop()

	for range ticker.C {
		rl.mu.Lock()
		now := time.Now()
		for ip, bucket := range rl.tokens {
			if now.Sub(bucket.lastTime) > 10*time.Minute {
				delete(rl.tokens, ip)
			}
		}
		rl.mu.Unlock()
	}
}

// NewProxyHandler creates a new proxy handler
func NewProxyHandler(cfg *Config, pool *ClientPool, tlsManager *TLSFingerprintManager) *ProxyHandler {
	return &ProxyHandler{
		config:      cfg,
		clientPool:  pool,
		tlsManager:  tlsManager,
		rateLimiter: NewRateLimiter(cfg.RateLimit, cfg.RateLimitBurst),
		allowedOrigins: []string{
			"http://localhost:3000",
			"http://127.0.0.1:3000",
			"http://real-estate-frontend:3000",
			"http://localhost:8000",
			"http://real-estate-api:8000",
		},
	}
}

// ProxyRequest represents an incoming proxy request
type ProxyRequest struct {
	URL     string            `json:"url"`
	Method  string            `json:"method,omitempty"`
	Headers map[string]string `json:"headers,omitempty"`
	Body    []byte            `json:"body,omitempty"`
	Timeout int               `json:"timeout,omitempty"`
}

// ProxyResponse represents the proxy response
type ProxyResponse struct {
	Status     int               `json:"status"`
	Headers    map[string]string `json:"headers"`
	Body       []byte            `json:"body"`
	Cookies    []http.Cookie     `json:"cookies,omitempty"`
	StatusCode string            `json:"status_code,omitempty"`
	Error      string            `json:"error,omitempty"`
}

// ServeHTTP handles incoming HTTP requests
func (ph *ProxyHandler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	// Get client IP for rate limiting
	clientIP := getClientIP(r)

	// Rate limiting check
	if !ph.rateLimiter.Allow(clientIP) {
		log.Warn().Str("ip", clientIP).Msg("Rate limit exceeded")
		ph.sendErrorResponse(w, "Rate limit exceeded. Please try again later.", http.StatusTooManyRequests)
		return
	}

	// CORS: Check origin and set appropriate headers
	origin := r.Header.Get("Origin")
	if origin != "" && ph.isOriginAllowed(origin) {
		w.Header().Set("Access-Control-Allow-Origin", origin)
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization, X-API-Key")
		w.Header().Set("Access-Control-Allow-Credentials", "true")
		w.Header().Set("Access-Control-Max-Age", "86400")
	}

	// Handle OPTIONS preflight
	if r.Method == "OPTIONS" {
		w.WriteHeader(http.StatusOK)
		return
	}

	// Health endpoint for Docker healthcheck (no auth required)
	if r.URL.Path == "/" {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		w.Write([]byte(`{"status":"ok","service":"invisible-proxy"}`))
		return
	}

	// API key authentication for proxy endpoint
	if r.URL.Path == "/proxy" {
		if !ph.authenticateRequest(r) {
			log.Warn().Str("ip", clientIP).Msg("Unauthorized proxy request")
			ph.sendErrorResponse(w, "Unauthorized. Valid API key required.", http.StatusUnauthorized)
			return
		}
	}

	// Proxy endpoint guard
	if r.URL.Path != "/proxy" {
		http.NotFound(w, r)
		return
	}

	// Route based on method
	switch r.Method {
	case "GET":
		ph.handleGetProxy(w, r)
	case "POST":
		ph.handlePostProxy(w, r)
	default:
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
	}
}

// isOriginAllowed checks if the origin is in the allowed list
func (ph *ProxyHandler) isOriginAllowed(origin string) bool {
	for _, allowed := range ph.allowedOrigins {
		if origin == allowed {
			return true
		}
	}
	return false
}

// authenticateRequest validates the API key
func (ph *ProxyHandler) authenticateRequest(r *http.Request) bool {
	if ph.config.APIKey == "" {
		return false
	}

	// Check X-API-Key header
	apiKey := r.Header.Get("X-API-Key")
	if apiKey != "" {
		return apiKey == ph.config.APIKey
	}

	// Check query parameter
	apiKey = r.URL.Query().Get("api_key")
	if apiKey != "" {
		return apiKey == ph.config.APIKey
	}

	return false
}

// getClientIP extracts the client IP from the request
func getClientIP(r *http.Request) string {
	// Check X-Forwarded-For header
	xff := r.Header.Get("X-Forwarded-For")
	if xff != "" {
		parts := strings.Split(xff, ",")
		return strings.TrimSpace(parts[0])
	}

	// Check X-Real-IP header
	xri := r.Header.Get("X-Real-IP")
	if xri != "" {
		return xri
	}

	// Fall back to RemoteAddr
	parts := strings.Split(r.RemoteAddr, ":")
	if len(parts) > 1 {
		return strings.Join(parts[:len(parts)-1], ":")
	}
	return r.RemoteAddr
}

var allowedProxyHosts = []string{
	"hepsiemlak.com",
	"emlakjet.com",
}

func normalizeProxyHost(host string) string {
	host = strings.ToLower(strings.TrimSpace(host))
	host = strings.TrimSuffix(host, ".")
	if parsed, _, err := net.SplitHostPort(host); err == nil {
		host = parsed
	}
	return strings.Trim(host, "[]")
}

func isAllowedProxyHost(host string) bool {
	host = normalizeProxyHost(host)
	for _, allowed := range allowedProxyHosts {
		if host == allowed || strings.HasSuffix(host, "."+allowed) {
			return true
		}
	}
	return false
}

func validateTargetURL(raw string) error {
	parsed, err := url.Parse(raw)
	if err != nil || parsed.Host == "" || parsed.Opaque != "" {
		return fmt.Errorf("invalid url")
	}
	if parsed.Scheme != "https" {
		return fmt.Errorf("only https targets are allowed")
	}
	if parsed.User != nil {
		return fmt.Errorf("userinfo is not allowed")
	}
	hostname := parsed.Hostname()
	if hostname == "" || net.ParseIP(hostname) != nil {
		return fmt.Errorf("host is not allowed")
	}
	if !isAllowedProxyHost(hostname) {
		return fmt.Errorf("host is not allowed")
	}
	return nil
}

// handleGetProxy handles GET requests with URL query parameter
func (ph *ProxyHandler) handleGetProxy(w http.ResponseWriter, r *http.Request) {
	targetURL := r.URL.Query().Get("url")
	if targetURL == "" {
		http.Error(w, "Missing 'url' parameter", http.StatusBadRequest)
		return
	}

	req := ProxyRequest{
		URL:     targetURL,
		Method:  "GET",
		Timeout: int(ph.config.ReadTimeout.Milliseconds() / 1000),
	}

	// Copy headers from request
	if headers := extractHeaders(r); len(headers) > 0 {
		req.Headers = headers
	}

	if err := validateTargetURL(req.URL); err != nil {
		ph.sendErrorResponse(w, err.Error(), http.StatusBadRequest)
		return
	}

	ph.executeProxyRequest(w, r.Context(), req)
}

// handlePostProxy handles POST requests with JSON body
func (ph *ProxyHandler) handlePostProxy(w http.ResponseWriter, r *http.Request) {
	var req ProxyRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, fmt.Sprintf("Invalid JSON: %v", err), http.StatusBadRequest)
		return
	}

	// Set default method if not provided
	if req.Method == "" {
		req.Method = "POST"
	}

	// Set default timeout if not provided
	if req.Timeout == 0 {
		req.Timeout = int(ph.config.ReadTimeout.Milliseconds() / 1000)
	}

	if err := validateTargetURL(req.URL); err != nil {
		ph.sendErrorResponse(w, err.Error(), http.StatusBadRequest)
		return
	}

	ph.executeProxyRequest(w, r.Context(), req)
}

// executeProxyRequest executes the actual proxy request with retry logic
func (ph *ProxyHandler) executeProxyRequest(w http.ResponseWriter, ctx context.Context, req ProxyRequest) {
	var lastError error

	// One client for every attempt, and for later calls that send the same
	// X-Proxy-Session, so the cookie jar keeps __cf_bm.
	session := proxySessionID(req.Headers)
	pooled := ph.clientPool.Acquire(session)
	client := pooled.Client
	defer ph.clientPool.Release(session, pooled)

	var held *http.Response
	var heldBody []byte
	sendHeld := func() bool {
		if heldBody == nil {
			return false
		}
		ph.sendSuccessResponse(w, held, heldBody)
		return true
	}

	// Retry logic
	for attempt := 0; attempt <= ph.config.MaxRetries; attempt++ {
		if attempt > 0 {
			log.Debug().Msgf("Retry attempt %d for URL: %s", attempt, req.URL)
			jitter := time.Duration(rand.Intn(400)) * time.Millisecond
			if !sleepWithContext(ctx, ph.config.RetryDelay+jitter) {
				if sendHeld() {
					return
				}
				ph.sendErrorResponse(w, ctx.Err().Error(), http.StatusGatewayTimeout)
				return
			}
		}

		// Create HTTP request
		httpReq, err := ph.createHTTPRequest(&req, pooled.UserAgent)
		if err != nil {
			lastError = err
			continue
		}

		// Execute request with context
		httpReq = httpReq.WithContext(ctx)
		resp, err := client.Do(httpReq)

		if err != nil {
			lastError = err
			if ph.shouldRetry(err) && attempt < ph.config.MaxRetries {
				log.Warn().Err(err).Msgf("Request failed, retrying (attempt %d/%d)", attempt+1, ph.config.MaxRetries)
				continue
			}
			log.Error().Err(err).Msgf("Request failed for URL: %s", req.URL)
			if sendHeld() {
				return
			}
			ph.sendErrorResponse(w, err.Error(), http.StatusBadGateway)
			return
		}

		// Read response body
		body, err := io.ReadAll(resp.Body)
		resp.Body.Close()

		if err != nil {
			lastError = err
			log.Error().Err(err).Msg("Failed to read response body")
			if sendHeld() {
				return
			}
			ph.sendErrorResponse(w, err.Error(), http.StatusInternalServerError)
			return
		}

		// 403/503 and a 200 interstitial are the same failure. Retry on this
		// client so its cookie jar keeps __cf_bm. A later transport error still
		// returns this body. The last attempt is returned as a normal body.
		if isCloudflareChallenge(resp.StatusCode, body) && attempt < ph.config.MaxRetries {
			log.Warn().Int("status", resp.StatusCode).Msgf("Challenge response for %s, retrying with same session (attempt %d/%d)", req.URL, attempt+1, ph.config.MaxRetries)
			held = &http.Response{StatusCode: resp.StatusCode, Header: resp.Header.Clone()}
			heldBody = append([]byte(nil), body...)
			jitter := time.Duration(rand.Intn(600)) * time.Millisecond
			if !sleepWithContext(ctx, ph.config.RetryDelay*time.Duration(attempt+1)+jitter) {
				sendHeld()
				return
			}
			continue
		}

		// Success! Send response back
		ph.sendSuccessResponse(w, resp, body)
		return
	}

	if sendHeld() {
		return
	}

	// All retries failed
	log.Error().Err(lastError).Msgf("All retries failed for URL: %s", req.URL)
	ph.sendErrorResponse(w, fmt.Sprintf("All retries failed: %v", lastError), http.StatusBadGateway)
}

// createHTTPRequest creates an HTTP request from ProxyRequest. The userAgent
// parameter is always applied last so it matches the pooled client's TLS
// fingerprint.
func (ph *ProxyHandler) createHTTPRequest(req *ProxyRequest, userAgent string) (*http.Request, error) {
	httpReq, err := http.NewRequest(req.Method, req.URL, bytes.NewReader(req.Body))
	if err != nil {
		return nil, err
	}

	effectiveUA := ph.config.UserAgent
	if userAgent != "" {
		effectiveUA = userAgent
	}

	// Set default headers
	httpReq.Header.Set("User-Agent", effectiveUA)
	httpReq.Header.Set("Accept", ph.config.AcceptHeader)
	httpReq.Header.Set("Accept-Language", ph.config.AcceptLanguage)
	httpReq.Header.Set("Connection", "keep-alive")
	httpReq.Header.Set("Upgrade-Insecure-Requests", "1")

	// Set Client Hints and Fetch Metadata when user-agent is Chrome
	if strings.Contains(effectiveUA, "Chrome") {
		chromeVer := "133"
		if strings.Contains(effectiveUA, "Chrome/131") {
			chromeVer = "131"
		} else if strings.Contains(effectiveUA, "Chrome/120") {
			chromeVer = "120"
		}
		httpReq.Header.Set("sec-ch-ua", fmt.Sprintf(`"Not(A:Brand";v="99", "Google Chrome";v="%s", "Chromium";v="%s"`, chromeVer, chromeVer))
		httpReq.Header.Set("sec-ch-ua-mobile", "?0")
		httpReq.Header.Set("sec-ch-ua-platform", `"Windows"`)
	}

	httpReq.Header.Set("Sec-Fetch-Dest", "document")
	httpReq.Header.Set("Sec-Fetch-Mode", "navigate")
	httpReq.Header.Set("Sec-Fetch-Site", "none")
	httpReq.Header.Set("Sec-Fetch-User", "?1")

	// Set custom headers
	for key, value := range req.Headers {
		// Keep Host and Accept-Encoding under proxy control.
		if strings.EqualFold(key, "Host") || strings.EqualFold(key, "Accept-Encoding") || strings.EqualFold(key, "X-Proxy-Session") {
			continue
		}
		httpReq.Header.Set(key, value)
	}

	// Always override the User-Agent with the fingerprint-matched one.
	if userAgent != "" {
		httpReq.Header.Set("User-Agent", userAgent)
	}

	return httpReq, nil
}

// sendSuccessResponse sends a successful response back to the client
func (ph *ProxyHandler) sendSuccessResponse(w http.ResponseWriter, resp *http.Response, body []byte) {
	cookies := resp.Cookies()
	// Create proxy response
	proxyResp := ProxyResponse{
		Status:  resp.StatusCode,
		Body:    body,
		Cookies: make([]http.Cookie, 0, len(cookies)),
		Headers: make(map[string]string, len(resp.Header)),
	}

	// Copy cookies manually
	for _, cookie := range cookies {
		proxyResp.Cookies = append(proxyResp.Cookies, *cookie)
	}

	// Copy headers
	for key, values := range resp.Header {
		if len(values) > 0 {
			proxyResp.Headers[key] = values[0]
		}
	}

	// Add status code as string for easy access
	proxyResp.StatusCode = http.StatusText(resp.StatusCode)

	// Send JSON response
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(proxyResp)
}

// sendErrorResponse sends an error response back to the client
func (ph *ProxyHandler) sendErrorResponse(w http.ResponseWriter, errorMsg string, statusCode int) {
	proxyResp := ProxyResponse{
		Status: statusCode,
		Error:  errorMsg,
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(statusCode)
	json.NewEncoder(w).Encode(proxyResp)
}

func proxySessionID(headers map[string]string) string {
	for key, value := range headers {
		if strings.EqualFold(key, "X-Proxy-Session") {
			return strings.TrimSpace(value)
		}
	}
	return ""
}

const maxCFChallengeScanBytes = 32 * 1024

var cfChallengeMarkers = []string{
	"cf-challenge",
	"challenge-platform",
	"just a moment",
	"checking your browser",
	"attention required",
	"cf-turnstile",
	"/cdn-cgi/challenge-platform/",
}

func sleepWithContext(ctx context.Context, d time.Duration) bool {
	if d <= 0 {
		return ctx.Err() == nil
	}
	timer := time.NewTimer(d)
	defer timer.Stop()
	select {
	case <-ctx.Done():
		return false
	case <-timer.C:
		return true
	}
}

func containsFoldASCII(haystack []byte, lowerNeedle string) bool {
	n := len(lowerNeedle)
	if n == 0 || len(haystack) < n {
		return false
	}
	first := lowerNeedle[0]
	limit := len(haystack) - n
	for i := 0; i <= limit; i++ {
		c := haystack[i]
		if c >= 'A' && c <= 'Z' {
			c += 'a' - 'A'
		}
		if c != first {
			continue
		}
		matched := true
		for j := 1; j < n; j++ {
			hc := haystack[i+j]
			if hc >= 'A' && hc <= 'Z' {
				hc += 'a' - 'A'
			}
			if hc != lowerNeedle[j] {
				matched = false
				break
			}
		}
		if matched {
			return true
		}
	}
	return false
}

func isCloudflareChallenge(status int, body []byte) bool {
	if status == http.StatusForbidden || status == http.StatusServiceUnavailable {
		return true
	}
	if status != http.StatusOK || len(body) == 0 {
		return false
	}
	sample := body
	if len(sample) > maxCFChallengeScanBytes {
		sample = sample[:maxCFChallengeScanBytes]
	}
	for _, marker := range cfChallengeMarkers {
		if containsFoldASCII(sample, marker) {
			return true
		}
	}
	return false
}

// shouldRetry determines if an error warrants a retry
func (ph *ProxyHandler) shouldRetry(err error) bool {
	if !ph.config.RetryOnTimeout {
		return false
	}

	// Check if error is timeout-related
	errStr := err.Error()
	return strings.Contains(errStr, "timeout") ||
		strings.Contains(errStr, "deadline") ||
		strings.Contains(errStr, "connection refused")
}

// extractHeaders extracts headers from the incoming request
func extractHeaders(r *http.Request) map[string]string {
	headers := make(map[string]string)

	// Extract relevant headers
	extractHeader := func(name string) {
		if val := r.Header.Get(name); val != "" {
			headers[name] = val
		}
	}

	extractHeader("X-Custom-Header")
	extractHeader("Authorization")
	extractHeader("Cookie")

	return headers
}
