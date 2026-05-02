// redboxq — analytics dashboard for crucible red-team runs.
package main

import (
	"context"
	"errors"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/crucible/redboxq/internal/alerts"
	"github.com/crucible/redboxq/internal/ch"
	"github.com/crucible/redboxq/internal/config"
	"github.com/crucible/redboxq/internal/server"
	"github.com/crucible/redboxq/internal/telemetry"
)

func main() {
	cfg, err := config.Load()
	if err != nil {
		log.Fatalf("config: %v", err)
	}

	shutdownOTel, err := telemetry.Init(cfg.OTLP.Endpoint, cfg.OTLP.Service)
	if err != nil {
		log.Printf("otel init: %v (continuing without)", err)
	}
	defer shutdownOTel()

	chc, err := ch.Open(cfg.CH.Addr, cfg.CH.Database, cfg.CH.Username, cfg.CH.Password)
	if err != nil {
		log.Fatalf("clickhouse: %v", err)
	}
	defer chc.Close()

	router, err := server.New(cfg, chc)
	if err != nil {
		log.Fatalf("server: %v", err)
	}

	engine := alerts.New(chc, alerts.Config{
		DiscordURL:  cfg.Alerts.DiscordURL,
		TelegramTok: cfg.Alerts.TelegramTok,
		TelegramCID: cfg.Alerts.TelegramCID,
	})
	go engine.Run(context.Background(), cfg.Alerts.Tick)

	srv := &http.Server{
		Addr:              cfg.ListenAddr,
		Handler:           router,
		ReadHeaderTimeout: 10 * time.Second,
	}

	stop := make(chan os.Signal, 1)
	signal.Notify(stop, os.Interrupt, syscall.SIGTERM)

	go func() {
		log.Printf("redboxq listening on %s (ch=%s, otel=%s)",
			cfg.ListenAddr, cfg.CH.Addr, cfg.OTLP.Endpoint)
		if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
			log.Fatalf("server: %v", err)
		}
	}()

	<-stop
	log.Print("shutting down…")
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	_ = srv.Shutdown(ctx)
}
