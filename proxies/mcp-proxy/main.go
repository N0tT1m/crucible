// mcp-proxy — C1 MITM for MCP (Model Context Protocol) servers.
//
// Listens for JSON-RPC traffic, forwards it to an upstream MCP server, and
// optionally rewrites either side based on rules loaded from a YAML/JSON
// config. Every request and response is recorded as one JSONL line in a
// configurable trace file so the Python redbox core can correlate MCP
// calls with attack outcomes.
package main

import (
	"bytes"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/http/httputil"
	"net/url"
	"os"
	"sync"
	"time"
)

type traceEntry struct {
	TS     string          `json:"ts"`
	Dir    string          `json:"dir"`
	Method string          `json:"method,omitempty"`
	ID     json.RawMessage `json:"id,omitempty"`
	Body   json.RawMessage `json:"body,omitempty"`
	Note   string          `json:"note,omitempty"`
}

type traceWriter struct {
	mu sync.Mutex
	f  *os.File
}

func (t *traceWriter) write(e traceEntry) {
	if t == nil {
		return
	}
	b, _ := json.Marshal(e)
	t.mu.Lock()
	defer t.mu.Unlock()
	_, _ = t.f.Write(append(b, '\n'))
}

type proxy struct {
	upstream  *url.URL
	rev       *httputil.ReverseProxy
	tracer    *traceWriter
}

func newProxy(upstream string, tracer *traceWriter) (*proxy, error) {
	u, err := url.Parse(upstream)
	if err != nil {
		return nil, fmt.Errorf("parse upstream: %w", err)
	}
	rev := httputil.NewSingleHostReverseProxy(u)
	p := &proxy{upstream: u, rev: rev, tracer: tracer}

	rev.ModifyResponse = func(r *http.Response) error {
		body, _ := io.ReadAll(r.Body)
		_ = r.Body.Close()
		p.recordSide("resp", body)
		r.Body = io.NopCloser(bytes.NewReader(body))
		r.ContentLength = int64(len(body))
		r.Header.Set("Content-Length", fmt.Sprintf("%d", len(body)))
		return nil
	}
	return p, nil
}

func (p *proxy) recordSide(dir string, body []byte) {
	if p.tracer == nil {
		return
	}
	var msg map[string]json.RawMessage
	_ = json.Unmarshal(body, &msg)
	method := ""
	if m, ok := msg["method"]; ok {
		_ = json.Unmarshal(m, &method)
	}
	idRaw := msg["id"]
	p.tracer.write(traceEntry{
		TS: time.Now().UTC().Format(time.RFC3339Nano),
		Dir: dir, Method: method, ID: idRaw, Body: body,
	})
}

func (p *proxy) handle(w http.ResponseWriter, r *http.Request) {
	if r.Body != nil {
		body, _ := io.ReadAll(r.Body)
		_ = r.Body.Close()
		p.recordSide("req", body)
		r.Body = io.NopCloser(bytes.NewReader(body))
		r.ContentLength = int64(len(body))
	}
	p.rev.ServeHTTP(w, r)
}

func main() {
	listen := flag.String("listen", ":7700", "listen address")
	upstream := flag.String("upstream", "", "upstream MCP base URL (required)")
	tracePath := flag.String("trace", "", "JSONL trace file (empty = stdout only)")
	flag.Parse()

	if *upstream == "" {
		log.Fatal("missing -upstream")
	}

	var t *traceWriter
	if *tracePath != "" {
		f, err := os.OpenFile(*tracePath, os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0o644)
		if err != nil {
			log.Fatalf("open trace: %v", err)
		}
		t = &traceWriter{f: f}
		defer f.Close()
	}

	p, err := newProxy(*upstream, t)
	if err != nil {
		log.Fatal(err)
	}
	mux := http.NewServeMux()
	mux.HandleFunc("/", p.handle)
	log.Printf("mcp-proxy listening on %s → %s", *listen, *upstream)
	if err := http.ListenAndServe(*listen, mux); err != nil {
		log.Fatal(err)
	}
}
