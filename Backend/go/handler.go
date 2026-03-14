package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"

	"github.com/rs/zerolog/log"
)

// ProxyHandler handles incoming proxy requests
type ProxyHandler struct {
	config     *Config
	clientPool *ClientPool
	tlsManager *TLSFingerprintManager
}

// NewProxyHandler creates a new proxy handler
func NewProxyHandler(cfg *Config, pool *ClientPool, tlsManager *TLSFingerprintManager) *ProxyHandler {
	return &ProxyHandler{
		config:     cfg,
		clientPool: pool,
		tlsManager: tlsManager,
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
	// Add CORS headers for cross-origin requests
	w.Header().Set("Access-Control-Allow-Origin", "*")
	w.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
	w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")

	// Handle OPTIONS preflight
	if r.Method == "OPTIONS" {
		w.WriteHeader(http.StatusOK)
		return
	}

	// Health endpoint for Docker healthcheck
	if r.URL.Path == "/" {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		w.Write([]byte(`{"status":"ok","service":"invisible-proxy"}`))
		return
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

// handleGetProxy handles GET requests with URL query parameter
func (ph *ProxyHandler) handleGetProxy(w http.ResponseWriter, r *http.Request) {
	targetURL := r.URL.Query().Get("url")
	if targetURL == "" {
		http.Error(w, "Missing 'url' parameter", http.StatusBadRequest)
		return
	}

	req := ProxyRequest{
		URL:    targetURL,
		Method: "GET",
		Timeout: int(ph.config.ReadTimeout.Milliseconds() / 1000),
	}

	// Copy headers from request
	if headers := extractHeaders(r); len(headers) > 0 {
		req.Headers = headers
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

	ph.executeProxyRequest(w, r.Context(), req)
}

// executeProxyRequest executes the actual proxy request with retry logic
func (ph *ProxyHandler) executeProxyRequest(w http.ResponseWriter, ctx context.Context, req ProxyRequest) {
	var lastError error

	// Retry logic
	for attempt := 0; attempt <= ph.config.MaxRetries; attempt++ {
		if attempt > 0 {
			log.Debug().Msgf("Retry attempt %d for URL: %s", attempt, req.URL)
			time.Sleep(ph.config.RetryDelay)
		}

		// Get client from pool
		client := ph.clientPool.GetClient()

		// Create HTTP request
		httpReq, err := ph.createHTTPRequest(&req)
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
			ph.sendErrorResponse(w, err.Error(), http.StatusBadGateway)
			return
		}

		// Read response body
		body, err := io.ReadAll(resp.Body)
		resp.Body.Close()

		if err != nil {
			lastError = err
			log.Error().Err(err).Msg("Failed to read response body")
			ph.sendErrorResponse(w, err.Error(), http.StatusInternalServerError)
			return
		}

		// Success! Send response back
		ph.sendSuccessResponse(w, resp, body)
		return
	}

	// All retries failed
	log.Error().Err(lastError).Msgf("All retries failed for URL: %s", req.URL)
	ph.sendErrorResponse(w, fmt.Sprintf("All retries failed: %v", lastError), http.StatusBadGateway)
}

// createHTTPRequest creates an HTTP request from ProxyRequest
func (ph *ProxyHandler) createHTTPRequest(req *ProxyRequest) (*http.Request, error) {
	httpReq, err := http.NewRequest(req.Method, req.URL, bytes.NewReader(req.Body))
	if err != nil {
		return nil, err
	}

	// Set default headers
	httpReq.Header.Set("User-Agent", ph.config.UserAgent)
	httpReq.Header.Set("Accept", ph.config.AcceptHeader)
	httpReq.Header.Set("Accept-Language", ph.config.AcceptLanguage)
	httpReq.Header.Set("Connection", "keep-alive")
	httpReq.Header.Set("Upgrade-Insecure-Requests", "1")

	// Set custom headers
	for key, value := range req.Headers {
		// Keep Host and Accept-Encoding under proxy control.
		if !strings.EqualFold(key, "Host") && !strings.EqualFold(key, "Accept-Encoding") {
			httpReq.Header.Set(key, value)
		}
	}

	return httpReq, nil
}

// sendSuccessResponse sends a successful response back to the client
func (ph *ProxyHandler) sendSuccessResponse(w http.ResponseWriter, resp *http.Response, body []byte) {
	// Create proxy response
	proxyResp := ProxyResponse{
		Status:  resp.StatusCode,
		Body:    body,
		Cookies: make([]http.Cookie, 0),
	}

	// Copy cookies manually
	for _, cookie := range resp.Cookies() {
		proxyResp.Cookies = append(proxyResp.Cookies, *cookie)
	}

	// Copy headers
	proxyResp.Headers = make(map[string]string)
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
