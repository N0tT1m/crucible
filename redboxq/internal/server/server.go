// Package server — chi router + template parsing for redboxq.
package server

import (
	"fmt"
	"html/template"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"

	"github.com/crucible/redboxq/internal/ch"
	"github.com/crucible/redboxq/internal/config"
	"github.com/crucible/redboxq/internal/handlers"
	"github.com/crucible/redboxq/internal/ingest"
)

// New builds the chi router with every page handler registered.
func New(cfg *config.Config, chc *ch.Client) (http.Handler, error) {
	tpls, err := parseTemplates(filepath.Join(cfg.WebRoot, "templates"))
	if err != nil {
		return nil, fmt.Errorf("templates: %w", err)
	}

	deps := &handlers.Deps{
		Config:    cfg,
		CH:        chc,
		Templates: tpls,
		Now:       time.Now,
	}

	r := chi.NewRouter()
	r.Use(middleware.RequestID)
	r.Use(middleware.RealIP)
	r.Use(middleware.Logger)
	r.Use(middleware.Recoverer)
	r.Use(middleware.Timeout(60 * time.Second))

	// pages
	r.Get("/", deps.Home)
	r.Get("/runs", deps.RunsList)
	r.Get("/runs/{id}", deps.RunDetail)
	r.Get("/attacks", deps.AttacksList)
	r.Get("/attacks/{id}", deps.AttackDetail)
	r.Get("/payloads", deps.PayloadsList)
	r.Get("/payloads/{id}", deps.PayloadDetail)
	r.Get("/models", deps.ModelsList)
	r.Get("/models/{name}", deps.ModelDetail)
	r.Get("/judges", deps.Judges)
	r.Get("/workbench", deps.Workbench)
	r.Post("/workbench", deps.WorkbenchRun)
	r.Get("/logs", deps.Logs)
	r.Get("/logs/stream", deps.LogsStream)
	r.Get("/lineage", deps.Lineage)
	r.Get("/reference", deps.Reference)

	// ingest
	in := &ingest.Deps{CH: chc}
	r.Post("/ingest/attack", in.Attack)
	r.Post("/ingest/outbox", in.Outbox)
	r.Post("/attacks/{id}/label", in.Label)

	// health
	r.Get("/health", func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"ok":true,"service":"redboxq"}`))
	})

	// 404
	r.NotFound(func(w http.ResponseWriter, req *http.Request) {
		w.WriteHeader(http.StatusNotFound)
		deps.Render(w, "404", map[string]any{"Path": req.URL.Path})
	})

	// static
	staticDir := http.Dir(filepath.Join(cfg.WebRoot, "static"))
	r.Handle("/static/*", http.StripPrefix("/static/", http.FileServer(staticDir)))

	return r, nil
}

// parseTemplates loads base.html plus each page.html into a separate
// template set keyed by page name. Each set has access to {{ template
// "content" . }} from the corresponding page file.
func parseTemplates(dir string) (map[string]*template.Template, error) {
	entries, err := os.ReadDir(dir)
	if err != nil {
		return nil, err
	}
	out := map[string]*template.Template{}
	basePath := filepath.Join(dir, "base.html")
	for _, e := range entries {
		if e.IsDir() || !strings.HasSuffix(e.Name(), ".html") || e.Name() == "base.html" {
			continue
		}
		name := strings.TrimSuffix(e.Name(), ".html")
		t, err := template.New("base.html").Funcs(funcMap()).ParseFiles(
			basePath, filepath.Join(dir, e.Name()),
		)
		if err != nil {
			return nil, fmt.Errorf("parse %s: %w", e.Name(), err)
		}
		out[name] = t
	}
	return out, nil
}

func funcMap() template.FuncMap {
	return template.FuncMap{
		"thousands": func(n any) string {
			s := fmt.Sprintf("%d", n)
			// thin grouping; ASCII-safe.
			if len(s) <= 3 {
				return s
			}
			out := make([]byte, 0, len(s)+len(s)/3)
			for i, c := range []byte(s) {
				if i != 0 && (len(s)-i)%3 == 0 {
					out = append(out, ',')
				}
				out = append(out, c)
			}
			return string(out)
		},
		"pct": func(f float64) string {
			return fmt.Sprintf("%.1f%%", f*100)
		},
		"fnum": func(f float64, prec int) string {
			return fmt.Sprintf("%.*f", prec, f)
		},
		"shortdate": func(t time.Time) string {
			return t.Format("Jan 2")
		},
		"isodate": func(t time.Time) string {
			return t.Format("2006-01-02")
		},
		"hhmm": func(t time.Time) string {
			return t.Format("15:04")
		},
		"hms": func(t time.Time) string {
			return t.Format("15:04:05")
		},
		"shortid": func(s string) string {
			if len(s) <= 8 {
				return s
			}
			return s[:8] + "…"
		},
		"truncate": func(n int, s string) string {
			if len(s) <= n {
				return s
			}
			return s[:n] + "…"
		},
		"safeHTML": func(s string) template.HTML { return template.HTML(s) },
		"deref": func(v any) any {
			switch x := v.(type) {
			case *float64:
				if x == nil {
					return 0.0
				}
				return *x
			case *float32:
				if x == nil {
					return float32(0)
				}
				return *x
			case *int64:
				if x == nil {
					return int64(0)
				}
				return *x
			case *int32:
				if x == nil {
					return int32(0)
				}
				return *x
			case *string:
				if x == nil {
					return ""
				}
				return *x
			default:
				return v
			}
		},
	}
}
