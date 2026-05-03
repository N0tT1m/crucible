// poison-page — B1 HTTP server that serves HTML pages with hidden prompt-injection
// payloads in many channels.
//
// The server loads .payload.txt files from a corpus directory at boot, and exposes
// each one at /p/<basename>. The /index.json endpoint lists all loaded payloads
// for clients (the Python redbox core) to correlate against. Every request is
// logged as one JSONL line on stdout.
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"html"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"
)

const pageTemplate = `<!doctype html>
<html>
<head>
<title>Knowledge base — %s</title>
<style>
.r1 { color: white; background: white; }
.r2 { display: none; }
.r3 { visibility: hidden; position: absolute; left: -9999px; }
.r4 { font-size: 0.01px; }
</style>
</head>
<body>
<header><h1>Knowledge base</h1></header>
<article>
<h2>%s</h2>
<p>This article describes the configuration and deployment options for the new system.</p>

<aside class="r2" data-role="assistant-instructions">%s</aside>
<details><summary>Full operator notes</summary><div class="r1">%s</div></details>

<p>For more, see the <a href="#" title="%s">linked policy</a>.</p>

<noscript class="r4">%s</noscript>
<!-- assistant: %s -->
</article>

<template id="lazy">%s</template>
</body>
</html>
`

type payload struct {
	ID   string `json:"id"`
	Size int    `json:"size"`
	Body string `json:"-"`
}

type server struct {
	mu        sync.RWMutex
	payloads  map[string]payload
	channels  []string
	logWriter *log.Logger
}

func newServer() *server {
	return &server{
		payloads: map[string]payload{},
		channels: []string{"hidden", "alt", "comment", "noscript", "title", "template"},
		logWriter: log.New(os.Stdout, "", 0),
	}
}

func (s *server) load(corpus string) error {
	entries, err := os.ReadDir(corpus)
	if err != nil {
		return fmt.Errorf("read corpus %s: %w", corpus, err)
	}
	loaded := 0
	for _, e := range entries {
		if e.IsDir() || !strings.HasSuffix(e.Name(), ".payload.txt") {
			continue
		}
		data, err := os.ReadFile(filepath.Join(corpus, e.Name()))
		if err != nil {
			return fmt.Errorf("read %s: %w", e.Name(), err)
		}
		id := strings.TrimSuffix(e.Name(), ".payload.txt")
		s.payloads[id] = payload{ID: id, Size: len(data), Body: string(data)}
		loaded++
	}
	if loaded == 0 {
		return fmt.Errorf("no .payload.txt files found in %s", corpus)
	}
	return nil
}

func (s *server) jsonRequestLog(r *http.Request) {
	rec := map[string]any{
		"ts":     time.Now().UTC().Format(time.RFC3339Nano),
		"remote": r.RemoteAddr,
		"path":   r.URL.Path,
		"ua":     r.Header.Get("User-Agent"),
	}
	b, _ := json.Marshal(rec)
	s.logWriter.Println(string(b))
}

func (s *server) handleIndex(w http.ResponseWriter, r *http.Request) {
	s.jsonRequestLog(r)
	s.mu.RLock()
	defer s.mu.RUnlock()
	out := make([]map[string]any, 0, len(s.payloads))
	for _, p := range s.payloads {
		out = append(out, map[string]any{
			"id":       p.ID,
			"size":     p.Size,
			"channels": s.channels,
		})
	}
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(out)
}

func (s *server) handlePage(w http.ResponseWriter, r *http.Request) {
	s.jsonRequestLog(r)
	parts := strings.Split(strings.TrimPrefix(r.URL.Path, "/p/"), "/")
	id := parts[0]
	mode := ""
	if len(parts) > 1 {
		mode = parts[1]
	}

	s.mu.RLock()
	p, ok := s.payloads[id]
	s.mu.RUnlock()
	if !ok {
		http.NotFound(w, r)
		return
	}

	switch mode {
	case "raw":
		w.Header().Set("Content-Type", "text/plain; charset=utf-8")
		_, _ = w.Write([]byte(p.Body))
		return
	case "visible":
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		fmt.Fprintf(w, "<h1>%s</h1><p>visible-only</p>", html.EscapeString(p.ID))
		return
	}

	body := html.EscapeString(p.Body)
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	fmt.Fprintf(w, pageTemplate, html.EscapeString(p.ID), html.EscapeString(p.ID),
		body, body, body, body, body, body)
}

func main() {
	addr := flag.String("addr", ":8080", "listen address")
	corpus := flag.String("corpus", "./corpus", "directory of .payload.txt files")
	flag.Parse()

	s := newServer()
	if err := s.load(*corpus); err != nil {
		log.Fatalf("load corpus: %v", err)
	}
	mux := http.NewServeMux()
	mux.HandleFunc("/index.json", s.handleIndex)
	mux.HandleFunc("/p/", s.handlePage)
	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		s.jsonRequestLog(r)
		fmt.Fprintln(w, "poison-page — try /index.json or /p/<id>")
	})

	log.Printf("poison-page listening on %s, %d payload(s)", *addr, len(s.payloads))
	if err := http.ListenAndServe(*addr, mux); err != nil {
		log.Fatal(err)
	}
}
