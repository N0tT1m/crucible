// Package handlers — per-page HTTP handlers for redboxq.
package handlers

import (
	"context"
	"fmt"
	"html/template"
	"log"
	"net/http"
	"strconv"
	"strings"
	"time"

	"github.com/go-chi/chi/v5"

	"github.com/crucible/redboxq/internal/ch"
	"github.com/crucible/redboxq/internal/config"
)

type Deps struct {
	Config    *config.Config
	CH        *ch.Client
	Templates map[string]*template.Template
	Now       func() time.Time
}

// ── shell ────────────────────────────────────────────────────────────

type Section struct {
	Slug, Name, Blurb string
}

var sections = []Section{
	{"/", "Front", "Today's bench at a glance"},
	{"/runs", "Runs", "Every bench, last 30 days"},
	{"/attacks", "Attacks", "Single-row drill-down"},
	{"/payloads", "Payloads", "Vault + efficacy"},
	{"/models", "Targets", "Per-model refusal trend"},
	{"/judges", "Judges", "Regex vs LLM agreement"},
	{"/lineage", "Lineage", "dbt model graph"},
	{"/workbench", "Workbench", "Ad-hoc SQL"},
	{"/logs", "Logs", "Live tail"},
	{"/reference", "Reference", "What every page does"},
}

type shell struct {
	Title     string
	Today     string
	FiledTime string
	Vol       string
	Issue     int
	Tagline   string
	Port      string
	Service   string
	Sections  []Section
	Current   string
	StaticV   string
}

func (d *Deps) shell(currentSlug string) shell {
	t := d.Now()
	port := d.Config.ListenAddr
	if len(port) > 0 && port[0] == ':' {
		port = port[1:]
	}
	return shell{
		Today:     t.Format("Monday, January 2, 2006"),
		FiledTime: t.Format("15:04"),
		Vol:       d.Config.Vol,
		Issue:     d.Config.IssueNo(t),
		Tagline:   "A daily read on red-team attacks, judges, and target drift.",
		Port:      port,
		Service:   d.Config.Service,
		Sections:  sections,
		Current:   currentSlug,
		StaticV:   d.Config.StaticVer,
	}
}

func (d *Deps) Render(w http.ResponseWriter, page string, data any) {
	t, ok := d.Templates[page]
	if !ok {
		http.Error(w, "template not found: "+page, http.StatusInternalServerError)
		return
	}
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	if err := t.ExecuteTemplate(w, "base.html", data); err != nil {
		log.Printf("render %s: %v", page, err)
	}
}

// reqCtx returns a context bounded by the request, with a 30s ceiling.
func reqCtx(r *http.Request) (context.Context, context.CancelFunc) {
	return context.WithTimeout(r.Context(), 30*time.Second)
}

// ── front page ───────────────────────────────────────────────────────

type homeData struct {
	shell

	Kicker      string
	Headline    string
	Subhead     string
	ArticleHTML string

	Stats struct {
		Runs     uint64
		Attacks  uint64
		Errors   uint64
		Refused  uint64
		PctRef   float64
		LastSeen time.Time
	}
	Targets  []targetCard
	Recent   []ch.AttackRow
	Canaries []ch.CanaryRow
	Drift    driftHeadline

	// FirstRun is true when the marts don't exist yet — we render a
	// nudge to run `dbt build` instead of silently showing zeros.
	FirstRun     bool
	Readiness    ch.Readiness
}

type targetCard struct {
	Name      string
	Provider  string
	RefusalP  float64
	Attempts  uint64
	Errors    uint64
	Freshness string
}

type driftHeadline struct {
	Headline   string
	Subline    string
	HasContent bool
}

