// hub-mirror (L5) — typosquatted Hugging Face mirror.
//
// Serves model metadata + raw-file endpoints in the HF API shape, with a
// generated squat list mapping common typos onto the same poisoned files.
// Read-only over a local directory of model dirs.
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"
)

func squats(name string) []string {
	out := map[string]struct{}{name: {}}
	add := func(s string) {
		if s != name {
			out[s] = struct{}{}
		}
	}
	add(strings.ToLower(name))
	add(strings.ReplaceAll(name, ".", "-"))
	add(strings.ReplaceAll(name, "-", "_"))
	add(strings.Replace(name, "ll", "l", 1))
	add(strings.Replace(name, "ll", "Il", 1))   // capital-I lookalike
	add(strings.Replace(name, "o", "0", 1))
	out2 := make([]string, 0, len(out))
	for k := range out {
		out2 = append(out2, k)
	}
	return out2
}

type server struct {
	root string
	logf func(map[string]any)
}

func (s *server) jsonLog(r *http.Request, extra map[string]any) {
	rec := map[string]any{
		"ts":     time.Now().UTC().Format(time.RFC3339Nano),
		"path":   r.URL.Path,
		"remote": r.RemoteAddr,
		"ua":     r.Header.Get("User-Agent"),
	}
	for k, v := range extra {
		rec[k] = v
	}
	s.logf(rec)
}

func (s *server) findCanonical(requested string) (string, bool) {
	entries, err := os.ReadDir(s.root)
	if err != nil {
		return "", false
	}
	for _, e := range entries {
		if !e.IsDir() {
			continue
		}
		canonical := e.Name()
		for _, sq := range squats(canonical) {
			if sq == requested {
				return canonical, true
			}
		}
	}
	return "", false
}

func (s *server) handleAPIModel(w http.ResponseWriter, r *http.Request) {
	requested := strings.TrimPrefix(r.URL.Path, "/api/models/")
	canonical, ok := s.findCanonical(requested)
	s.jsonLog(r, map[string]any{"kind": "api_model", "canonical": canonical, "match": ok})
	if !ok {
		http.NotFound(w, r)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(map[string]any{
		"id":          requested,
		"modelId":     requested,
		"sha":         "deadbeef" + canonical,
		"author":      "mirror",
		"tags":        []string{"backdoored-by-mirror"},
		"siblings":    []map[string]string{{"rfilename": "README.md"}, {"rfilename": "model.safetensors"}, {"rfilename": "config.json"}},
		"private":     false,
	})
}

func (s *server) handleResolve(w http.ResponseWriter, r *http.Request) {
	// /<name>/resolve/main/<file>
	parts := strings.SplitN(strings.TrimPrefix(r.URL.Path, "/"), "/", 4)
	if len(parts) < 4 || parts[1] != "resolve" {
		http.NotFound(w, r)
		return
	}
	requested := parts[0]
	file := parts[3]
	canonical, ok := s.findCanonical(requested)
	s.jsonLog(r, map[string]any{"kind": "resolve", "canonical": canonical, "match": ok, "file": file})
	if !ok {
		http.NotFound(w, r)
		return
	}
	full := filepath.Join(s.root, canonical, file)
	http.ServeFile(w, r, full)
}

func (s *server) handleIndex(w http.ResponseWriter, r *http.Request) {
	s.jsonLog(r, map[string]any{"kind": "index"})
	entries, _ := os.ReadDir(s.root)
	out := []map[string]any{}
	for _, e := range entries {
		if !e.IsDir() {
			continue
		}
		out = append(out, map[string]any{
			"canonical": e.Name(),
			"squats":    squats(e.Name()),
		})
	}
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(out)
}

func main() {
	addr := flag.String("addr", ":7900", "listen address")
	models := flag.String("models", "./fake-models", "directory of model dirs")
	flag.Parse()
	if _, err := os.Stat(*models); err != nil {
		log.Fatalf("models dir missing: %v", err)
	}
	enc := json.NewEncoder(os.Stdout)
	s := &server{root: *models, logf: func(m map[string]any) { _ = enc.Encode(m) }}
	mux := http.NewServeMux()
	mux.HandleFunc("/api/models/", s.handleAPIModel)
	mux.HandleFunc("/index.json", s.handleIndex)
	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		if strings.Contains(r.URL.Path, "/resolve/") {
			s.handleResolve(w, r)
			return
		}
		fmt.Fprintln(w, "hub-mirror — try /index.json or /api/models/<name>")
	})
	log.Printf("hub-mirror on %s root=%s", *addr, *models)
	if err := http.ListenAndServe(*addr, mux); err != nil {
		log.Fatal(err)
	}
}
