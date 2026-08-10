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

// CreateDialTLSContextFunc creates a TLS dialer that uses utls fingerprinting.
func (tfm *TLSFingerprintManager) CreateDialTLSContextFunc() func(ctx context.Context, network, addr string) (net.Conn, error) {
	return func(ctx context.Context, network, addr string) (net.Conn, error) {
		return tfm.dialUTLSContext(ctx, network, addr)
	}
}

func (tfm *TLSFingerprintManager) dialUTLSContext(ctx context.Context, network, addr string) (net.Conn, error) {
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

	// Get TLS client ID (with rotation if enabled)
	clientID := tfm.getNextClientHelloID()

	tlsConfig := &utls.Config{
		ServerName:         serverName,
		MinVersion:         utls.VersionTLS12,
		MaxVersion:         utls.VersionTLS13,
		InsecureSkipVerify: false,
		NextProtos:         []string{"http/1.1"},
	}

	clientHelloID := tfm.resolveClientHelloID(clientID)
	uConn := utls.UClient(rawConn, tlsConfig, utls.HelloCustom)
	if err := tfm.applyClientHelloPreset(uConn, clientHelloID); err != nil {
		_ = rawConn.Close()
		return nil, err
	}
	if err := uConn.HandshakeContext(ctx); err != nil {
		_ = rawConn.Close()
		return nil, err
	}

	return uConn, nil
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
	case "hellofirefox_120", "hellofirefox_auto", "firefox", "hellofirefox_117", "firefox_117":
		return utls.HelloFirefox_Auto
	case "helloedge_120", "helloedge_auto", "edge":
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
