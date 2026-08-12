package main

import (
	"context"
	"math/rand"
	"net"
	"strings"
	"sync/atomic"
	"time"

	utls "github.com/refraction-networking/utls"
	"github.com/rs/zerolog/log"
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
	return FingerprintUserAgents["HelloChrome_120"]
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

// CreateDialTLSContextFuncFor creates a TLS dialer that always uses the given
// client hello preset (no rotation at dial time).
func (tfm *TLSFingerprintManager) CreateDialTLSContextFuncFor(clientHelloID string) func(ctx context.Context, network, addr string) (net.Conn, error) {
	return func(ctx context.Context, network, addr string) (net.Conn, error) {
		return tfm.dialUTLSContextWith(ctx, network, addr, clientHelloID)
	}
}

func (tfm *TLSFingerprintManager) dialUTLSContextWith(ctx context.Context, network, addr, clientHelloID string) (net.Conn, error) {
	dialer := &net.Dialer{
		Timeout:   10 * time.Second,
		KeepAlive: 30 * time.Second,
	}
	rawConn, err := dialer.DialContext(ctx, network, addr)
	if err != nil {
		return nil, err
	}

	serverName := addr
	if host, _, splitErr := net.SplitHostPort(addr); splitErr == nil {
		serverName = host
	}

	tlsConfig := &utls.Config{
		ServerName:         serverName,
		MinVersion:         utls.VersionTLS12,
		MaxVersion:         utls.VersionTLS13,
		InsecureSkipVerify: false,
		NextProtos:         []string{"http/1.1"},
	}

	clientHelloPreset := tfm.resolveClientHelloID(clientHelloID)
	uConn := utls.UClient(rawConn, tlsConfig, utls.HelloCustom)
	if err := tfm.applyClientHelloPreset(uConn, clientHelloPreset); err != nil {
		_ = rawConn.Close()
		return nil, err
	}
	if err := uConn.HandshakeContext(ctx); err != nil {
		_ = rawConn.Close()
		return nil, err
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
	return tfm.dialUTLSContextWith(ctx, network, addr, clientID)
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

func (tfm *TLSFingerprintManager) applyClientHelloPreset(uConn *utls.UConn, clientHelloID utls.ClientHelloID) error {
	spec, err := utls.UTLSIdToSpec(clientHelloID)
	if err != nil {
		return err
	}

	for _, ext := range spec.Extensions {
		if alpnExt, ok := ext.(*utls.ALPNExtension); ok {
			alpnExt.AlpnProtocols = []string{"http/1.1"}
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
		return utls.HelloChrome_Auto
	}
}

// GetRandomFingerprint returns a random fingerprint from the rotation list
func GetRandomFingerprint(fingerprints []string) string {
	if len(fingerprints) == 0 {
		return "HelloChrome_120"
	}
	return fingerprints[rand.Intn(len(fingerprints))]
}
