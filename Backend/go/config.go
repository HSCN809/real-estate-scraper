package main

import (
	"os"
	"strconv"
	"strings"
	"time"
)

// Config holds the proxy server configuration
type Config struct {
	// Server settings
	Host         string
	Port         int
	ReadTimeout  time.Duration
	WriteTimeout time.Duration

	// Proxy settings
	MobileProxyURL  string
	MobileProxyUser string
	MobileProxyPass string
	UseMobileProxy  bool

	// TLS fingerprint settings
	TLSClientID    string   // uTLS ClientHello ID
	JA3Fingerprint string   // JA3 fingerprint to emulate
	TLSRotate      bool     // Enable TLS fingerprint rotation
	TLSRotateList  []string // List of TLS client IDs to rotate

	// Browser emulation settings
	UserAgent      string
	AcceptLanguage string
	AcceptHeader   string

	// Connection pool settings
	MaxIdleConns        int
	MaxIdleConnsPerHost int
	IdleConnTimeout     time.Duration

	// Retry settings
	MaxRetries     int
	RetryDelay     time.Duration
	RetryOnTimeout bool

	// Security settings
	APIKey         string   // API key for authentication
	AllowedOrigins []string // Allowed CORS origins

	// Rate limiting
	RateLimit      int // Requests per second
	RateLimitBurst int // Max burst size
}

// DefaultConfig returns configuration with sensible defaults
func DefaultConfig() *Config {
	return &Config{
		Host:         "127.0.0.1",
		Port:         8080,
		ReadTimeout:  30 * time.Second,
		WriteTimeout: 30 * time.Second,

		MobileProxyURL: "",
		UseMobileProxy: false,

		// Chrome 120 fingerprint
		TLSClientID:    "HelloChrome_120",
		JA3Fingerprint: "771,4865-4866-4867-49195-49199-49196-49200-52393-52542-49171-49172-156-157-47-53,0-23-65281-10-11-35-16-5-34-51-43-13-45-28-21,29-23-24,0",
		TLSRotate:      true,
		TLSRotateList: []string{
			"HelloChrome_133",
			"HelloChrome_131",
			"HelloChrome_120",
			"HelloFirefox_120",
			"HelloEdge_85",
		},

		UserAgent:      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
		AcceptLanguage: "en-US,en;q=0.9,tr;q=0.8",
		AcceptHeader:   "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",

		MaxIdleConns:        100,
		MaxIdleConnsPerHost: 10,
		IdleConnTimeout:     90 * time.Second,

		MaxRetries:     3,
		RetryDelay:     1 * time.Second,
		RetryOnTimeout: true,

		APIKey: "", // No auth by default
		AllowedOrigins: []string{
			"http://localhost:3000",
			"http://127.0.0.1:3000",
			"http://real-estate-frontend:3000",
		},

		RateLimit:      10, // 10 requests per second
		RateLimitBurst: 20, // Max burst of 20
	}
}

// LoadConfigFromEnv loads configuration from environment variables
func LoadConfigFromEnv() *Config {
	cfg := DefaultConfig()

	if host := os.Getenv("PROXY_HOST"); host != "" {
		cfg.Host = host
	}

	if port := os.Getenv("PROXY_PORT"); port != "" {
		if p, err := strconv.Atoi(port); err == nil {
			cfg.Port = p
		}
	}

	if mobileProxy := os.Getenv("MOBILE_PROXY_URL"); mobileProxy != "" {
		cfg.MobileProxyURL = mobileProxy
		cfg.UseMobileProxy = true
	}

	if proxyUser := os.Getenv("MOBILE_PROXY_USER"); proxyUser != "" {
		cfg.MobileProxyUser = proxyUser
	}

	if proxyPass := os.Getenv("MOBILE_PROXY_PASS"); proxyPass != "" {
		cfg.MobileProxyPass = proxyPass
	}

	if userAgent := os.Getenv("USER_AGENT"); userAgent != "" {
		cfg.UserAgent = userAgent
	}

	if tlsClientID := os.Getenv("TLS_CLIENT_ID"); tlsClientID != "" {
		cfg.TLSClientID = tlsClientID
	}

	if tlsRotate := os.Getenv("TLS_ROTATE"); tlsRotate != "" {
		cfg.TLSRotate = strings.ToLower(tlsRotate) == "true"
	}

	if tlsRotateList := os.Getenv("TLS_ROTATE_LIST"); tlsRotateList != "" {
		cfg.TLSRotateList = strings.Split(tlsRotateList, ",")
	}

	if maxRetries := os.Getenv("MAX_RETRIES"); maxRetries != "" {
		if r, err := strconv.Atoi(maxRetries); err == nil {
			cfg.MaxRetries = r
		}
	}

	// API Key
	if apiKey := os.Getenv("PROXY_API_KEY"); apiKey != "" {
		cfg.APIKey = apiKey
	}

	// Allowed Origins
	if origins := os.Getenv("ALLOWED_ORIGINS"); origins != "" {
		cfg.AllowedOrigins = strings.Split(origins, ",")
	}

	// Rate Limiting
	if rateLimit := os.Getenv("RATE_LIMIT"); rateLimit != "" {
		if r, err := strconv.Atoi(rateLimit); err == nil {
			cfg.RateLimit = r
		}
	}

	if rateBurst := os.Getenv("RATE_LIMIT_BURST"); rateBurst != "" {
		if b, err := strconv.Atoi(rateBurst); err == nil {
			cfg.RateLimitBurst = b
		}
	}

	return cfg
}
