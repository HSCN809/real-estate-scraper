package main

import (
	"net/http"
	"net/url"
	"testing"
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
