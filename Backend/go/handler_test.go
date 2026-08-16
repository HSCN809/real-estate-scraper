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
	if rec.Code == http.StatusUnauthorized {
		t.Fatal("empty API key should not return 401")
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
	req := httptest.NewRequest(http.MethodGet, "/", nil)
	req.Header.Set("X-Forwarded-For", "1.1.1.1, 2.2.2.2")
	if got := getClientIP(req); got != "1.1.1.1" {
		t.Fatalf("xff ip = %q", got)
	}

	req = httptest.NewRequest(http.MethodGet, "/", nil)
	req.Header.Set("X-Real-IP", "3.3.3.3")
	if got := getClientIP(req); got != "3.3.3.3" {
		t.Fatalf("xri ip = %q", got)
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
	ph := testHandler("")
	rec := httptest.NewRecorder()
	ph.ServeHTTP(rec, httptest.NewRequest(http.MethodGet, "/proxy?url=http://127.0.0.1:9/", nil))
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
