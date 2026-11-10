package main

import (
	"bufio"
	"context"
	"encoding/base64"
	"fmt"
	"io"
	"math/rand"
	"net"
	"net/http"
	"net/url"
	"strings"
	"sync/atomic"
	"time"

	utls "github.com/refraction-networking/utls"
	"github.com/rs/zerolog/log"
	"golang.org/x/net/proxy"
)

// TLSFingerprintManager manages TLS fingerprint spoofing
type TLSFingerprintManager struct {
	config      *Config
	rotateIndex atomic.Int64
}

// FingerprintUserAgents maps TLS client IDs to matching User-Agent strings.
// Keeping UA and TLS fingerprint consistent is critical for Cloudflare detection.
var FingerprintUserAgents = map[string]string{
	"HelloChrome_133":  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
	"HelloChrome_131":  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
	"HelloChrome_120":  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
	"HelloFirefox_120": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
	"HelloFirefox_105": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:105.0) Gecko/20100101 Firefox/105.0",
	"HelloFirefox_102": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:102.0) Gecko/20100101 Firefox/102.0",
}

// UserAgentForClientHelloID returns the matching User-Agent for a client hello ID.
func UserAgentForClientHelloID(clientHelloID string) string {
	if ua, ok := FingerprintUserAgents[clientHelloID]; ok {
		return ua
	}
	return FingerprintUserAgents["HelloChrome_133"]
}

// NewTLSFingerprintManager creates a new TLS fingerprint manager
func NewTLSFingerprintManager(cfg *Config) *TLSFingerprintManager {
	mgr := &TLSFingerprintManager{
		config: cfg,
	}

	// Log fingerprint rotation status
	if cfg.TLSRotate && len(cfg.TLSRotateList) > 0 {
		log.Info().
			Int("count", len(cfg.TLSRotateList)).
			Strs("fingerprints", cfg.TLSRotateList).
			Msg("TLS fingerprint rotation enabled")
	} else {
		log.Info().
			Str("fingerprint", cfg.TLSClientID).
			Msg("TLS fingerprint rotation disabled, using fixed fingerprint")
	}

	return mgr
}

// FingerprintForClient returns the fingerprint ID and matching User-Agent for a
// pooled client index. Rotation (if enabled) is deterministic per client so the
// UA sent with the request always matches the TLS fingerprint of the connection.
func (tfm *TLSFingerprintManager) FingerprintForClient(index int) (string, string) {
	var clientID string
	if tfm.config.TLSRotate && len(tfm.config.TLSRotateList) > 0 {
		clientID = tfm.config.TLSRotateList[index%len(tfm.config.TLSRotateList)]
	} else {
		clientID = tfm.config.TLSClientID
	}
	return clientID, UserAgentForClientHelloID(clientID)
}

type bufferedConn struct {
	net.Conn
	r io.Reader
}

func (bc *bufferedConn) Read(b []byte) (int, error) {
	return bc.r.Read(b)
}

