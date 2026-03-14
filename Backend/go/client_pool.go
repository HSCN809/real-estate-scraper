package main

import (
	"crypto/tls"
	"net"
	"net/http"
	"net/url"
	"sync"
	"time"

	"github.com/rs/zerolog/log"
)

// ClientPool manages a pool of reusable HTTP clients.
type ClientPool struct {
	config     *Config
	tlsManager *TLSFingerprintManager
	clients    chan *http.Client
	mu         sync.RWMutex
	maxSize    int
}

// NewClientPool creates a new client pool.
func NewClientPool(cfg *Config, tlsManager *TLSFingerprintManager) *ClientPool {
	pool := &ClientPool{
		config:     cfg,
		tlsManager: tlsManager,
		clients:    make(chan *http.Client, cfg.MaxIdleConns),
		maxSize:    cfg.MaxIdleConns,
	}

	// Pre-warm the pool with some clients.
	for i := 0; i < cfg.MaxIdleConnsPerHost; i++ {
		pool.clients <- pool.createClient()
	}

	log.Info().Msgf("Client pool initialized with %d clients", cfg.MaxIdleConnsPerHost)
	return pool
}

// GetClient retrieves a client from the pool.
func (cp *ClientPool) GetClient() *http.Client {
	select {
	case client := <-cp.clients:
		return client
	default:
		// Pool is empty, create a new client.
		return cp.createClient()
	}
}

// ReturnClient returns a client back to the pool.
func (cp *ClientPool) ReturnClient(client *http.Client) {
	cp.mu.RLock()
	defer cp.mu.RUnlock()

	if len(cp.clients) < cp.maxSize {
		select {
		case cp.clients <- client:
			return
		default:
			// Pool is full, discard this client.
		}
	}
}

// createClient creates a new HTTP client with custom transport.
func (cp *ClientPool) createClient() *http.Client {
	return &http.Client{
		Transport: cp.createTransport(),
		Timeout:   cp.config.ReadTimeout,
	}
}

// createTransport creates an HTTP transport and wires utls TLS dialing.
func (cp *ClientPool) createTransport() *http.Transport {
	var proxyURL *url.URL

	if cp.config.UseMobileProxy && cp.config.MobileProxyURL != "" {
		if parsedURL, err := url.Parse(cp.config.MobileProxyURL); err == nil {
			if cp.config.MobileProxyUser != "" || cp.config.MobileProxyPass != "" {
				parsedURL.User = url.UserPassword(cp.config.MobileProxyUser, cp.config.MobileProxyPass)
			}
			proxyURL = parsedURL
			log.Info().Msgf("Mobile proxy configured: %s", proxyURL.String())
		}
	}

	transport := &http.Transport{
		Proxy: http.ProxyURL(proxyURL),
		DialContext: (&net.Dialer{
			Timeout:   10 * time.Second,
			KeepAlive: 30 * time.Second,
		}).DialContext,
		MaxIdleConns:          cp.config.MaxIdleConns,
		MaxIdleConnsPerHost:   cp.config.MaxIdleConnsPerHost,
		IdleConnTimeout:       cp.config.IdleConnTimeout,
		TLSHandshakeTimeout:   10 * time.Second,
		ExpectContinueTimeout: 1 * time.Second,

		// Fallback config; actual TLS fingerprinting comes from DialTLSContext.
		TLSClientConfig: &tls.Config{
			MinVersion: tls.VersionTLS12,
			MaxVersion: tls.VersionTLS13,
		},

		// Keep HTTP/2 enabled when utls negotiates h2 via ALPN.
		ForceAttemptHTTP2: true,
	}

	if cp.tlsManager != nil {
		transport.DialTLSContext = cp.tlsManager.CreateDialTLSContextFunc()
	}

	return transport
}

// Close closes all clients in the pool.
func (cp *ClientPool) Close() {
	close(cp.clients)

	for client := range cp.clients {
		if transport, ok := client.Transport.(*http.Transport); ok {
			transport.CloseIdleConnections()
		}
	}

	log.Info().Msg("Client pool closed")
}

// GetPoolStats returns statistics about the pool.
func (cp *ClientPool) GetPoolStats() map[string]int {
	cp.mu.RLock()
	defer cp.mu.RUnlock()

	return map[string]int{
		"available_clients": len(cp.clients),
		"max_size":          cp.maxSize,
		"max_per_host":      cp.config.MaxIdleConnsPerHost,
	}
}
