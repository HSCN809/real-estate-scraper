package main

import (
	"crypto/tls"
	"io"
	"net"
	"net/http"
	"net/http/httptest"
	"net/url"
	"sync/atomic"
	"testing"
	"time"
)

func TestAcquireReusesSessionClient(t *testing.T) {
	cfg := DefaultConfig()
	cfg.MaxIdleConns = 4
	cfg.MaxIdleConnsPerHost = 1
	pool := NewClientPool(cfg, NewTLSFingerprintManager(cfg))
	defer pool.Close()

	first := pool.Acquire("scrape-1")
	pool.Release("scrape-1", first)
	second := pool.Acquire("scrape-1")
	if first != second {
		t.Fatal("session client was not reused")
	}

	other := pool.Acquire("")
	pool.Release("", other)
	if other == first {
		t.Fatal("unscoped acquire returned the leased client")
	}
}

func TestRecycleClearsCookieJar(t *testing.T) {
	cfg := DefaultConfig()
	cfg.MaxIdleConns = 2
	cfg.MaxIdleConnsPerHost = 1
	pool := NewClientPool(cfg, NewTLSFingerprintManager(cfg))
	defer pool.Close()

	client := pool.Acquire("s")
	target, err := url.Parse("https://www.hepsiemlak.com/")
	if err != nil {
		t.Fatal(err)
	}
	client.Client.Jar.SetCookies(target, []*http.Cookie{{Name: "__cf_bm", Value: "secret"}})

	pool.mu.Lock()
	delete(pool.sessions, "s")
	pool.mu.Unlock()
	pool.recycle(client)

	again := pool.GetClient()
	if cookies := again.Client.Jar.Cookies(target); len(cookies) != 0 {
		t.Fatalf("recycled jar = %+v", cookies)
	}
}

func TestAdaptiveTransportH1Fallback(t *testing.T) {
	ts := httptest.NewUnstartedServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("X-Proto", r.Proto)
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte("ok-http1"))
	}))
	ts.TLS = &tls.Config{
		NextProtos: []string{"http/1.1"},
	}
	ts.StartTLS()
	defer ts.Close()

	cfg := DefaultConfig()
	cfg.InsecureSkipVerify = true
	cfg.ReadTimeout = 5 * time.Second

	tlsMgr := NewTLSFingerprintManager(cfg)
	pool := NewClientPool(cfg, tlsMgr)
	defer pool.Close()

	client := pool.GetClient()
	defer pool.ReturnClient(client)

	req, err := http.NewRequest(http.MethodGet, ts.URL, nil)
	if err != nil {
		t.Fatal(err)
	}

	resp, err := client.Client.Do(req)
	if err != nil {
		t.Fatalf("Do failed on H1-only server: %v", err)
	}
	defer resp.Body.Close()

	body, _ := io.ReadAll(resp.Body)
	if resp.StatusCode != http.StatusOK || string(body) != "ok-http1" {
		t.Fatalf("unexpected response: status=%d, body=%s", resp.StatusCode, string(body))
	}

	at, ok := client.Client.Transport.(*AdaptiveTransport)
	if !ok {
		t.Fatalf("expected *AdaptiveTransport, got %T", client.Client.Transport)
	}
	parsedURL, _ := url.Parse(ts.URL)
	if _, isH1 := at.h1OnlyHosts.Load(parsedURL.Host); !isH1 {
		t.Fatalf("expected host %s to be marked h1-only", parsedURL.Host)
	}
}

func TestAdaptiveTransportProxyTunnel(t *testing.T) {
	var connectCalled atomic.Bool

	targetServer := httptest.NewTLSServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte("proxied-target"))
	}))
	defer targetServer.Close()

	proxyServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodConnect {
			http.Error(w, "only CONNECT allowed", http.StatusMethodNotAllowed)
			return
		}
		connectCalled.Store(true)

		hijacker, ok := w.(http.Hijacker)
		if !ok {
			http.Error(w, "hijacking not supported", http.StatusInternalServerError)
			return
		}
		clientConn, _, err := hijacker.Hijack()
		if err != nil {
			return
		}
		defer clientConn.Close()

		targetConn, err := net.Dial("tcp", r.Host)
		if err != nil {
			clientConn.Write([]byte("HTTP/1.1 502 Bad Gateway\r\n\r\n"))
			return
		}
		defer targetConn.Close()

		clientConn.Write([]byte("HTTP/1.1 200 Connection Established\r\n\r\n"))

		go func() {
			_, _ = io.Copy(targetConn, clientConn)
		}()
		_, _ = io.Copy(clientConn, targetConn)
	}))
	defer proxyServer.Close()

	cfg := DefaultConfig()
	cfg.InsecureSkipVerify = true
	cfg.UseMobileProxy = true
	cfg.MobileProxyURL = proxyServer.URL
	cfg.ReadTimeout = 5 * time.Second

	tlsMgr := NewTLSFingerprintManager(cfg)
	pool := NewClientPool(cfg, tlsMgr)
	defer pool.Close()

	client := pool.GetClient()
	defer pool.ReturnClient(client)

	req, err := http.NewRequest(http.MethodGet, targetServer.URL, nil)
	if err != nil {
		t.Fatal(err)
	}

	resp, err := client.Client.Do(req)
	if err != nil {
		t.Fatalf("request through proxy failed: %v", err)
	}
	defer resp.Body.Close()

	body, _ := io.ReadAll(resp.Body)
	if resp.StatusCode != http.StatusOK || string(body) != "proxied-target" {
		t.Fatalf("unexpected resp: status=%d body=%s", resp.StatusCode, string(body))
	}

	if !connectCalled.Load() {
		t.Fatal("expected request to go through CONNECT proxy, but proxy was never called!")
	}
}