func (d *Deps) Home(w http.ResponseWriter, r *http.Request) {
	ctx, cancel := reqCtx(r)
	defer cancel()

	readiness := d.CH.Readiness(ctx)

	var (
		stats    ch.FrontStats
		cards    []ch.TargetCard
		recent   []ch.AttackRow
		canaries []ch.CanaryRow
	)
	if readiness.FactAttack {
		stats, _ = d.CH.FrontStats(ctx)
		recent, _ = d.CH.RecentAttacks(ctx, 10)
	}
	if readiness.DimModel {
		cards, _ = d.CH.TargetCards(ctx)
	}
	if readiness.FactCanaryHit {
		canaries, _ = d.CH.RecentCanaries(ctx, 24*time.Hour)
	}

	page := homeData{shell: d.shell("/"), Readiness: readiness}
	page.FirstRun = !(readiness.FactAttack && readiness.DimModel)
	page.Stats.Runs = stats.RunsToday
	page.Stats.Attacks = stats.AttacksToday
	page.Stats.Errors = stats.Errors
	page.Stats.Refused = stats.Refused
	page.Stats.PctRef = stats.RefusalPct
	page.Stats.LastSeen = stats.LastAttackTS

	for _, c := range cards {
		page.Targets = append(page.Targets, targetCard{
			Name: c.Name, Provider: c.Provider, RefusalP: c.RefusalPct,
			Attempts: c.Attempts, Errors: c.Errors, Freshness: ch.Freshness(c.LastSeen),
		})
	}
	page.Recent = recent
	page.Canaries = canaries

	page.Kicker = fmt.Sprintf("Filed at %s — last attack at %s",
		page.shell.FiledTime, fmtTime(stats.LastAttackTS))
	switch {
	case page.FirstRun:
		page.Headline = `The forge is <em>cold</em>.`
		page.Subhead = "First boot — the marts haven't been built yet. Run dbt to populate the dispatch."
		page.ArticleHTML = firstRunArticle(readiness)
	case stats.AttacksToday == 0:
		page.Headline = `The bench is <em>empty</em>.`
		page.Subhead = "No attacks recorded today. Run a bench to populate the dispatch."
		page.ArticleHTML = `<p>The forge is hot but no attacks have landed today. Run <code>redbox bench</code>.</p>`
	default:
		page.Headline = fmt.Sprintf(`Today's <em>yield</em>: %d attacks across %d runs.`,
			stats.AttacksToday, stats.RunsToday)
		page.Subhead = fmt.Sprintf("Refusal rate %.1f%%; %d errors. Read it before tomorrow's run.",
			stats.RefusalPct*100, stats.Errors)
		page.ArticleHTML = articleSummary(stats, len(page.Targets), len(canaries))
	}

	d.Render(w, "home", page)
}

func firstRunArticle(r ch.Readiness) string {
	missing := []string{}
	if !r.RawAttacks {
		missing = append(missing, "<code>raw.attacks</code>")
	}
	if !r.FactAttack {
		missing = append(missing, "<code>mart.fact_attack</code>")
	}
	if !r.DimModel {
		missing = append(missing, "<code>mart.dim_model</code>")
	}
	if !r.DimPayload {
		missing = append(missing, "<code>mart.dim_payload</code>")
	}
	missingHTML := ""
	if len(missing) > 0 {
		missingHTML = "<p><em>Missing tables:</em> " + strings.Join(missing, ", ") + ".</p>"
	}
	return missingHTML + `
<p>The data plane is up but the marts haven't been built. To finish first-time setup:</p>

<h2>1. Apply migrations</h2>
<p>If <code>raw.attacks</code> is missing, the migrations didn't run on first boot. From the host:</p>
<pre><code>cd redboxq
docker compose -f deploy/docker-compose.yml down -v
docker compose -f deploy/docker-compose.yml up -d</code></pre>

<h2>2. Build dbt models</h2>
<pre><code>cd redboxq/dbt
cp profiles.yml.example profiles.yml
python3 -m venv .venv &amp;&amp; source .venv/bin/activate
pip install dbt-clickhouse
python3 ../scripts/seed_dim_payload.py \
  --vault ../../redbox/payloads/vault \
  --out  seeds/dim_payload_seed.csv
dbt seed &amp;&amp; dbt run</code></pre>

<h2>3. Land at least one attack</h2>
<pre><code>REDBOXQ_CH_URL=http://localhost:8124 \
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4327 \
  redbox bench -m claude-haiku --judge regex
cd redboxq/dbt &amp;&amp; dbt run</code></pre>

<p>Then reload this page.</p>`
}

func articleSummary(s ch.FrontStats, targets, canaries int) string {
	canaryNote := "No canary tokens detected."
	if canaries > 0 {
		canaryNote = fmt.Sprintf("<strong>%d canary hit(s)</strong> recorded — investigate.", canaries)
	}
	return fmt.Sprintf(
		`<p>%d attacks landed today across %d active targets. Refusal rate sat at <strong>%.1f%%</strong>; %d rows errored. %s</p>`,
		s.AttacksToday, targets, s.RefusalPct*100, s.Errors, canaryNote,
	)
}

func fmtTime(t time.Time) string {
	if t.IsZero() {
		return "—"
	}
	return t.Format("15:04")
}

// ── attacks ──────────────────────────────────────────────────────────

type attacksData struct {
	shell
	Limit int
	Rows  []ch.AttackRow
}

