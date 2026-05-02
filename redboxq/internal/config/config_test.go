package config

import (
	"testing"
	"time"
)

func TestLoadDefaults(t *testing.T) {
	t.Setenv("REDBOXQ_LISTEN_ADDR", "")
	t.Setenv("REDBOXQ_CH_ADDR", "")
	t.Setenv("REDBOXQ_OTLP_ENDPOINT", "")
	t.Setenv("REDBOXQ_DISCORD_WEBHOOK_URL", "")

	c, err := Load()
	if err != nil {
		t.Fatalf("Load: %v", err)
	}
	if c.ListenAddr != ":7000" {
		t.Errorf("default listen addr = %q, want :7000", c.ListenAddr)
	}
	// defaults should target the redboxq host port (9001), not the CH default
	// (9000) which is taken by mommy-smoothies-morning-milking on the empire.
	if c.CH.Addr != "localhost:9001" {
		t.Errorf("default ch addr = %q, want localhost:9001", c.CH.Addr)
	}
	if c.OTLP.Endpoint != "localhost:4327" {
		t.Errorf("default otlp = %q, want localhost:4327", c.OTLP.Endpoint)
	}
	if c.Alerts.Tick != 30*time.Second {
		t.Errorf("default tick = %s, want 30s", c.Alerts.Tick)
	}
}

func TestLoadOverrides(t *testing.T) {
	t.Setenv("REDBOXQ_LISTEN_ADDR", ":9999")
	t.Setenv("REDBOXQ_CH_ADDR", "ch.example:9000")
	t.Setenv("REDBOXQ_ALERT_TICK", "5m")

	c, err := Load()
	if err != nil {
		t.Fatalf("Load: %v", err)
	}
	if c.ListenAddr != ":9999" {
		t.Errorf("listen addr = %q", c.ListenAddr)
	}
	if c.CH.Addr != "ch.example:9000" {
		t.Errorf("ch addr = %q", c.CH.Addr)
	}
	if c.Alerts.Tick != 5*time.Minute {
		t.Errorf("tick = %s", c.Alerts.Tick)
	}
}

func TestIssueNo(t *testing.T) {
	c, _ := Load()
	c.IssueBase = time.Date(2026, 1, 1, 0, 0, 0, 0, time.UTC)

	cases := []struct {
		t    time.Time
		want int
	}{
		{time.Date(2026, 1, 1, 12, 0, 0, 0, time.UTC), 1}, // base day
		{time.Date(2025, 6, 1, 0, 0, 0, 0, time.UTC), 1},  // pre-base clamps
		{time.Date(2026, 1, 10, 0, 0, 0, 0, time.UTC), 10},
		{time.Date(2027, 1, 1, 0, 0, 0, 0, time.UTC), 366},
	}
	for _, tc := range cases {
		got := c.IssueNo(tc.t)
		if got != tc.want {
			t.Errorf("IssueNo(%s) = %d, want %d", tc.t, got, tc.want)
		}
	}
}
