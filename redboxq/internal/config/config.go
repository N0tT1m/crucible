// Package config — env-based config loader for redboxq.
package config

import (
	"os"
	"strconv"
	"time"
)

type Config struct {
	ListenAddr string
	WebRoot    string
	StaticVer  string
	Service    string
	Vol        string
	IssueBase  time.Time

	CH struct {
		Addr     string
		Database string
		Username string
		Password string
	}

	OTLP struct {
		Endpoint string
		Service  string
	}

	Alerts struct {
		Tick        time.Duration
		DiscordURL  string
		TelegramTok string
		TelegramCID string
	}
}

func Load() (*Config, error) {
	c := &Config{
		ListenAddr: env("REDBOXQ_LISTEN_ADDR", ":7000"),
		WebRoot:    env("REDBOXQ_WEB_ROOT", "./web"),
		StaticVer:  env("REDBOXQ_STATIC_VER", strconv.FormatInt(time.Now().Unix(), 10)),
		Service:    env("OTEL_SERVICE_NAME", "redboxq"),
		Vol:        env("REDBOXQ_VOLUME", "I"),
		IssueBase:  time.Date(2026, 5, 1, 0, 0, 0, 0, time.UTC),
	}
	// Default to the redboxq host port (9001), not the ClickHouse default (9000)
	// — :9000 is taken by mommy-smoothies-morning-milking on the empire stack.
	c.CH.Addr = env("REDBOXQ_CH_ADDR", "localhost:9001")
	c.CH.Database = env("REDBOXQ_CH_DATABASE", "mart")
	c.CH.Username = env("REDBOXQ_CH_USERNAME", "default")
	c.CH.Password = env("REDBOXQ_CH_PASSWORD", "")

	c.OTLP.Endpoint = env("REDBOXQ_OTLP_ENDPOINT", "localhost:4327")
	c.OTLP.Service = c.Service

	tickStr := env("REDBOXQ_ALERT_TICK", "30s")
	tick, err := time.ParseDuration(tickStr)
	if err != nil {
		tick = 30 * time.Second
	}
	c.Alerts.Tick = tick
	c.Alerts.DiscordURL = env("REDBOXQ_DISCORD_WEBHOOK_URL", "")
	c.Alerts.TelegramTok = env("REDBOXQ_TELEGRAM_BOT_TOKEN", "")
	c.Alerts.TelegramCID = env("REDBOXQ_TELEGRAM_CHAT_ID", "")

	return c, nil
}

// IssueNo returns the daily issue number relative to IssueBase.
func (c *Config) IssueNo(t time.Time) int {
	d := int(t.Sub(c.IssueBase).Hours() / 24)
	if d < 1 {
		return 1
	}
	return d + 1
}

func env(k, def string) string {
	if v := os.Getenv(k); v != "" {
		return v
	}
	return def
}
