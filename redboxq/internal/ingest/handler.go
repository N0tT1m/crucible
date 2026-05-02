// Package ingest — POST /ingest/* + /attacks/{id}/label endpoints.
package ingest

import (
	"context"
	"encoding/json"
	"net/http"
	"time"

	"github.com/ClickHouse/clickhouse-go/v2/lib/driver"

	"github.com/crucible/redboxq/internal/ch"
)

type Deps struct {
	CH *ch.Client
}

// Helper that exposes the underlying conn for ingest writes.
func (d *Deps) conn() driver.Conn {
	type connHolder interface{ Conn() driver.Conn }
	if h, ok := any(d.CH).(connHolder); ok {
		return h.Conn()
	}
	return nil
}

// AttackPayload mirrors the raw.attacks row shape for /ingest/attack.
type AttackPayload struct {
	TS               string   `json:"ts"`
	RunID            string   `json:"run_id"`
	PayloadID        string   `json:"payload_id"`
	TargetName       string   `json:"target_name"`
	Model            string   `json:"model"`
	RenderedPrompt   string   `json:"rendered_prompt"`
	SystemPrompt     string   `json:"system_prompt"`
	TemplateHash     string   `json:"template_hash"`
	ParentPayloadID  string   `json:"parent_payload_id"`
	Response         string   `json:"response"`
	LatencyMs        uint32   `json:"latency_ms"`
	InputTokens      uint32   `json:"input_tokens"`
	OutputTokens     uint32   `json:"output_tokens"`
	FinishReason     string   `json:"finish_reason"`
	ModelFingerprint string   `json:"model_fingerprint"`
	Temperature      *float32 `json:"temperature"`
	TopP             *float32 `json:"top_p"`
	TopK             *int32   `json:"top_k"`
	Seed             *int64   `json:"seed"`
	Verdict          string   `json:"verdict"`
	Confidence       *float32 `json:"confidence"`
	JudgeName        string   `json:"judge_name"`
	JudgeReason      string   `json:"judge_reason"`
	Error            string   `json:"error"`
	ErrorKind        string   `json:"error_kind"`
	BaseURL          string   `json:"base_url"`
	CallerUser       string   `json:"caller_user"`
	UsdAtAttack      *float64 `json:"usd_at_attack"`
	TraceID          string   `json:"trace_id"`
}

func (d *Deps) Attack(w http.ResponseWriter, r *http.Request) {
	var p AttackPayload
	if err := json.NewDecoder(r.Body).Decode(&p); err != nil {
		http.Error(w, "bad json: "+err.Error(), 400)
		return
	}
	if p.RunID == "" || p.PayloadID == "" || p.TargetName == "" {
		http.Error(w, "run_id, payload_id, target_name required", 400)
		return
	}
	// Insert via the same JSONEachRow path as the Python sink.
	body, _ := json.Marshal(p)
	ctx, cancel := context.WithTimeout(r.Context(), 5*time.Second)
	defer cancel()
	if err := d.CH.InsertJSONEachRow(ctx, "raw.attacks", string(body)); err != nil {
		http.Error(w, "ch insert: "+err.Error(), 500)
		return
	}
	w.WriteHeader(http.StatusAccepted)
	_, _ = w.Write([]byte(`{"ok":true}`))
}

// OutboxPayload mirrors raw.outbox_events.
type OutboxPayload struct {
	TS         string `json:"ts"`
	SessionID  string `json:"session_id"`
	Model      string `json:"model"`
	ToAddr     string `json:"to_addr"`
	Subject    string `json:"subject"`
	Body       string `json:"body"`
	TraceID    string `json:"trace_id"`
}

func (d *Deps) Outbox(w http.ResponseWriter, r *http.Request) {
	var p OutboxPayload
	if err := json.NewDecoder(r.Body).Decode(&p); err != nil {
		http.Error(w, "bad json: "+err.Error(), 400)
		return
	}
	body, _ := json.Marshal(p)
	ctx, cancel := context.WithTimeout(r.Context(), 5*time.Second)
	defer cancel()
	if err := d.CH.InsertJSONEachRow(ctx, "raw.outbox_events", string(body)); err != nil {
		http.Error(w, "ch insert: "+err.Error(), 500)
		return
	}
	w.WriteHeader(http.StatusAccepted)
}

// LabelRequest is what the UI form posts.
type LabelRequest struct {
	RunID       string `json:"run_id"`
	PayloadID   string `json:"payload_id"`
	TargetName  string `json:"target_name"`
	TS          string `json:"ts"`            // ISO8601 of the attack
	Label       string `json:"label"`         // refused|complied|partial|unknown
	RefusalKind string `json:"refusal_kind"`  // safety|capability|format|hedge|''
	Severity    string `json:"severity"`      // low|med|high|''
	Notes       string `json:"notes"`
	LabeledBy   string `json:"labeled_by"`
}

func (d *Deps) Label(w http.ResponseWriter, r *http.Request) {
	var lr LabelRequest
	if err := json.NewDecoder(r.Body).Decode(&lr); err != nil {
		http.Error(w, "bad json: "+err.Error(), 400)
		return
	}
	switch lr.Label {
	case "refused", "complied", "partial", "unknown":
	default:
		http.Error(w, "label must be one of refused|complied|partial|unknown", 400)
		return
	}
	if lr.LabeledBy == "" {
		lr.LabeledBy = "anon"
	}
	row, _ := json.Marshal(map[string]any{
		"run_id":       lr.RunID,
		"payload_id":   lr.PayloadID,
		"target_name":  lr.TargetName,
		"ts":           lr.TS,
		"label":        lr.Label,
		"refusal_kind": lr.RefusalKind,
		"severity":     lr.Severity,
		"notes":        lr.Notes,
		"labeled_by":   lr.LabeledBy,
	})
	ctx, cancel := context.WithTimeout(r.Context(), 5*time.Second)
	defer cancel()
	if err := d.CH.InsertJSONEachRow(ctx, "mart.dim_label", string(row)); err != nil {
		http.Error(w, "ch insert: "+err.Error(), 500)
		return
	}
	w.WriteHeader(http.StatusCreated)
	_, _ = w.Write([]byte(`{"ok":true}`))
}
