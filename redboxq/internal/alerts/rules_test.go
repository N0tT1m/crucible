package alerts

import (
	"testing"
	"time"
)

func TestDefaultRules(t *testing.T) {
	rs := DefaultRules()
	if len(rs) != 4 {
		t.Fatalf("expected 4 default rules, got %d", len(rs))
	}
	names := map[string]bool{}
	for _, r := range rs {
		names[r.Name()] = true
		if r.Cooldown() <= 0 {
			t.Errorf("%s has zero cooldown", r.Name())
		}
		if r.Severity() == "" {
			t.Errorf("%s has empty severity", r.Name())
		}
	}
	for _, want := range []string{"canary_hit", "error_rate", "refusal_drift", "silent_producer"} {
		if !names[want] {
			t.Errorf("missing rule: %s", want)
		}
	}
}

func TestRuleCooldownsAreReasonable(t *testing.T) {
	// canary_hit must be reactive (≤ 10 min); silent_producer can be slow.
	for _, r := range DefaultRules() {
		switch r.Name() {
		case "canary_hit":
			if r.Cooldown() > 10*time.Minute {
				t.Errorf("canary_hit cooldown %s is too slow", r.Cooldown())
			}
		case "silent_producer":
			if r.Cooldown() < 1*time.Hour {
				t.Errorf("silent_producer cooldown %s is too noisy", r.Cooldown())
			}
		}
	}
}
