// Package alerts — built-in rule kinds.
package alerts

import (
	"context"
	"fmt"
	"time"

	"github.com/crucible/redboxq/internal/ch"
)

func DefaultRules() []Rule {
	return []Rule{
		&CanaryHit{Cool: 5 * time.Minute},
		&ErrorRate{Window: 10 * time.Minute, Threshold: 0.10, Cool: 15 * time.Minute},
		&RefusalDrift{ZThreshold: 2.5, Cool: 6 * time.Hour},
		&SilentProducer{Threshold: 24 * time.Hour, Cool: 6 * time.Hour},
	}
}

// CanaryHit fires whenever any new row appears in mart.fact_canary_hit.
type CanaryHit struct {
	Cool time.Duration
}

func (r *CanaryHit) Name() string            { return "canary_hit" }
func (r *CanaryHit) Cooldown() time.Duration { return r.Cool }
func (r *CanaryHit) Severity() string        { return "critical" }
func (r *CanaryHit) Evaluate(ctx context.Context, chc *ch.Client) (bool, string, error) {
	rows, err := chc.RecentCanaries(ctx, r.Cool*2) // a window slightly larger than cooldown
	if err != nil {
		return false, "", err
	}
	if len(rows) == 0 {
		return false, "", nil
	}
	return true, fmt.Sprintf("%d canary hit(s) in last %s — service=%s token=%s",
		len(rows), r.Cool*2, rows[0].Service, rows[0].Token), nil
}

// ErrorRate fires when error fraction over Window exceeds Threshold.
type ErrorRate struct {
	Window    time.Duration
	Threshold float64
	Cool      time.Duration
}

func (r *ErrorRate) Name() string            { return "error_rate" }
func (r *ErrorRate) Cooldown() time.Duration { return r.Cool }
func (r *ErrorRate) Severity() string        { return "warn" }
func (r *ErrorRate) Evaluate(ctx context.Context, chc *ch.Client) (bool, string, error) {
	res, err := chc.RunQuery(ctx, fmt.Sprintf(`
		SELECT model,
		       countIf(error != '') / nullIf(count(), 0) AS error_rate,
		       count() AS n
		FROM raw.attacks
		WHERE ts >= now() - INTERVAL %d SECOND
		GROUP BY model
		HAVING n >= 10 AND error_rate >= %f
		ORDER BY error_rate DESC
		LIMIT 5
	`, int(r.Window.Seconds()), r.Threshold), 50)
	if err != nil {
		return false, "", err
	}
	if len(res.Rows) == 0 {
		return false, "", nil
	}
	first := res.Rows[0]
	return true, fmt.Sprintf("model=%v error_rate=%v over %s (n=%v)",
		first[0], first[1], r.Window, first[2]), nil
}

// RefusalDrift fires when today's refusal rate for a (model, category)
// pair drifts > N standard deviations from the trailing-14d mean.
type RefusalDrift struct {
	ZThreshold float64
	Cool       time.Duration
}

func (r *RefusalDrift) Name() string            { return "refusal_drift" }
func (r *RefusalDrift) Cooldown() time.Duration { return r.Cool }
func (r *RefusalDrift) Severity() string        { return "warn" }
func (r *RefusalDrift) Evaluate(ctx context.Context, chc *ch.Client) (bool, string, error) {
	res, err := chc.RunQuery(ctx, fmt.Sprintf(`
		WITH baseline AS (
			SELECT model, category,
			       avg(refusal_rate) AS mu,
			       stddevSamp(refusal_rate) AS sigma
			FROM mart.mart_refusal_rate
			WHERE day BETWEEN today() - 14 AND today() - 1
			GROUP BY model, category
			HAVING sigma > 0
		),
		today_rate AS (
			SELECT model, category, refusal_rate AS today
			FROM mart.mart_refusal_rate
			WHERE day = today()
		)
		SELECT b.model, b.category, t.today, b.mu, abs(t.today - b.mu) / b.sigma AS z
		FROM baseline b
		JOIN today_rate t USING (model, category)
		WHERE z >= %f
		ORDER BY z DESC
		LIMIT 5
	`, r.ZThreshold), 50)
	if err != nil {
		return false, "", err
	}
	if len(res.Rows) == 0 {
		return false, "", nil
	}
	first := res.Rows[0]
	return true, fmt.Sprintf("drift on %v/%v: today=%v mu=%v z=%v",
		first[0], first[1], first[2], first[3], first[4]), nil
}

// SilentProducer fires when no rows have arrived from raw.attacks for
// longer than Threshold.
type SilentProducer struct {
	Threshold time.Duration
	Cool      time.Duration
}

func (r *SilentProducer) Name() string            { return "silent_producer" }
func (r *SilentProducer) Cooldown() time.Duration { return r.Cool }
func (r *SilentProducer) Severity() string        { return "info" }
func (r *SilentProducer) Evaluate(ctx context.Context, chc *ch.Client) (bool, string, error) {
	res, err := chc.RunQuery(ctx, `SELECT max(ts) FROM raw.attacks`, 1)
	if err != nil {
		return false, "", err
	}
	if len(res.Rows) == 0 || res.Rows[0][0] == nil {
		return true, "no attacks ever recorded", nil
	}
	last, ok := res.Rows[0][0].(time.Time)
	if !ok {
		return false, "", nil
	}
	if time.Since(last) > r.Threshold {
		return true, fmt.Sprintf("no attacks in %s (last at %s)",
			r.Threshold, last.Format(time.RFC3339)), nil
	}
	return false, "", nil
}
