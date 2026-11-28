package main

import (
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"
)

func testHandler(apiKey string) *ProxyHandler {
	return &ProxyHandler{
		config: &Config{
			APIKey:         apiKey,
			ReadTimeout:    30 * time.Second,
			RetryOnTimeout: true,
			UserAgent:      "cfg-ua",
			AcceptHeader:   "text/html",
			AcceptLanguage: "tr",
		},
		rateLimiter:    NewRateLimiter(1000, 1000),
		allowedOrigins: []string{"http://localhost:3000"},
		inflight:       make(chan struct{}, 4),
	}
}

func TestServeHTTPProxyBusyReturns503(t *testing.T) {
	ph := testHandler("secret")
	ph.inflight = make(chan struct{}, 1)
	ph.inflight <- struct{}{} // simulate one in-flight request filling capacity

	rec := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodPost, "/proxy", strings.NewReader("{}"))
	req.Header.Set("X-API-Key", "secret")
	ph.ServeHTTP(rec, req)
	if rec.Code != http.StatusServiceUnavailable {
		t.Fatalf("busy status = %d", rec.Code)
	}
}

func TestServeHTTPRejectsOversizedBody(t *testing.T) {
	ph := testHandler("secret")

	body := `{"url":"https://www.hepsiemlak.com/","body":"` + strings.Repeat("A", maxProxyRequestBytes) + `"}`
	rec := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodPost, "/proxy", strings.NewReader(body))
	req.Header.Set("X-API-Key", "secret")
	ph.ServeHTTP(rec, req)
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("oversized body status = %d", rec.Code)
	}
	if len(ph.inflight) != 0 {
		t.Fatal("inflight slot not released")
	}
}

func TestRateLimiterAllowBurstThenDeny(t *testing.T) {
	rl := NewRateLimiter(1, 2)
	if !rl.Allow("1.1.1.1") || !rl.Allow("1.1.1.1") {
		t.Fatal("first two requests should be allowed")
	}
	if rl.Allow("1.1.1.1") {
		t.Fatal("third request should be denied")
	}
	if !rl.Allow("2.2.2.2") {
		t.Fatal("different IP should still be allowed")
	}
}

func TestServeHTTPHealthAndNotFound(t *testing.T) {
	ph := testHandler("secret")

	rec := httptest.NewRecorder()
	ph.ServeHTTP(rec, httptest.NewRequest(http.MethodGet, "/", nil))
	if rec.Code != http.StatusOK {
		t.Fatalf("health status = %d", rec.Code)
	}
	if !strings.Contains(rec.Body.String(), "invisible-proxy") {
		t.Fatalf("health body = %s", rec.Body.String())
	}

	rec = httptest.NewRecorder()
	ph.ServeHTTP(rec, httptest.NewRequest(http.MethodGet, "/unknown", nil))
	if rec.Code != http.StatusNotFound {
		t.Fatalf("unknown status = %d", rec.Code)
	}
}

func TestServeHTTPProxyAuth(t *testing.T) {
	ph := testHandler("secret")

	rec := httptest.NewRecorder()
	ph.ServeHTTP(rec, httptest.NewRequest(http.MethodPost, "/proxy", strings.NewReader("{}")))
	if rec.Code != http.StatusUnauthorized {
		t.Fatalf("missing key status = %d", rec.Code)
	}

	rec = httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodPost, "/proxy", strings.NewReader("{not-json"))
	req.Header.Set("X-API-Key", "secret")
	ph.ServeHTTP(rec, req)
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("bad json after auth status = %d", rec.Code)
	}

	rec = httptest.NewRecorder()
	req = httptest.NewRequest(http.MethodGet, "/proxy?api_key=secret", nil)
	ph.ServeHTTP(rec, req)
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("query key missing url status = %d", rec.Code)
	}

	open := testHandler("")
	rec = httptest.NewRecorder()
	open.ServeHTTP(rec, httptest.NewRequest(http.MethodGet, "/proxy", nil))
	if rec.Code != http.StatusUnauthorized {
		t.Fatalf("empty API key status = %d", rec.Code)
	}
}

