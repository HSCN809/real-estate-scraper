package main

import (
	"crypto/tls"
	"fmt"
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

// sessionIdle is how long a scrape may pause before its client returns to the pool.
// ponytail: one map, no reaper goroutine. Raise this if a task waits longer between pages.
const sessionIdle = 15 * time.Minute

type sessionLease struct {
	client *PooledClient
	used   time.Time
}

// ClientPool manages a pool of reusable HTTP clients.
type ClientPool struct {
	config     *Config
	tlsManager *TLSFingerprintManager
	clients    chan *PooledClient
	sessions   map[string]*sessionLease
	mu         sync.RWMutex
	maxSize    int
}

// NewClientPool creates a new client pool.
func NewClientPool(cfg *Config, tlsManager *TLSFingerprintManager) *ClientPool {
	pool := &ClientPool{
		config:     cfg,
		tlsManager: tlsManager,
		clients:    make(chan *PooledClient, cfg.MaxIdleConns),
		sessions:   make(map[string]*sessionLease),
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

// Acquire returns the client pinned to session, or any pooled client when session is empty.
func (cp *ClientPool) Acquire(session string) *PooledClient {
	cp.returnAll(cp.dropIdleSessions())
	if session == "" {
		return cp.GetClient()
	}

	cp.mu.Lock()
	if lease, ok := cp.sessions[session]; ok {
		lease.used = time.Now()
		client := lease.client
		cp.mu.Unlock()
		return client
	}
	cp.mu.Unlock()

	client := cp.GetClient()
	cp.mu.Lock()
	if lease, ok := cp.sessions[session]; ok {
		lease.used = time.Now()
		existing := lease.client
		cp.mu.Unlock()
		cp.ReturnClient(client)
		return existing
	}
	evict := cp.evictOldestLocked()
	cp.sessions[session] = &sessionLease{client: client, used: time.Now()}
	cp.mu.Unlock()
	if evict != nil {
		cp.recycle(evict)
	}
	return client
}

// Release returns an unscoped client to the pool. A session client stays leased.
func (cp *ClientPool) Release(session string, client *PooledClient) {
	cp.returnAll(cp.dropIdleSessions())
	if session == "" {
		cp.ReturnClient(client)
	}
}

func (cp *ClientPool) evictOldestLocked() *PooledClient {
	if len(cp.sessions) < cp.maxSize {
		return nil
	}
	var oldestID string
	var oldest time.Time
	var evict *PooledClient
	first := true
	for id, lease := range cp.sessions {
		if first || lease.used.Before(oldest) {
			first = false
			oldest = lease.used
			oldestID = id
			evict = lease.client
		}
	}
	delete(cp.sessions, oldestID)
	return evict
}

func (cp *ClientPool) dropIdleSessions() []*PooledClient {
	cp.mu.Lock()
	defer cp.mu.Unlock()

	now := time.Now()
	stale := make([]*PooledClient, 0)
	for id, lease := range cp.sessions {
		if now.Sub(lease.used) > sessionIdle {
			stale = append(stale, lease.client)
			delete(cp.sessions, id)
		}
	}
	return stale
}

func (cp *ClientPool) returnAll(clients []*PooledClient) {
	for _, client := range clients {
		cp.recycle(client)
	}
}

// recycle drops the previous host cookies before the client can be borrowed again.
func (cp *ClientPool) recycle(client *PooledClient) {
	jar, err := cookiejar.New(nil)
	if err != nil {
		if transport, ok := client.Client.Transport.(*http.Transport); ok {
			transport.CloseIdleConnections()
		}
		return
	}
	client.Client.Jar = jar
	cp.ReturnClient(client)
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
			if transport, ok := client.Client.Transport.(*http.Transport); ok {
				transport.CloseIdleConnections()
			}
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
			CheckRedirect: func(req *http.Request, via []*http.Request) error {
				if len(via) >= 10 {
					return fmt.Errorf("too many redirects")
				}
				return validateTargetURL(req.URL.String())
			},
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
	cp.mu.Lock()
	leased := make([]*PooledClient, 0, len(cp.sessions))
	for _, lease := range cp.sessions {
		leased = append(leased, lease.client)
	}
	cp.sessions = map[string]*sessionLease{}
	cp.mu.Unlock()
	for _, client := range leased {
		if transport, ok := client.Client.Transport.(*http.Transport); ok {
			transport.CloseIdleConnections()
		}
	}

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