func dialRawConn(ctx context.Context, network, addr string, proxyURL *url.URL) (net.Conn, error) {
	dialer := &net.Dialer{
		Timeout:   10 * time.Second,
		KeepAlive: 30 * time.Second,
	}

	if proxyURL == nil {
		return dialer.DialContext(ctx, network, addr)
	}

	switch proxyURL.Scheme {
	case "http", "https":
		proxyHost := proxyURL.Host
		if _, _, err := net.SplitHostPort(proxyHost); err != nil {
			if proxyURL.Scheme == "https" {
				proxyHost = net.JoinHostPort(proxyHost, "443")
			} else {
				proxyHost = net.JoinHostPort(proxyHost, "80")
			}
		}

		conn, err := dialer.DialContext(ctx, "tcp", proxyHost)
		if err != nil {
			return nil, fmt.Errorf("failed to dial proxy %s: %w", proxyURL.Redacted(), err)
		}

		connectReq := &http.Request{
			Method: http.MethodConnect,
			URL:    &url.URL{Opaque: addr},
			Host:   addr,
			Header: make(http.Header),
		}

		if proxyURL.User != nil {
			user := proxyURL.User.Username()
			pass, _ := proxyURL.User.Password()
			auth := base64.StdEncoding.EncodeToString([]byte(user + ":" + pass))
			connectReq.Header.Set("Proxy-Authorization", "Basic "+auth)
		}

		if err := connectReq.Write(conn); err != nil {
			_ = conn.Close()
			return nil, fmt.Errorf("failed to send CONNECT to proxy: %w", err)
		}

		br := bufio.NewReader(conn)
		connectResp, err := http.ReadResponse(br, connectReq)
		if err != nil {
			_ = conn.Close()
			return nil, fmt.Errorf("failed to read CONNECT response from proxy: %w", err)
		}
		if connectResp.StatusCode != http.StatusOK {
			_ = conn.Close()
			return nil, fmt.Errorf("proxy CONNECT rejected with status %d: %s", connectResp.StatusCode, connectResp.Status)
		}

		if br.Buffered() > 0 {
			return &bufferedConn{Conn: conn, r: br}, nil
		}
		return conn, nil

	case "socks5":
		var auth *proxy.Auth
		if proxyURL.User != nil {
			auth = &proxy.Auth{
				User: proxyURL.User.Username(),
			}
			auth.Password, _ = proxyURL.User.Password()
		}
		socksDialer, err := proxy.SOCKS5("tcp", proxyURL.Host, auth, dialer)
		if err != nil {
			return nil, fmt.Errorf("failed to create socks5 dialer: %w", err)
		}
		if contextDialer, ok := socksDialer.(proxy.ContextDialer); ok {
			return contextDialer.DialContext(ctx, network, addr)
		}
		return socksDialer.Dial(network, addr)

	default:
		return nil, fmt.Errorf("unsupported proxy scheme: %s", proxyURL.Scheme)
	}
}

// CreateDialTLSContextFuncFor creates a TLS dialer that always uses the given
// client hello preset (no rotation at dial time) with specified ALPN protocols.
func (tfm *TLSFingerprintManager) CreateDialTLSContextFuncFor(clientHelloID string, alpnProtocols ...string) func(ctx context.Context, network, addr string) (net.Conn, error) {
	return tfm.CreateDialTLSContextFuncWithProxy(nil, false, clientHelloID, alpnProtocols...)
}

// CreateDialTLSContextFuncWithProxy creates a TLS dialer that supports upstream proxy tunneling,
// strict HTTP/2 ALPN validation, and utls fingerprint presets.
func (tfm *TLSFingerprintManager) CreateDialTLSContextFuncWithProxy(proxyURL *url.URL, mustNegotiateH2 bool, clientHelloID string, alpnProtocols ...string) func(ctx context.Context, network, addr string) (net.Conn, error) {
	protocols := alpnProtocols
	if len(protocols) == 0 {
		protocols = []string{"h2", "http/1.1"}
	}
	return func(ctx context.Context, network, addr string) (net.Conn, error) {
		return tfm.dialUTLSContextWith(ctx, network, addr, clientHelloID, protocols, proxyURL, mustNegotiateH2)
	}
}

func (tfm *TLSFingerprintManager) dialUTLSContextWith(ctx context.Context, network, addr, clientHelloID string, alpnProtocols []string, proxyURL *url.URL, mustNegotiateH2 bool) (net.Conn, error) {
	rawConn, err := dialRawConn(ctx, network, addr, proxyURL)
	if err != nil {
		return nil, err
	}

	serverName := addr
	if host, _, splitErr := net.SplitHostPort(addr); splitErr == nil {
		serverName = host
	}

	if len(alpnProtocols) == 0 {
		alpnProtocols = []string{"h2", "http/1.1"}
	}

	tlsConfig := &utls.Config{
		ServerName:         serverName,
		MinVersion:         utls.VersionTLS12,
		MaxVersion:         utls.VersionTLS13,
		InsecureSkipVerify: tfm.config != nil && tfm.config.InsecureSkipVerify,
		NextProtos:         alpnProtocols,
	}

	clientHelloPreset := tfm.resolveClientHelloID(clientHelloID)
	uConn := utls.UClient(rawConn, tlsConfig, utls.HelloCustom)
	if err := tfm.applyClientHelloPreset(uConn, clientHelloPreset, alpnProtocols); err != nil {
		_ = rawConn.Close()
		return nil, err
	}
	if err := uConn.HandshakeContext(ctx); err != nil {
		_ = rawConn.Close()
		return nil, err
	}

	if mustNegotiateH2 {
		negotiated := uConn.ConnectionState().NegotiatedProtocol
		if negotiated != "h2" {
			_ = uConn.Close()
			return nil, fmt.Errorf("unexpected ALPN protocol %q; want %q", negotiated, "h2")
		}
	}

	return uConn, nil
}