func TestServeHTTPCORSAndOptions(t *testing.T) {
	ph := testHandler("")

	rec := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodOptions, "/proxy", nil)
	req.Header.Set("Origin", "http://localhost:3000")
	ph.ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("options status = %d", rec.Code)
	}
	if rec.Header().Get("Access-Control-Allow-Origin") != "http://localhost:3000" {
		t.Fatalf("allowed origin header = %q", rec.Header().Get("Access-Control-Allow-Origin"))
	}

	rec = httptest.NewRecorder()
	req = httptest.NewRequest(http.MethodGet, "/", nil)
	req.Header.Set("Origin", "https://evil.example")
	ph.ServeHTTP(rec, req)
	if rec.Header().Get("Access-Control-Allow-Origin") != "" {
		t.Fatal("unknown origin should not get ACAO")
	}
}

func TestCreateHTTPRequestAndShouldRetry(t *testing.T) {
	ph := testHandler("")
	req, err := ph.createHTTPRequest(&ProxyRequest{
		URL:    "https://example.com/path",
		Method: http.MethodGet,
		Headers: map[string]string{
			"Host":            "evil.example",
			"Accept-Encoding": "identity",
			"Authorization":   "Bearer x",
		},
	}, "pooled-ua")
	if err != nil {
		t.Fatal(err)
	}
	if req.Header.Get("Host") != "" && req.Host == "evil.example" {
		t.Fatal("custom Host should not override the request")
	}
	if req.Header.Get("Accept-Encoding") == "identity" {
		t.Fatal("Accept-Encoding should stay under proxy control")
	}
	if req.Header.Get("User-Agent") != "pooled-ua" {
		t.Fatalf("UA = %q, want pooled-ua", req.Header.Get("User-Agent"))
	}
	if req.Header.Get("Authorization") != "Bearer x" {
		t.Fatal("Authorization should be forwarded")
	}

	ph.config.RetryOnTimeout = false
	if ph.shouldRetry(errors.New("i/o timeout")) {
		t.Fatal("should not retry when RetryOnTimeout is false")
	}
	ph.config.RetryOnTimeout = true
	if !ph.shouldRetry(errors.New("i/o timeout")) {
		t.Fatal("timeout should retry")
	}
	if ph.shouldRetry(errors.New("something else")) {
		t.Fatal("unrelated error should not retry")
	}
}

func TestGetClientIPAndExtractHeaders(t *testing.T) {
	// Spoofable headers are ignored; only the direct peer counts.
	req := httptest.NewRequest(http.MethodGet, "/", nil)
	req.RemoteAddr = "10.0.0.5:4321"
	req.Header.Set("X-Forwarded-For", "1.1.1.1, 2.2.2.2")
	req.Header.Set("X-Real-IP", "3.3.3.3")
	if got := getClientIP(req); got != "10.0.0.5" {
		t.Fatalf("client ip = %q", got)
	}

	req.RemoteAddr = "[::1]:4321"
	if got := getClientIP(req); got != "::1" {
		t.Fatalf("ipv6 client ip = %q", got)
	}

	req = httptest.NewRequest(http.MethodGet, "/", nil)
	req.Header.Set("Authorization", "Bearer x")
	req.Header.Set("Cookie", "a=b")
	req.Header.Set("User-Agent", "browser")
	headers := extractHeaders(req)
	if headers["Authorization"] != "Bearer x" || headers["Cookie"] != "a=b" {
		t.Fatalf("headers = %#v", headers)
	}
	if _, ok := headers["User-Agent"]; ok {
		t.Fatal("User-Agent should not be extracted")
	}
}

func TestValidateTargetURL(t *testing.T) {
	allowed := []string{
		"https://www.hepsiemlak.com/istanbul",
		"https://hepsiemlak.com/",
		"https://www.emlakjet.com/satilik-konut",
	}
	for _, raw := range allowed {
		if err := validateTargetURL(raw); err != nil {
			t.Fatalf("allowed %s: %v", raw, err)
		}
	}

	blocked := []string{
		"http://127.0.0.1:9/",
		"https://127.0.0.1/",
		"http://www.hepsiemlak.com/",
		"https://evil.com/",
		"https://hepsiemlak.com.evil.com/",
		"file:///etc/passwd",
		"https://user:pass@www.hepsiemlak.com/",
	}
	for _, raw := range blocked {
		if err := validateTargetURL(raw); err == nil {
			t.Fatalf("expected reject for %s", raw)
		}
	}
}

func TestServeHTTPRejectsInternalURL(t *testing.T) {
	ph := testHandler("secret")
	rec := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodGet, "/proxy?url=http://127.0.0.1:9/", nil)
	req.Header.Set("X-API-Key", "secret")
	ph.ServeHTTP(rec, req)
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("internal url status = %d", rec.Code)
	}
}

