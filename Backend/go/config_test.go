package main

import (
	"testing"
	"time"
)

func TestDefaultConfig(t *testing.T) {
	cfg := DefaultConfig()
	if cfg.Host != "127.0.0.1" {
		t.Fatalf("Host = %q, want 127.0.0.1", cfg.Host)
	}
	if cfg.Port != 8080 {
		t.Fatalf("Port = %d, want 8080", cfg.Port)
	}
	if cfg.APIKey != "" {
		t.Fatalf("APIKey = %q, want empty", cfg.APIKey)
	}
	if cfg.RateLimit != 2 || cfg.RateLimitBurst != 5 {
		t.Fatalf("rate = %d/%d, want 2/5", cfg.RateLimit, cfg.RateLimitBurst)
	}
	if cfg.TLSClientID != "HelloChrome_133" {
		t.Fatalf("TLSClientID = %q", cfg.TLSClientID)
	}
}

func TestLoadConfigFromEnv(t *testing.T) {
	t.Setenv("PROXY_PORT", "9090")
	t.Setenv("PROXY_API_KEY", "secret")
	t.Setenv("TLS_ROTATE", "true")
	t.Setenv("ALLOWED_ORIGINS", "http://a.com,http://b.com")
	t.Setenv("MOBILE_PROXY_URL", "http://proxy:8000")
	t.Setenv("RATE_LIMIT", "25")
	t.Setenv("RETRY_DELAY", "1000")

	cfg := LoadConfigFromEnv()
	if cfg.Port != 9090 {
		t.Fatalf("Port = %d, want 9090", cfg.Port)
	}
	if cfg.APIKey != "secret" {
		t.Fatalf("APIKey = %q, want secret", cfg.APIKey)
	}
	if !cfg.TLSRotate {
		t.Fatal("TLSRotate = false, want true")
	}
	if len(cfg.AllowedOrigins) != 2 {
		t.Fatalf("AllowedOrigins = %v", cfg.AllowedOrigins)
	}
	if !cfg.UseMobileProxy {
		t.Fatal("UseMobileProxy = false, want true")
	}
	if cfg.RateLimit != 25 {
		t.Fatalf("RateLimit = %d, want 25", cfg.RateLimit)
	}
	if cfg.RetryDelay != time.Second {
		t.Fatalf("RetryDelay = %s, want 1s", cfg.RetryDelay)
	}
}

func TestLoadConfigFromEnvIgnoresInvalidPort(t *testing.T) {
	t.Setenv("PROXY_PORT", "abc")
	cfg := LoadConfigFromEnv()
	if cfg.Port != 8080 {
		t.Fatalf("Port = %d, want default 8080", cfg.Port)
	}
}
