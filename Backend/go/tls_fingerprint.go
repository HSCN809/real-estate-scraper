package main

import (
	"context"
	"net"
	"strings"
	"time"

	utls "github.com/refraction-networking/utls"
)

// TLSFingerprintManager manages TLS fingerprint spoofing
type TLSFingerprintManager struct {
	config *Config
}

// NewTLSFingerprintManager creates a new TLS fingerprint manager
func NewTLSFingerprintManager(cfg *Config) *TLSFingerprintManager {
	return &TLSFingerprintManager{
		config: cfg,
	}
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

	tlsConfig := &utls.Config{
		ServerName:         serverName,
		MinVersion:         utls.VersionTLS12,
		MaxVersion:         utls.VersionTLS13,
		InsecureSkipVerify: false,
		NextProtos:         []string{"http/1.1"},
	}

	clientHelloID := tfm.resolveClientHelloID(tfm.config.TLSClientID)
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
	case "hellofirefox_120", "hellofirefox_auto", "firefox":
		return utls.HelloFirefox_Auto
	case "helloedge_120", "helloedge_auto", "edge":
		return utls.HelloEdge_Auto
	case "hellosafari_auto", "safari":
		return utls.HelloSafari_Auto
	case "hellorandomized", "randomized":
		return utls.HelloRandomized
	case "hellorandomizedalpn", "randomizedalpn":
		return utls.HelloRandomizedALPN
	default:
		return utls.HelloChrome_Auto
	}
}
