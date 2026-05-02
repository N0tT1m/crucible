// Package alerts — rule engine + Discord/Telegram fan-out.
package alerts

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"net/url"
	"sync"
	"time"

	"github.com/crucible/redboxq/internal/ch"
)

type Config struct {
	DiscordURL  string
	TelegramTok string
	TelegramCID string
}

type Rule interface {
	Name() string
	Cooldown() time.Duration
	Severity() string
	Evaluate(ctx context.Context, chc *ch.Client) (fired bool, summary string, err error)
}

type Engine struct {
	chc       *ch.Client
	cfg       Config
	rules     []Rule
	lastFire  map[string]time.Time
	mu        sync.Mutex
	httpc     *http.Client
}

func New(chc *ch.Client, cfg Config) *Engine {
	return &Engine{
		chc:      chc,
		cfg:      cfg,
		rules:    DefaultRules(),
		lastFire: map[string]time.Time{},
		httpc:    &http.Client{Timeout: 10 * time.Second},
	}
}

func (e *Engine) Run(ctx context.Context, tick time.Duration) {
	if tick <= 0 {
		tick = 30 * time.Second
	}
	t := time.NewTicker(tick)
	defer t.Stop()
	log.Printf("alerts: engine started, tick=%s, rules=%d", tick, len(e.rules))
	for {
		select {
		case <-ctx.Done():
			return
		case <-t.C:
			e.evalOnce(ctx)
		}
	}
}

func (e *Engine) evalOnce(ctx context.Context) {
	now := time.Now()
	for _, r := range e.rules {
		e.mu.Lock()
		last := e.lastFire[r.Name()]
		e.mu.Unlock()
		if !last.IsZero() && now.Sub(last) < r.Cooldown() {
			continue
		}
		ec, cancel := context.WithTimeout(ctx, 15*time.Second)
		fired, summary, err := r.Evaluate(ec, e.chc)
		cancel()
		if err != nil {
			if ch.MissingTable(err) {
				// Expected until migrations + dbt have run. Stay quiet.
				continue
			}
			log.Printf("alerts: %s: %v", r.Name(), err)
			continue
		}
		if !fired {
			continue
		}
		e.mu.Lock()
		e.lastFire[r.Name()] = now
		e.mu.Unlock()
		e.fanout(ctx, r, summary)
		e.persist(ctx, r, summary)
	}
}

func (e *Engine) fanout(ctx context.Context, r Rule, summary string) {
	body := fmt.Sprintf("[%s · %s] %s", r.Name(), r.Severity(), summary)

	if e.cfg.DiscordURL != "" {
		_ = e.discord(ctx, body)
	}
	if e.cfg.TelegramTok != "" && e.cfg.TelegramCID != "" {
		_ = e.telegram(ctx, body)
	}
	log.Printf("ALERT %s", body)
}

func (e *Engine) discord(ctx context.Context, body string) error {
	payload, _ := json.Marshal(map[string]string{"content": body})
	req, _ := http.NewRequestWithContext(ctx, "POST", e.cfg.DiscordURL, bytes.NewReader(payload))
	req.Header.Set("Content-Type", "application/json")
	resp, err := e.httpc.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	return nil
}

func (e *Engine) telegram(ctx context.Context, body string) error {
	api := fmt.Sprintf("https://api.telegram.org/bot%s/sendMessage", e.cfg.TelegramTok)
	form := url.Values{}
	form.Set("chat_id", e.cfg.TelegramCID)
	form.Set("text", body)
	req, _ := http.NewRequestWithContext(ctx, "POST", api, bytes.NewBufferString(form.Encode()))
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	resp, err := e.httpc.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	return nil
}

func (e *Engine) persist(ctx context.Context, r Rule, summary string) {
	row := map[string]any{
		"ts":        time.Now().UTC().Format(time.RFC3339Nano),
		"rule_name": r.Name(),
		"state":     "fired",
		"severity":  r.Severity(),
		"summary":   summary,
		"payload":   "{}",
		"fired_at":  time.Now().UTC().Format(time.RFC3339Nano),
	}
	body, _ := json.Marshal(row)
	c, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()
	if err := e.chc.InsertJSONEachRow(c, "mart.alerts", string(body)); err != nil {
		log.Printf("alerts: persist: %v", err)
	}
}
