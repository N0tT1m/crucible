// Package ch — ClickHouse query layer.
package ch

import (
	"context"
	"fmt"
	"strings"
	"time"

	"github.com/ClickHouse/clickhouse-go/v2"
	"github.com/ClickHouse/clickhouse-go/v2/lib/driver"
)

type Client struct {
	conn driver.Conn
	DB   string
}

func Open(addr, database, user, pass string) (*Client, error) {
	conn, err := clickhouse.Open(&clickhouse.Options{
		Addr: []string{addr},
		Auth: clickhouse.Auth{
			Database: database,
			Username: user,
			Password: pass,
		},
		DialTimeout: 5 * time.Second,
		Compression: &clickhouse.Compression{Method: clickhouse.CompressionLZ4},
	})
	if err != nil {
		return nil, err
	}
	if err := conn.Ping(context.Background()); err != nil {
		return nil, fmt.Errorf("ping: %w", err)
	}
	return &Client{conn: conn, DB: database}, nil
}

func (c *Client) Close() error { return c.conn.Close() }

// hasLimit returns true if upper-cased SQL already has a top-level LIMIT.
// Naive but works for our queries — we don't have subqueries with LIMIT
// that would confuse it.
func hasLimit(upperSQL string) bool {
	// Strip a trailing semicolon if any.
	s := strings.TrimRight(strings.TrimSpace(upperSQL), ";")
	// Last 100 chars are enough to find a tail LIMIT clause.
	if len(s) > 100 {
		s = s[len(s)-100:]
	}
	return strings.Contains(s, "LIMIT ") || strings.HasSuffix(s, "LIMIT")
}

// Conn returns the underlying driver.Conn for callers that need it
// (currently the ingest package, which uses InsertJSONEachRow).
func (c *Client) Conn() driver.Conn { return c.conn }

// InsertJSONEachRow uses the AsyncInsert path with a JSONEachRow body.
// `body` is one or more newline-delimited JSON objects.
// Used by /ingest/* endpoints.
func (c *Client) InsertJSONEachRow(ctx context.Context, fqTable, body string) error {
	q := fmt.Sprintf("INSERT INTO %s FORMAT JSONEachRow %s", fqTable, body)
	return c.conn.AsyncInsert(ctx, q, false)
}

// ── front page ──

type FrontStats struct {
	RunsToday    uint64
	AttacksToday uint64
	Errors       uint64
	Refused      uint64
	RefusalPct   float64
	LastAttackTS time.Time
}

func (c *Client) FrontStats(ctx context.Context) (FrontStats, error) {
	var s FrontStats
	row := c.conn.QueryRow(ctx, `
		SELECT
			uniqExact(run_id),
			count(),
			countIf(error != ''),
			countIf(verdict = 'refused'),
			countIf(verdict = 'refused') / nullIf(count(), 0),
			max(ts)
		FROM mart.fact_attack
		WHERE ts >= today()
	`)
	var refusalPct *float64
	var ts *time.Time
	err := row.Scan(&s.RunsToday, &s.AttacksToday, &s.Errors, &s.Refused, &refusalPct, &ts)
	if err != nil {
		return s, err
	}
	if refusalPct != nil {
		s.RefusalPct = *refusalPct
	}
	if ts != nil {
		s.LastAttackTS = *ts
	}
	return s, nil
}

// ── attacks ──

type AttackRow struct {
	TS        time.Time
	RunID     string
	Target    string
	Payload   string
	Model     string
	Verdict   string
	LatencyMs uint32
	InTokens  uint32
	OutTokens uint32
	JudgeName string
	Conf      *float64
	Error     string
}

