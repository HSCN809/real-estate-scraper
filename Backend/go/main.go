package main

import (
	"context"
	"fmt"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/rs/zerolog"
	"github.com/rs/zerolog/log"
)

func main() {
	// Setup structured logging
	zerolog.TimeFieldFormat = zerolog.TimeFormatUnix
	zerolog.SetGlobalLevel(zerolog.InfoLevel)

	// JSON structured logging for production
	if os.Getenv("ENVIRONMENT") == "production" {
		log.Logger = zerolog.New(os.Stdout).With().
			Timestamp().
			Str("service", "invisible-proxy").
			Logger()
	} else {
		// Console writer for development
		log.Logger = log.Output(zerolog.ConsoleWriter{Out: os.Stdout})
	}

	// Enable debug mode if specified
	if os.Getenv("DEBUG") == "true" {
		zerolog.SetGlobalLevel(zerolog.DebugLevel)
		log.Debug().Msg("Debug logging enabled")
	}

	log.Info().
		Str("version", "1.0.0").
		Msg("Invisible Go Proxy Server Starting...")

	// Load configuration
	config := LoadConfigFromEnv()
	log.Info().
		Str("host", config.Host).
		Int("port", config.Port).
		Bool("mobile_proxy", config.UseMobileProxy).
		Bool("tls_rotate", config.TLSRotate).
		Int("tls_fingerprints", len(config.TLSRotateList)).
		Bool("api_key_set", config.APIKey != "").
		Int("rate_limit", config.RateLimit).
		Int("rate_burst", config.RateLimitBurst).
		Msg("Configuration loaded")

	// Initialize components
	tlsManager := NewTLSFingerprintManager(config)
	log.Info().Str("tls_client_id", config.TLSClientID).Msg("TLS fingerprint manager initialized")

	clientPool := NewClientPool(config, tlsManager)
	defer clientPool.Close()

	proxyHandler := NewProxyHandler(config, clientPool, tlsManager)

	// Create HTTP server
	server := &http.Server{
		Addr:         fmt.Sprintf("%s:%d", config.Host, config.Port),
		Handler:      proxyHandler,
		ReadTimeout:  config.ReadTimeout,
		WriteTimeout: config.WriteTimeout,
		IdleTimeout:  90 * time.Second,
	}

	// Start server in goroutine
	serverErrors := make(chan error, 1)
	go func() {
		log.Info().
			Str("address", fmt.Sprintf("%s:%d", config.Host, config.Port)).
			Msg("Server listening")
		serverErrors <- server.ListenAndServe()
	}()

	// Setup graceful shutdown
	shutdown := make(chan os.Signal, 1)
	signal.Notify(shutdown, os.Interrupt, syscall.SIGTERM)

	// Wait for shutdown signal or server error
	select {
	case err := <-serverErrors:
		log.Fatal().Err(err).Msg("Server failed")
	case sig := <-shutdown:
		log.Info().Msgf("Received signal %v, shutting down gracefully...", sig)
	}

	// Graceful shutdown with timeout
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	// Shutdown server
	if err := server.Shutdown(ctx); err != nil {
		log.Error().Err(err).Msg("Server shutdown error")
	}

	log.Info().Msg("Server stopped gracefully")
}

// Health check endpoint (can be called from handler.go)
func setupHealthCheckHandler() http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		w.Write([]byte(`{"status":"ok","service":"invisible-proxy"}`))
	}
}