// CreateDialTLSContextFunc creates a TLS dialer that uses utls fingerprinting.
func (tfm *TLSFingerprintManager) CreateDialTLSContextFunc() func(ctx context.Context, network, addr string) (net.Conn, error) {
	return func(ctx context.Context, network, addr string) (net.Conn, error) {
		return tfm.dialUTLSContext(ctx, network, addr)
	}
}

func (tfm *TLSFingerprintManager) dialUTLSContext(ctx context.Context, network, addr string) (net.Conn, error) {
	clientID := tfm.getNextClientHelloID()
	return tfm.dialUTLSContextWith(ctx, network, addr, clientID, []string{"h2", "http/1.1"}, nil, false)
}

// getNextClientHelloID returns the next TLS client ID for rotation
func (tfm *TLSFingerprintManager) getNextClientHelloID() string {
	if !tfm.config.TLSRotate || len(tfm.config.TLSRotateList) == 0 {
		return tfm.config.TLSClientID
	}

	// Get next index atomically
	idx := tfm.rotateIndex.Add(1) - 1
	fingerprint := tfm.config.TLSRotateList[idx%int64(len(tfm.config.TLSRotateList))]

	log.Debug().
		Str("fingerprint", fingerprint).
		Int64("index", idx%int64(len(tfm.config.TLSRotateList))).
		Msg("Using rotated TLS fingerprint")

	return fingerprint
}

func (tfm *TLSFingerprintManager) applyClientHelloPreset(uConn *utls.UConn, clientHelloID utls.ClientHelloID, alpnProtocols []string) error {
	spec, err := utls.UTLSIdToSpec(clientHelloID)
	if err != nil {
		return err
	}

	if len(alpnProtocols) > 0 {
		for _, ext := range spec.Extensions {
			if alpnExt, ok := ext.(*utls.ALPNExtension); ok {
				alpnExt.AlpnProtocols = alpnProtocols
			}
		}
	}

	return uConn.ApplyPreset(&spec)
}

func (tfm *TLSFingerprintManager) resolveClientHelloID(clientID string) utls.ClientHelloID {
	switch strings.ToLower(strings.TrimSpace(clientID)) {
	case "hellochrome_133", "chrome_133":
		return utls.HelloChrome_133
	case "hellochrome_131", "chrome_131":
		return utls.HelloChrome_131
	case "hellofirefox_120", "firefox_120":
		return utls.HelloFirefox_120
	case "hellofirefox_105", "firefox_105":
		return utls.HelloFirefox_105
	case "hellofirefox_102", "firefox_102":
		return utls.HelloFirefox_102
	case "hellofirefox_auto", "firefox":
		return utls.HelloFirefox_Auto
	case "helloedge_auto", "edge":
		return utls.HelloEdge_Auto
	case "hellosafari_auto", "safari":
		return utls.HelloSafari_Auto
	case "hellorandomized", "randomized":
		return utls.HelloRandomized
	case "hellorandomizedalpn", "randomizedalpn":
		return utls.HelloRandomizedALPN
	case "hellochrome_120", "chrome_120", "hellochrome_119", "chrome_119", "hellochrome_118", "chrome_118", "hellochrome_117", "chrome_117", "hellochrome_116", "chrome_116":
		return utls.HelloChrome_120
	default:
		return utls.HelloChrome_133
	}
}

// GetRandomFingerprint returns a random fingerprint from the rotation list
func GetRandomFingerprint(fingerprints []string) string {
	if len(fingerprints) == 0 {
		return "HelloChrome_133"
	}
	return fingerprints[rand.Intn(len(fingerprints))]
}
