// observatory (I6) — long-running web dashboard over redbox.sqlite.
//
// Read-only over the A5 schema (runs + results tables). Serves HTML +
// JSON over HTTP. The drift timeline plot is rendered client-side from
// the /drift.json endpoint with a tiny inline SVG renderer (no JS deps).
package main

import (
	"database/sql"
	"encoding/json"
	"flag"
	"fmt"
	"html/template"
	"log"
	"net/http"
	"sort"
	"time"

	_ "modernc.org/sqlite"
)

type runRow struct {
	RunID     string `json:"run_id"`
	Started   string `json:"started_ts"`
	Finished  string `json:"finished_ts"`
	Config    string `json:"config_json"`
}

type driftPoint struct {
	Date          string  `json:"date"`
	Model         string  `json:"model"`
	RefusalRate   float64 `json:"refusal_rate"`
	Total         int     `json:"total"`
}

type server struct {
	db *sql.DB
}

func (s *server) runs(w http.ResponseWriter, r *http.Request) {
	rows, err := s.db.Query("SELECT run_id, started_ts, COALESCE(finished_ts,''), config_json FROM runs ORDER BY started_ts DESC LIMIT 200")
	if err != nil {
		http.Error(w, err.Error(), 500)
		return
	}
	defer rows.Close()
	out := []runRow{}
	for rows.Next() {
		var rr runRow
		if err := rows.Scan(&rr.RunID, &rr.Started, &rr.Finished, &rr.Config); err == nil {
			out = append(out, rr)
		}
	}
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(out)
}

func (s *server) drift(w http.ResponseWriter, r *http.Request) {
	q := `
		SELECT date(ts) as d, model,
		       SUM(CASE WHEN verdict='refused' THEN 1 ELSE 0 END) * 1.0 / COUNT(*) as refusal_rate,
		       COUNT(*) as total
		FROM results
		WHERE verdict IS NOT NULL
		GROUP BY d, model
		ORDER BY d ASC, model ASC`
	rows, err := s.db.Query(q)
	if err != nil {
		http.Error(w, err.Error(), 500)
		return
	}
	defer rows.Close()
	pts := []driftPoint{}
	for rows.Next() {
		var p driftPoint
		if err := rows.Scan(&p.Date, &p.Model, &p.RefusalRate, &p.Total); err == nil {
			pts = append(pts, p)
		}
	}
	sort.Slice(pts, func(i, j int) bool {
		if pts[i].Date != pts[j].Date {
			return pts[i].Date < pts[j].Date
		}
		return pts[i].Model < pts[j].Model
	})
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(pts)
}

const indexTpl = `<!doctype html><html><head><meta charset="utf-8">
<title>redbox observatory</title>
<style>
body { font: 14px/1.45 -apple-system, system-ui, sans-serif; max-width: 1100px;
       margin: 24px auto; color: #222; }
h1 { margin: 0 0 12px; }
.muted { color: #666; }
table { border-collapse: collapse; width: 100%; margin-top: 18px; }
th, td { padding: 6px 10px; border-bottom: 1px solid #eee; }
th { background: #fafafa; text-align: left; }
.dot { display:inline-block; width: 8px; height: 8px; border-radius:50%; margin-right:6px; }
</style>
</head><body>
<h1>redbox observatory</h1>
<p class="muted">Refusal-rate over time, per model. Updated {{.Now}}</p>
<svg id="chart" width="1080" height="280" style="border:1px solid #eee"></svg>
<table id="runs"></table>
<script>
async function load() {
  const drift = await (await fetch('/drift.json')).json();
  draw(drift);
  const runs = await (await fetch('/runs.json')).json();
  const t = document.getElementById('runs');
  t.innerHTML = '<thead><tr><th>run_id</th><th>started</th><th>finished</th><th>config</th></tr></thead>';
  const tb = document.createElement('tbody');
  runs.forEach(r => {
    const tr = document.createElement('tr');
    tr.innerHTML = '<td><code>' + r.run_id.slice(0,8) + '…</code></td>'
                 + '<td>' + (r.started_ts || '') + '</td>'
                 + '<td>' + (r.finished_ts || '—') + '</td>'
                 + '<td><code>' + (r.config_json || '').slice(0,180) + '</code></td>';
    tb.appendChild(tr);
  });
  t.appendChild(tb);
}
function draw(pts) {
  const svg = document.getElementById('chart');
  if (!pts.length) return;
  const dates = [...new Set(pts.map(p => p.date))].sort();
  const models = [...new Set(pts.map(p => p.model))].sort();
  const W = 1080, H = 280, pad = 40;
  const x = i => pad + i * (W - pad*2) / Math.max(dates.length-1, 1);
  const y = v => H - pad - v * (H - pad*2);
  const palette = ['#1f77b4','#ff7f0e','#2ca02c','#d62728','#9467bd','#8c564b'];
  // axes
  const ns = 'http://www.w3.org/2000/svg';
  const ax = document.createElementNS(ns, 'line');
  ax.setAttribute('x1', pad); ax.setAttribute('x2', W-pad);
  ax.setAttribute('y1', H-pad); ax.setAttribute('y2', H-pad);
  ax.setAttribute('stroke', '#bbb');
  svg.appendChild(ax);
  models.forEach((m, mi) => {
    const series = dates.map(d => {
      const p = pts.find(pp => pp.date===d && pp.model===m);
      return p ? p.refusal_rate : null;
    });
    let path = '';
    series.forEach((v, i) => {
      if (v == null) return;
      path += (path ? ' L' : 'M') + x(i) + ' ' + y(v);
    });
    const el = document.createElementNS(ns, 'path');
    el.setAttribute('d', path);
    el.setAttribute('fill', 'none');
    el.setAttribute('stroke', palette[mi % palette.length]);
    el.setAttribute('stroke-width', 2);
    svg.appendChild(el);
    const lab = document.createElementNS(ns, 'text');
    lab.setAttribute('x', W - pad - 200);
    lab.setAttribute('y', pad + mi * 16);
    lab.setAttribute('fill', palette[mi % palette.length]);
    lab.textContent = m;
    svg.appendChild(lab);
  });
}
load();
</script>
</body></html>`

func (s *server) index(w http.ResponseWriter, r *http.Request) {
	t, _ := template.New("i").Parse(indexTpl)
	_ = t.Execute(w, map[string]string{"Now": time.Now().UTC().Format(time.RFC3339)})
}

func main() {
	addr := flag.String("addr", ":7000", "listen address")
	dbPath := flag.String("db", "./redbox.sqlite", "redbox sqlite path")
	flag.Parse()
	db, err := sql.Open("sqlite", *dbPath+"?mode=ro")
	if err != nil {
		log.Fatal(err)
	}
	s := &server{db: db}
	mux := http.NewServeMux()
	mux.HandleFunc("/", s.index)
	mux.HandleFunc("/runs.json", s.runs)
	mux.HandleFunc("/drift.json", s.drift)
	log.Printf("observatory on %s db=%s", *addr, *dbPath)
	if err := http.ListenAndServe(*addr, mux); err != nil {
		log.Fatal(err)
	}
}

func init() {
	_ = fmt.Sprintf // keep fmt import
}