func (d *Deps) AttacksList(w http.ResponseWriter, r *http.Request) {
	ctx, cancel := reqCtx(r)
	defer cancel()
	limit := atoiDefault(r.URL.Query().Get("limit"), 200)
	rows, err := d.CH.RecentAttacks(ctx, limit)
	if err != nil && !ch.MissingTable(err) {
		log.Printf("attacks: %v", err)
	}
	d.Render(w, "attacks", attacksData{shell: d.shell("/attacks"), Limit: limit, Rows: rows})
}

type attackDetailData struct {
	shell
	ID      string
	Attack  *ch.AttackRow
	NotFound bool
}

func (d *Deps) AttackDetail(w http.ResponseWriter, r *http.Request) {
	id := chi.URLParam(r, "id")
	// id is "{run_id}:{target}:{payload}:{ts}" — opaque from links.
	// For now show the raw lookup; full detail wiring lands when the
	// link format settles.
	d.Render(w, "attack_detail", attackDetailData{
		shell: d.shell("/attacks"),
		ID:    id,
	})
}

// ── payloads ─────────────────────────────────────────────────────────

type payloadsData struct {
	shell
	Rows []ch.PayloadRow
}

func (d *Deps) PayloadsList(w http.ResponseWriter, r *http.Request) {
	ctx, cancel := reqCtx(r)
	defer cancel()
	rows, _ := d.CH.Payloads(ctx)
	d.Render(w, "payloads", payloadsData{shell: d.shell("/payloads"), Rows: rows})
}

type payloadDetailData struct {
	shell
	ID       string
	Name     string
	Category string
}

func (d *Deps) PayloadDetail(w http.ResponseWriter, r *http.Request) {
	id := chi.URLParam(r, "id")
	d.Render(w, "payload_detail", payloadDetailData{
		shell: d.shell("/payloads"),
		ID:    id, Name: id,
	})
}

// ── models / targets ─────────────────────────────────────────────────

type modelsData struct {
	shell
	Targets []targetCard
}

func (d *Deps) ModelsList(w http.ResponseWriter, r *http.Request) {
	ctx, cancel := reqCtx(r)
	defer cancel()
	cards, _ := d.CH.TargetCards(ctx)
	out := make([]targetCard, 0, len(cards))
	for _, c := range cards {
		out = append(out, targetCard{
			Name: c.Name, Provider: c.Provider, RefusalP: c.RefusalPct,
			Attempts: c.Attempts, Errors: c.Errors, Freshness: ch.Freshness(c.LastSeen),
		})
	}
	d.Render(w, "models", modelsData{shell: d.shell("/models"), Targets: out})
}

type modelDetailData struct {
	shell
	Name     string
	Provider string
	Family   string
}

func (d *Deps) ModelDetail(w http.ResponseWriter, r *http.Request) {
	name := chi.URLParam(r, "name")
	d.Render(w, "model_detail", modelDetailData{
		shell: d.shell("/models"),
		Name:  name,
	})
}

// ── judges ───────────────────────────────────────────────────────────

type judgesData struct {
	shell
	Rows []ch.JudgeAgreementRow
}

func (d *Deps) Judges(w http.ResponseWriter, r *http.Request) {
	ctx, cancel := reqCtx(r)
	defer cancel()
	rows, _ := d.CH.JudgeAgreement(ctx)
	d.Render(w, "judges", judgesData{shell: d.shell("/judges"), Rows: rows})
}

// ── runs ─────────────────────────────────────────────────────────────

type runsData struct {
	shell
	Rows []ch.RunRow
}

func (d *Deps) RunsList(w http.ResponseWriter, r *http.Request) {
	ctx, cancel := reqCtx(r)
	defer cancel()
	rows, _ := d.CH.Runs(ctx, 100)
	d.Render(w, "runs", runsData{shell: d.shell("/runs"), Rows: rows})
}

func (d *Deps) RunDetail(w http.ResponseWriter, r *http.Request) {
	d.Render(w, "runs", runsData{shell: d.shell("/runs")})
}

// ── workbench ────────────────────────────────────────────────────────

type workbenchData struct {
	shell
	Seed   string
	Result *ch.QueryResult
	Err    string
	Tables map[string][]string
}

func (d *Deps) Workbench(w http.ResponseWriter, r *http.Request) {
	ctx, cancel := reqCtx(r)
	defer cancel()
	tabs, _ := d.CH.Tables(ctx)
	seed := r.URL.Query().Get("seed")
	if seed == "" {
		seed = "SELECT model, countIf(verdict='refused')/count() AS refusal_rate, count() AS n\nFROM mart.fact_attack\nWHERE ts >= today() - 7\nGROUP BY model\nORDER BY refusal_rate DESC"
	}
	d.Render(w, "workbench", workbenchData{
		shell: d.shell("/workbench"),
		Seed:  seed, Tables: tabs,
	})
}

