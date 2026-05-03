// bus-tap (N1) — MITM HTTP proxy for inter-agent message buses.
//
// HTTP front-end (CrewAI/AutoGen/LangGraph all expose HTTP shims). Every
// JSON body posted to a bus endpoint is logged to a JSONL trace and
// optionally rewritten before being forwarded upstream.
package main

import (
	"bytes"
	"encoding/json"
	"flag"
	"io"
	"log"
	"net/http"
	"net/http/httputil"
	"net/url"
	"os"
	"sync"
	"time"
)

type traceWriter struct {
	mu sync.Mutex
	f  *os.File
}

func (t *traceWriter) write(rec map[string]any) {
	if t == nil {
		return
	}
	rec["ts"] = time.Now().UTC().Format(time.RFC3339Nano)
	b, _ := json.Marshal(rec)
	t.mu.Lock()
	defer t.mu.Unlock()
	_, _ = t.f.Write(append(b, '\n'))
}

func main() {
	listen := flag.String("listen", ":7800", "listen address")
	upstream := flag.String("upstream", "", "upstream bus base URL (required)")
	tracePath := flag.String("trace", "", "JSONL trace file")
	flag.Parse()
	if *upstream == "" {
		log.Fatal("missing -upstream")
	}
	u, err := url.Parse(*upstream)
	if err != nil {
		log.Fatalf("bad upstream: %v", err)
	}
	rev := httputil.NewSingleHostReverseProxy(u)
	var t *traceWriter
	if *tracePath != "" {
		f, err := os.OpenFile(*tracePath, os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0o644)
		if err != nil {
			log.Fatalf("open trace: %v", err)
		}
		t = &traceWriter{f: f}
		defer f.Close()
	}

	rev.ModifyResponse = func(r *http.Response) error {
		body, _ := io.ReadAll(r.Body)
		_ = r.Body.Close()
		t.write(map[string]any{"dir": "resp", "body": json.RawMessage(body)})
		r.Body = io.NopCloser(bytes.NewReader(body))
		return nil
	}

	mux := http.NewServeMux()
	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		if r.Body != nil {
			body, _ := io.ReadAll(r.Body)
			_ = r.Body.Close()
			t.write(map[string]any{"dir": "req", "path": r.URL.Path, "body": json.RawMessage(body)})
			r.Body = io.NopCloser(bytes.NewReader(body))
		}
		rev.ServeHTTP(w, r)
	})
	log.Printf("bus-tap on %s → %s", *listen, *upstream)
	if err := http.ListenAndServe(*listen, mux); err != nil {
		log.Fatal(err)
	}
}
