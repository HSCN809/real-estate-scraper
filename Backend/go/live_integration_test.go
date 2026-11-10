package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"
)

func TestLiveHepsiemlakProxy(t *testing.T) {
	if testing.Short() {
		t.Skip("skipping live network integration test")
	}

	cfg := DefaultConfig()
	cfg.APIKey = "test-key"
	cfg.ReadTimeout = 30 * time.Second
	cfg.WriteTimeout = 30 * time.Second
	cfg.RateLimit = 100
	cfg.RateLimitBurst = 100

	tlsMgr := NewTLSFingerprintManager(cfg)
	pool := NewClientPool(cfg, tlsMgr)
	defer pool.Close()

	handler := NewProxyHandler(cfg, pool, tlsMgr)

	// Test 1: robots.txt via proxy handler
	proxyReq := ProxyRequest{
		URL:    "https://www.hepsiemlak.com/robots.txt",
		Method: "GET",
	}
	reqBody, _ := json.Marshal(proxyReq)
	req := httptest.NewRequest(http.MethodPost, "/proxy", bytes.NewReader(reqBody))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-API-Key", "test-key")
	rec := httptest.NewRecorder()

	handler.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected HTTP 200 from proxy, got %d: %s", rec.Code, rec.Body.String())
	}

	var proxyResp ProxyResponse
	if err := json.Unmarshal(rec.Body.Bytes(), &proxyResp); err != nil {
		t.Fatalf("failed to decode proxy response: %v", err)
	}

	if proxyResp.Status != 200 {
		t.Fatalf("target status = %d, error: %s", proxyResp.Status, proxyResp.Error)
	}

	t.Logf("robots.txt: Status %d, Body %d bytes", proxyResp.Status, len(proxyResp.Body))

	// Test 2: Live real estate listing search page
	searchReq := ProxyRequest{
		URL:    "https://www.hepsiemlak.com/kadikoy-satilik",
		Method: "GET",
	}
	searchBody, _ := json.Marshal(searchReq)
	req2 := httptest.NewRequest(http.MethodPost, "/proxy", bytes.NewReader(searchBody))
	req2.Header.Set("Content-Type", "application/json")
	req2.Header.Set("X-API-Key", "test-key")
	rec2 := httptest.NewRecorder()

	handler.ServeHTTP(rec2, req2)

	if rec2.Code != http.StatusOK {
		t.Fatalf("expected HTTP 200 from proxy for search, got %d: %s", rec2.Code, rec2.Body.String())
	}

	var searchResp ProxyResponse
	if err := json.Unmarshal(rec2.Body.Bytes(), &searchResp); err != nil {
		t.Fatalf("failed to decode search proxy response: %v", err)
	}

	if searchResp.Status != 200 {
		t.Fatalf("search target status = %d, error: %s", searchResp.Status, searchResp.Error)
	}

	bodyStr := string(searchResp.Body)
	isChallenge := isCloudflareChallenge(searchResp.Status, searchResp.Body)
	hasListings := strings.Contains(bodyStr, "listingCard") || strings.Contains(bodyStr, "card-link") || strings.Contains(bodyStr, "hepsiemlak")

	t.Logf("Search page: Status %d, Body %d bytes", searchResp.Status, len(searchResp.Body))
	t.Logf("Is Cloudflare Challenge: %v", isChallenge)
	t.Logf("Has Listings/Content: %v", hasListings)

	if isChallenge {
		t.Fatalf("Cloudflare challenge received!")
	}
	if !hasListings {
		t.Fatalf("Expected listing content in body")
	}

	// Test 3: Emlakjet robots.txt
	emlakjetReq := ProxyRequest{
		URL:    "https://www.emlakjet.com/robots.txt",
		Method: "GET",
	}
	emlakjetBody, _ := json.Marshal(emlakjetReq)
	req3 := httptest.NewRequest(http.MethodPost, "/proxy", bytes.NewReader(emlakjetBody))
	req3.Header.Set("Content-Type", "application/json")
	req3.Header.Set("X-API-Key", "test-key")
	rec3 := httptest.NewRecorder()

	handler.ServeHTTP(rec3, req3)

	if rec3.Code != http.StatusOK {
		t.Fatalf("expected HTTP 200 from proxy for emlakjet, got %d: %s", rec3.Code, rec3.Body.String())
	}

	var emlakjetResp ProxyResponse
	if err := json.Unmarshal(rec3.Body.Bytes(), &emlakjetResp); err != nil {
		t.Fatalf("failed to decode emlakjet response: %v", err)
	}

	if emlakjetResp.Status != 200 {
		t.Fatalf("emlakjet target status = %d, error: %s", emlakjetResp.Status, emlakjetResp.Error)
	}

	t.Logf("Emlakjet robots.txt: Status %d, Body %d bytes", emlakjetResp.Status, len(emlakjetResp.Body))
}
