package main

import (
	"strings"
	"testing"
)

func TestUserAgentForClientHelloID(t *testing.T) {
	ua := UserAgentForClientHelloID("HelloFirefox_120")
	if !strings.Contains(ua, "Firefox/120") {
		t.Fatalf("UA = %q, want Firefox/120", ua)
	}

	fallback := UserAgentForClientHelloID("HelloUnknown_1")
	if !strings.Contains(fallback, "Chrome/120") {
		t.Fatalf("fallback UA = %q, want Chrome/120", fallback)
	}
}

func TestFingerprintForClientRotation(t *testing.T) {
	cfg := DefaultConfig()
	cfg.TLSRotate = true
	cfg.TLSRotateList = []string{"HelloChrome_120", "HelloFirefox_120"}
	mgr := NewTLSFingerprintManager(cfg)

	id0, ua0 := mgr.FingerprintForClient(0)
	id1, ua1 := mgr.FingerprintForClient(1)
	id2, _ := mgr.FingerprintForClient(2)

	if id0 != "HelloChrome_120" || !strings.Contains(ua0, "Chrome/120") {
		t.Fatalf("index 0 = %s %s", id0, ua0)
	}
	if id1 != "HelloFirefox_120" || !strings.Contains(ua1, "Firefox/120") {
		t.Fatalf("index 1 = %s %s", id1, ua1)
	}
	if id2 != "HelloChrome_120" {
		t.Fatalf("index 2 = %s, want wrap to Chrome", id2)
	}
}

func TestFingerprintForClientFixed(t *testing.T) {
	cfg := DefaultConfig()
	cfg.TLSRotate = false
	cfg.TLSClientID = "HelloFirefox_105"
	mgr := NewTLSFingerprintManager(cfg)

	id, ua := mgr.FingerprintForClient(7)
	if id != "HelloFirefox_105" {
		t.Fatalf("id = %s, want HelloFirefox_105", id)
	}
	if !strings.Contains(ua, "Firefox/105") {
		t.Fatalf("ua = %s", ua)
	}
}
