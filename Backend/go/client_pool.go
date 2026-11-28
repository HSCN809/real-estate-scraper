package main

import (
	"context"
	"crypto/tls"
	"fmt"
	"net"
	"net/http"
	"net/http/cookiejar"
	"net/url"
	"strings"
	"sync"
	"time"

	"github.com/rs/zerolog/log"
	"golang.org/x/net/http2"
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
	lastSweep  time.Time
	mu         sync.RWMutex
	maxSize    int
	closed     bool // guarded by mu; ReturnClient must not send after Close
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
	now := time.Now()
	cp.mu.Lock()
	defer cp.mu.Unlock()

	if len(cp.sessions) == 0 || now.Sub(cp.lastSweep) < 10*time.Second {
		return nil
	}
	cp.lastSweep = now
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

type idleCloser interface {
	CloseIdleConnections()
}

func closeIdleClient(client *PooledClient) {
	if client != nil && client.Client != nil {
		if closer, ok := client.Client.Transport.(idleCloser); ok {
			closer.CloseIdleConnections()
		}
	}
}

// AdaptiveTransport routes HTTPS requests to HTTP/2 transport (negotiating h2 via utls ALPN)
// and gracefully falls back to HTTP/1.1 if the target host does not support h2.
type AdaptiveTransport struct {
	h1Transport *http.Transport
	h2Transport *http2.Transport
	h1OnlyHosts sync.Map
}

func (at *AdaptiveTransport) RoundTrip(req *http.Request) (*http.Response, error) {
	host := req.URL.Host
	if req.URL.Scheme == "https" && at.h2Transport != nil {
		if _, isH1 := at.h1OnlyHosts.Load(host); !isH1 {
			resp, err := at.h2Transport.RoundTrip(req)
			if err == nil {
				return resp, nil
			}
			errStr := strings.ToLower(err.Error())
			if strings.Contains(errStr, "unexpected alpn") || strings.Contains(errStr, "no prior knowledge") {
				at.h1OnlyHosts.Store(host, true)
				if req.GetBody != nil && req.Body != nil {
					if body, bErr := req.GetBody(); bErr == nil {
						req.Body = body
					}
				}
				return at.h1Transport.RoundTrip(req)
			}
			return nil, err
		}
	}
	return at.h1Transport.RoundTrip(req)
}

func (at *AdaptiveTransport) CloseIdleConnections() {
	if at.h1Transport != nil {
		at.h1Transport.CloseIdleConnections()
	}
	if at.h2Transport != nil {
		at.h2Transport.CloseIdleConnections()
	}
}

// recycle drops the previous host cookies before the client can be borrowed again.
func (cp *ClientPool) recycle(client *PooledClient) {
	jar, err := cookiejar.New(nil)
	if err != nil {
		closeIdleClient(client)
		return
	}
	client.Client.Jar = jar
	cp.ReturnClient(client)
}

// GetClient retrieves a client from the pool.
func (cp *ClientPool) GetClient() *PooledClient {
	select {
	case client, ok := <-cp.clients:
		if ok {
			return client
		}
	default:
	}
	// Pool is empty (or closed during shutdown), create a new client.
	return cp.createClient(int(time.Now().UnixNano()))
}

// ReturnClient returns a client back to the pool, closing idle connections on overflow.
func (cp *ClientPool) ReturnClient(client *PooledClient) {
	if client == nil {
		return
	}
	cp.mu.RLock()
	defer cp.mu.RUnlock()
	if cp.closed {
		closeIdleClient(client)
		return
	}

	select {
	case cp.clients <- client:
		return
	default:
		closeIdleClient(client)
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

// createTransport creates an HTTP transport with HTTP/2 and HTTP/1.1 support via utls.
func (cp *ClientPool) createTransport(clientHelloID string) http.RoundTripper {
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

	h1Transport := &http.Transport{
		DialContext: (&net.Dialer{
			Timeout:   10 * time.Second,
			KeepAlive: 30 * time.Second,
		}).DialContext,
		MaxIdleConns:          cp.config.MaxIdleConns,
		MaxIdleConnsPerHost:   cp.config.MaxIdleConnsPerHost,
		IdleConnTimeout:       cp.config.IdleConnTimeout,
		TLSHandshakeTimeout:   10 * time.Second,
		ExpectContinueTimeout: 1 * time.Second,
		TLSClientConfig: &tls.Config{
			MinVersion: tls.VersionTLS12,
			MaxVersion: tls.VersionTLS13,
		},
	}

	if cp.tlsManager != nil {
		h1Transport.DialTLSContext = cp.tlsManager.CreateDialTLSContextFuncWithProxy(proxyURL, false, clientHelloID, "http/1.1")
	}

	h2Transport := &http2.Transport{
		IdleConnTimeout: cp.config.IdleConnTimeout,
		PingTimeout:     15 * time.Second,
	}

	if cp.tlsManager != nil {
		h2Dialer := cp.tlsManager.CreateDialTLSContextFuncWithProxy(proxyURL, true, clientHelloID, "h2", "http/1.1")
		h2Transport.DialTLSContext = func(ctx context.Context, network, addr string, cfg *tls.Config) (net.Conn, error) {
			return h2Dialer(ctx, network, addr)
		}
	}

	return &AdaptiveTransport{
		h1Transport: h1Transport,
		h2Transport: h2Transport,
	}
}

// Close closes all clients in the pool.
func (cp *ClientPool) Close() {
	cp.mu.Lock()
	leased := make([]*PooledClient, 0, len(cp.sessions))
	for _, lease := range cp.sessions {
		leased = append(leased, lease.client)
	}
	cp.sessions = map[string]*sessionLease{}
	cp.closed = true
	// Closed under the write lock so no ReturnClient (holding RLock) can send on it.
	close(cp.clients)
	cp.mu.Unlock()
	for _, client := range leased {
		closeIdleClient(client)
	}

	for client := range cp.clients {
		closeIdleClient(client)
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