func (c *Client) RecentAttacks(ctx context.Context, limit int) ([]AttackRow, error) {
	if limit <= 0 || limit > 5000 {
		limit = 100
	}
	rows, err := c.conn.Query(ctx, `
		SELECT ts, run_id, target_name, payload_id, model, verdict,
		       latency_ms, input_tokens, output_tokens,
		       judge_name, confidence, error
		FROM mart.fact_attack
		ORDER BY ts DESC
		LIMIT ?
	`, limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var out []AttackRow
	for rows.Next() {
		var r AttackRow
		if err := rows.Scan(
			&r.TS, &r.RunID, &r.Target, &r.Payload, &r.Model, &r.Verdict,
			&r.LatencyMs, &r.InTokens, &r.OutTokens,
			&r.JudgeName, &r.Conf, &r.Error,
		); err != nil {
			return nil, err
		}
		out = append(out, r)
	}
	return out, rows.Err()
}

func (c *Client) Attack(ctx context.Context, runID, target, payload string, ts time.Time) (*AttackRow, error) {
	row := c.conn.QueryRow(ctx, `
		SELECT ts, run_id, target_name, payload_id, model, verdict,
		       latency_ms, input_tokens, output_tokens,
		       judge_name, confidence, error
		FROM mart.fact_attack
		WHERE run_id = ? AND target_name = ? AND payload_id = ? AND ts = ?
		LIMIT 1
	`, runID, target, payload, ts)
	var r AttackRow
	if err := row.Scan(
		&r.TS, &r.RunID, &r.Target, &r.Payload, &r.Model, &r.Verdict,
		&r.LatencyMs, &r.InTokens, &r.OutTokens,
		&r.JudgeName, &r.Conf, &r.Error,
	); err != nil {
		return nil, err
	}
	return &r, nil
}

// ── targets ──

type TargetCard struct {
	Name       string
	Provider   string
	Family     string
	RefusalPct float64
	Attempts   uint64
	Errors     uint64
	LastSeen   time.Time
}

func (c *Client) TargetCards(ctx context.Context) ([]TargetCard, error) {
	rows, err := c.conn.Query(ctx, `
		SELECT
			m.model_name,
			any(m.provider),
			any(m.family),
			countIf(a.verdict = 'refused') / nullIf(count(a.run_id), 0),
			count(a.run_id),
			countIf(a.error != ''),
			max(a.ts)
		FROM mart.dim_model m
		LEFT JOIN mart.fact_attack a
		  ON a.model = m.model_name AND a.ts >= today() - 7
		GROUP BY m.model_name
		ORDER BY count(a.run_id) DESC
	`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var out []TargetCard
	for rows.Next() {
		var t TargetCard
		var refusal *float64
		var last *time.Time
		if err := rows.Scan(&t.Name, &t.Provider, &t.Family, &refusal, &t.Attempts, &t.Errors, &last); err != nil {
			return nil, err
		}
		if refusal != nil {
			t.RefusalPct = *refusal
		}
		if last != nil {
			t.LastSeen = *last
		}
		out = append(out, t)
	}
	return out, rows.Err()
}

// Freshness buckets a last-seen timestamp.
func Freshness(last time.Time) string {
	if last.IsZero() {
		return "cold"
	}
	d := time.Since(last)
	switch {
	case d < 6*time.Hour:
		return "fresh"
	case d < 24*time.Hour:
		return "warm"
	case d < 7*24*time.Hour:
		return "stale"
	default:
		return "cold"
	}
}

// ── payloads ──

type PayloadRow struct {
	ID            string
	Name          string
	Category      string
	Tags          string
	Refs          string
	Attempts7d    uint64
	ComplianceRate float64
}

func (c *Client) Payloads(ctx context.Context) ([]PayloadRow, error) {
	rows, err := c.conn.Query(ctx, `
		SELECT
			p.payload_id,
			p.name,
			p.category,
			p.tags,
			p.references,
			countIf(a.run_id != '') AS attempts,
			countIf(a.verdict = 'complied') / nullIf(attempts, 0)
		FROM mart.dim_payload p
		LEFT JOIN mart.fact_attack a
		  ON a.payload_id = p.payload_id AND a.ts >= today() - 7
		GROUP BY p.payload_id, p.name, p.category, p.tags, p.references
		ORDER BY attempts DESC
	`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var out []PayloadRow
	for rows.Next() {
		var r PayloadRow
		var rate *float64
		if err := rows.Scan(&r.ID, &r.Name, &r.Category, &r.Tags, &r.Refs, &r.Attempts7d, &rate); err != nil {
			return nil, err
		}
		if rate != nil {
			r.ComplianceRate = *rate
		}
		out = append(out, r)
	}
	return out, rows.Err()
}

// ── runs ──

type RunRow struct {
	RunID       string
	Started     time.Time
	Finished    time.Time
	Models      string
	Attacks     uint64
	Errors      uint64
	RefusalRate float64
}

func (c *Client) Runs(ctx context.Context, limit int) ([]RunRow, error) {
	if limit <= 0 || limit > 1000 {
		limit = 50
	}
	rows, err := c.conn.Query(ctx, `
		SELECT
			run_id,
			min(ts), max(ts),
			arrayStringConcat(groupUniqArray(model), ','),
			count(),
			countIf(error != ''),
			countIf(verdict = 'refused') / nullIf(count(), 0)
		FROM mart.fact_attack
		GROUP BY run_id
		ORDER BY min(ts) DESC
		LIMIT ?
	`, limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var out []RunRow
	for rows.Next() {
		var r RunRow
		var rate *float64
		if err := rows.Scan(&r.RunID, &r.Started, &r.Finished, &r.Models, &r.Attacks, &r.Errors, &rate); err != nil {
			return nil, err
		}
		if rate != nil {
			r.RefusalRate = *rate
		}
		out = append(out, r)
	}
	return out, rows.Err()
}

// ── judges ──

type JudgeAgreementRow struct {
	RegexVerdict string
	LLMVerdict   string
	Count        uint64
	Agreed       bool
}

func (c *Client) JudgeAgreement(ctx context.Context) ([]JudgeAgreementRow, error) {
	rows, err := c.conn.Query(ctx, `
		SELECT regex_verdict, llm_verdict, count(), regex_verdict = llm_verdict
		FROM mart.mart_judge_agreement
		GROUP BY regex_verdict, llm_verdict
		ORDER BY count() DESC
	`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []JudgeAgreementRow
	for rows.Next() {
		var r JudgeAgreementRow
		if err := rows.Scan(&r.RegexVerdict, &r.LLMVerdict, &r.Count, &r.Agreed); err != nil {
			return nil, err
		}
		out = append(out, r)
	}
	return out, rows.Err()
}

// ── canaries ──

type CanaryRow struct {
	TS      time.Time
	Service string
	Token   string
	Body    string
	TraceID string
}

func (c *Client) RecentCanaries(ctx context.Context, since time.Duration) ([]CanaryRow, error) {
	rows, err := c.conn.Query(ctx, `
		SELECT ts, service, canary_token, log_body, trace_id
		FROM mart.fact_canary_hit
		WHERE ts >= now() - INTERVAL ? SECOND
		ORDER BY ts DESC
		LIMIT 100
	`, int(since.Seconds()))
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []CanaryRow
	for rows.Next() {
		var r CanaryRow
		if err := rows.Scan(&r.TS, &r.Service, &r.Token, &r.Body, &r.TraceID); err != nil {
			return nil, err
		}
		out = append(out, r)
	}
	return out, rows.Err()
}

// ── workbench ──

type QueryResult struct {
	Cols []string
	Rows [][]any
}

func (c *Client) RunQuery(ctx context.Context, sql string, limit int) (*QueryResult, error) {
	if limit <= 0 || limit > 50000 {
		limit = 10000
	}
	upper := strings.ToUpper(strings.TrimSpace(sql))
	for _, banned := range []string{"INSERT", "ALTER", "DROP", "TRUNCATE", "RENAME", "ATTACH", "DETACH", "CREATE", "DELETE", "OPTIMIZE", "GRANT", "REVOKE"} {
		if strings.HasPrefix(upper, banned) {
			return nil, fmt.Errorf("workbench is read-only; %s is not allowed", banned)
		}
	}
	// Only append LIMIT when the caller hasn't already.
	finalSQL := sql
	if !hasLimit(upper) {
		finalSQL = fmt.Sprintf("%s\nLIMIT %d", sql, limit)
	}
	rows, err := c.conn.Query(ctx, finalSQL)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	cts := rows.ColumnTypes()
	cols := make([]string, len(cts))
	for i, ct := range cts {
		cols[i] = ct.Name()
	}
	out := &QueryResult{Cols: cols}
	for rows.Next() {
		vals := make([]any, len(cols))
		ptrs := make([]any, len(cols))
		for i := range vals {
			ptrs[i] = &vals[i]
		}
		if err := rows.Scan(ptrs...); err != nil {
			return nil, err
		}
		out.Rows = append(out.Rows, vals)
	}
	return out, rows.Err()
}

// ── lineage ──

type Node struct {
	DB   string
	Name string
}

func (c *Client) Tables(ctx context.Context) (map[string][]string, error) {
	rows, err := c.conn.Query(ctx, `
		SELECT database, name FROM system.tables
		WHERE database IN ('raw','stg','mart')
		  AND engine NOT LIKE '%View%' OR engine LIKE '%View%'
		ORDER BY database, name
	`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	out := map[string][]string{}
	for rows.Next() {
		var db, name string
		if err := rows.Scan(&db, &name); err != nil {
			return nil, err
		}
		out[db] = append(out[db], name)
	}
	return out, rows.Err()
}

// ── log tail ──

type LogRow struct {
	TS       time.Time
	Severity string
	Service  string
	Body     string
	TraceID  string
}

func (c *Client) RecentLogs(ctx context.Context, limit int) ([]LogRow, error) {
	if limit <= 0 || limit > 1000 {
		limit = 200
	}
	rows, err := c.conn.Query(ctx, `
		SELECT Timestamp, SeverityText, ServiceName, Body, TraceId
		FROM raw.otel_logs
		ORDER BY Timestamp DESC
		LIMIT ?
	`, limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []LogRow
	for rows.Next() {
		var r LogRow
		if err := rows.Scan(&r.TS, &r.Severity, &r.Service, &r.Body, &r.TraceID); err != nil {
			return nil, err
		}
		out = append(out, r)
	}
	return out, rows.Err()
}
