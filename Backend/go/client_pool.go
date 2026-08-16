package main

import (
	"crypto/tls"
	"net"
	"net/http"
	"net/http/cookiejar"
	"net/url"
	"sync"
	"time"

	"github.com/rs/zerolog/log"
)

// PooledClient bundles an HTTP client with the User-Agent that matches its
// fixed TLS fingerprint, so UA and fingerprint never diverge.
type PooledClient struct {
	Client    *http.Client
	UserAgent string
}

// ClientPool manages a pool of reusable HTTP clients.
type ClientPool struct {
	config     *Config
	tlsManager *TLSFingerprintManager
	clients    chan *PooledClient
	mu         sync.RWMutex
	maxSize    int
}

// NewClientPool creates a new client pool.
func NewClientPool(cfg *Config, tlsManager *TLSFingerprintManager) *ClientPool {
	pool := &ClientPool{
		config:     cfg,
		tlsManager: tlsManager,
		clients:    make(chan *PooledClient, cfg.MaxIdleConns),
		maxSize:    cfg.MaxIdleConns,
	}

	// Pre-warm the pool with some clients. Each client gets a fixed fingerprint
	// (rotating across the configured list) and the matching User-Agent.
	for i := 0; i < cfg.MaxIdleConnsPerHost; i++ {
		pool.clients <- pool.createClient(i)
	}

	log.Info().Msgf("Client pool initialized with %d clients", cfg.MaxIdleConnsPerHost)
	return pool
}

// GetClient retrieves a client from the pool.
func (cp *ClientPool) GetClient() *PooledClient {
	select {
	case client := <-cp.clients:
		return client
	default:
		// Pool is empty, create a new client.
		return cp.createClient(int(time.Now().UnixNano()))
	}
}

// ReturnClient returns a client back to the pool.
func (cp *ClientPool) ReturnClient(client *PooledClient) {
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

// createClient creates a new HTTP client with custom transport, a cookie jar,
// and a TLS fingerprint bound to the given rotation index.
func (cp *ClientPool) createClient(index int) *PooledClient {
	clientHelloID, userAgent := cp.tlsManager.FingerprintForClient(index)

	jar, err := cookiejar.New(nil)
	if err != nil {
		jar = nil
	}

	return &PooledClient{
		Client: &http.Client{
			Transport: cp.createTransport(clientHelloID),
			Timeout:   cp.config.ReadTimeout,
			Jar:       jar,
		},
		UserAgent: userAgent,
	}
}

// createTransport creates an HTTP transport and wires utls TLS dialing.
func (cp *ClientPool) createTransport(clientHelloID string) *http.Transport {
	var proxyURL *url.URL

	if cp.config.UseMobileProxy && cp.config.MobileProxyURL != "" {
		if parsedURL, err := url.Parse(cp.config.MobileProxyURL); err == nil {
			if cp.config.MobileProxyUser != "" || cp.config.MobileProxyPass != "" {
				parsedURL.User = url.UserPassword(cp.config.MobileProxyUser, cp.config.MobileProxyPass)
			}
			proxyURL = parsedURL
			log.Info().Msgf("Upstream residential proxy configured: %s", proxyURL.Redacted())
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
		transport.DialTLSContext = cp.tlsManager.CreateDialTLSContextFuncFor(clientHelloID)
	}

	return transport
}

// Close closes all clients in the pool.
func (cp *ClientPool) Close() {
	close(cp.clients)

	for client := range cp.clients {
		if transport, ok := client.Client.Transport.(*http.Transport); ok {
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