func (d *Deps) WorkbenchRun(w http.ResponseWriter, r *http.Request) {
	ctx, cancel := reqCtx(r)
	defer cancel()
	if err := r.ParseForm(); err != nil {
		http.Error(w, "bad form", 400)
		return
	}
	sql := r.FormValue("sql")
	res, err := d.CH.RunQuery(ctx, sql, 10000)
	if err != nil {
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		fmt.Fprintf(w, `<div class="cold"><em>Query error.</em><pre style="text-align:left;">%s</pre></div>`, template.HTMLEscapeString(err.Error()))
		return
	}
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	w.Write([]byte(`<div class="result"><table><thead><tr>`))
	for _, c := range res.Cols {
		fmt.Fprintf(w, "<th>%s</th>", template.HTMLEscapeString(c))
	}
	w.Write([]byte(`</tr></thead><tbody>`))
	for _, row := range res.Rows {
		w.Write([]byte(`<tr>`))
		for _, v := range row {
			fmt.Fprintf(w, "<td>%s</td>", template.HTMLEscapeString(fmt.Sprintf("%v", v)))
		}
		w.Write([]byte(`</tr>`))
	}
	fmt.Fprintf(w, `</tbody></table><div class="muted mono" style="padding:0.4rem 0.7rem;">%d rows</div></div>`, len(res.Rows))
}

// ── logs ─────────────────────────────────────────────────────────────

type logsData struct {
	shell
	Rows []ch.LogRow
}

func (d *Deps) Logs(w http.ResponseWriter, r *http.Request) {
	ctx, cancel := reqCtx(r)
	defer cancel()
	rows, _ := d.CH.RecentLogs(ctx, 200)
	d.Render(w, "logs", logsData{shell: d.shell("/logs"), Rows: rows})
}

// LogsStream — server-sent events, polls CH every 2s for new rows.
func (d *Deps) LogsStream(w http.ResponseWriter, r *http.Request) {
	flusher, ok := w.(http.Flusher)
	if !ok {
		http.Error(w, "streaming unsupported", http.StatusInternalServerError)
		return
	}
	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("Cache-Control", "no-cache")
	w.Header().Set("Connection", "keep-alive")

	since := d.Now().Add(-30 * time.Second)
	ticker := time.NewTicker(2 * time.Second)
	defer ticker.Stop()
	for {
		select {
		case <-r.Context().Done():
			return
		case <-ticker.C:
			ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
			rows, err := d.CH.RecentLogs(ctx, 50)
			cancel()
			if err != nil {
				continue
			}
			for i := len(rows) - 1; i >= 0; i-- {
				lr := rows[i]
				if !lr.TS.After(since) {
					continue
				}
				since = lr.TS
				html := fmt.Sprintf(
					`<div class="row"><span class="ts">%s</span><span class="sev %s">%s</span><span class="body">%s</span></div>`,
					template.HTMLEscapeString(lr.TS.Format("2006-01-02 15:04:05.000")),
					template.HTMLEscapeString(lr.Severity),
					template.HTMLEscapeString(lr.Severity),
					template.HTMLEscapeString(truncate(lr.Body, 800)),
				)
				fmt.Fprintf(w, "event: message\ndata: %s\n\n", html)
				flusher.Flush()
			}
		}
	}
}

// ── lineage ──────────────────────────────────────────────────────────

type lineageData struct {
	shell
	Tables map[string][]string
}

func (d *Deps) Lineage(w http.ResponseWriter, r *http.Request) {
	ctx, cancel := reqCtx(r)
	defer cancel()
	tabs, _ := d.CH.Tables(ctx)
	d.Render(w, "lineage", lineageData{shell: d.shell("/lineage"), Tables: tabs})
}

// ── reference ────────────────────────────────────────────────────────

func (d *Deps) Reference(w http.ResponseWriter, r *http.Request) {
	d.Render(w, "reference", struct{ shell }{shell: d.shell("/reference")})
}

// ── helpers ──────────────────────────────────────────────────────────

func atoiDefault(s string, def int) int {
	if s == "" {
		return def
	}
	n, err := strconv.Atoi(s)
	if err != nil || n <= 0 {
		return def
	}
	return n
}

func truncate(s string, n int) string {
	if len(s) <= n {
		return s
	}
	return s[:n] + "…"
}