func TestSendErrorResponseJSON(t *testing.T) {
	ph := testHandler("secret")
	rec := httptest.NewRecorder()
	ph.sendErrorResponse(rec, "Unauthorized. Valid API key required.", http.StatusUnauthorized)

	var body ProxyResponse
	if err := json.Unmarshal(rec.Body.Bytes(), &body); err != nil {
		t.Fatal(err)
	}
	if body.Status != http.StatusUnauthorized || body.Error == "" {
		t.Fatalf("body = %+v", body)
	}
}

func BenchmarkIsOriginAllowed(b *testing.B) {
	ph := testHandler("")
	for i := 0; i < b.N; i++ {
		_ = ph.isOriginAllowed("http://localhost:3000")
	}
}

func BenchmarkRateLimiterAllow(b *testing.B) {
	rl := NewRateLimiter(1_000_000, 1_000_000)
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_ = rl.Allow("1.1.1.1")
	}
}

func BenchmarkIsCloudflareChallengeLargeHTML(b *testing.B) {
	body := []byte("<html><body>" + strings.Repeat("<div>ilan detayi istanbul kadikoy satilik daire</div>", 10000) + "</body></html>")
	b.ReportAllocs()
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_ = isCloudflareChallenge(http.StatusOK, body)
	}
}

func TestIsCloudflareChallenge(t *testing.T) {
	if !isCloudflareChallenge(http.StatusForbidden, []byte("no")) {
		t.Fatal("403 should be a challenge")
	}
	if !isCloudflareChallenge(http.StatusOK, []byte("<title>Just a moment...</title>")) {
		t.Fatal("200 interstitial should be a challenge")
	}
	if !isCloudflareChallenge(http.StatusOK, []byte("<HTML><TITLE>JUST A MOMENT</TITLE></HTML>")) {
		t.Fatal("uppercase interstitial should be detected")
	}
	if isCloudflareChallenge(http.StatusOK, []byte("<html>ilan listesi</html>")) {
		t.Fatal("listing html should not be a challenge")
	}
	largeListing := append([]byte(strings.Repeat("<div>ilan</div>", 5000)), []byte("just a moment")...)
	if isCloudflareChallenge(http.StatusOK, largeListing) {
		t.Fatal("marker past 32KB scan cap in large listing html should be ignored")
	}
}

func TestProxySessionID(t *testing.T) {
	if got := proxySessionID(map[string]string{"x-proxy-session": "abc"}); got != "abc" {
		t.Fatalf("session = %q", got)
	}
	if proxySessionID(nil) != "" {
		t.Fatal("nil headers should have no session")
	}
}

func TestCreateHTTPRequestClientHints(t *testing.T) {
	ph := testHandler("")
	req, err := ph.createHTTPRequest(&ProxyRequest{
		URL:    "https://www.hepsiemlak.com/istanbul",
		Method: http.MethodGet,
	}, "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36")
	if err != nil {
		t.Fatal(err)
	}

	if req.Header.Get("Sec-Ch-Ua") == "" || !strings.Contains(req.Header.Get("Sec-Ch-Ua"), "133") {
		t.Fatalf("Sec-Ch-Ua = %q, want Chrome 133 hints", req.Header.Get("Sec-Ch-Ua"))
	}
	if req.Header.Get("Sec-Ch-Ua-Mobile") != "?0" {
		t.Fatalf("Sec-Ch-Ua-Mobile = %q, want ?0", req.Header.Get("Sec-Ch-Ua-Mobile"))
	}
	if req.Header.Get("Sec-Ch-Ua-Platform") != `"Windows"` {
		t.Fatalf("Sec-Ch-Ua-Platform = %q, want Windows", req.Header.Get("Sec-Ch-Ua-Platform"))
	}
	if req.Header.Get("Sec-Fetch-Dest") != "document" {
		t.Fatalf("Sec-Fetch-Dest = %q, want document", req.Header.Get("Sec-Fetch-Dest"))
	}
	if req.Header.Get("Sec-Fetch-Mode") != "navigate" {
		t.Fatalf("Sec-Fetch-Mode = %q, want navigate", req.Header.Get("Sec-Fetch-Mode"))
	}
	if req.Header.Get("Sec-Fetch-Site") != "none" {
		t.Fatalf("Sec-Fetch-Site = %q, want none", req.Header.Get("Sec-Fetch-Site"))
	}
	if req.Header.Get("Sec-Fetch-User") != "?1" {
		t.Fatalf("Sec-Fetch-User = %q, want ?1", req.Header.Get("Sec-Fetch-User"))
	}
}
