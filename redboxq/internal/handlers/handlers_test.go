package handlers

import (
	"strings"
	"testing"
	"time"

	"github.com/crucible/redboxq/internal/ch"
)

func TestAtoiDefault(t *testing.T) {
	cases := []struct {
		in   string
		def  int
		want int
	}{
		{"", 100, 100},
		{"50", 100, 50},
		{"abc", 100, 100},
		{"-5", 100, 100},
		{"0", 100, 100},
	}
	for _, c := range cases {
		got := atoiDefault(c.in, c.def)
		if got != c.want {
			t.Errorf("atoiDefault(%q, %d) = %d, want %d", c.in, c.def, got, c.want)
		}
	}
}

func TestTruncateLocal(t *testing.T) {
	if got := truncate("hi", 10); got != "hi" {
		t.Errorf("under: %q", got)
	}
	if got := truncate("hello world", 5); got != "hello…" {
		t.Errorf("over: %q", got)
	}
}

func TestFmtTime(t *testing.T) {
	if got := fmtTime(time.Time{}); got != "—" {
		t.Errorf("zero: %q", got)
	}
	tm := time.Date(2026, 5, 2, 15, 4, 5, 0, time.UTC)
	if got := fmtTime(tm); got != "15:04" {
		t.Errorf("nonzero: %q", got)
	}
}

func TestSectionsCoverEveryRoute(t *testing.T) {
	for i, s := range sections {
		if s.Slug == "" || s.Name == "" || s.Blurb == "" {
			t.Errorf("section %d incomplete: %+v", i, s)
		}
	}
	if sections[0].Slug != "/" {
		t.Errorf("first section is not the front: %s", sections[0].Slug)
	}
}

func TestArticleSummaryHandlesZeros(t *testing.T) {
	html := articleSummary(ch.FrontStats{}, 0, 0)
	if html == "" {
		t.Fatal("articleSummary returned empty")
	}
	if strings.Contains(html, "NaN") {
		t.Errorf("NaN in output: %s", html)
	}
}

func TestFirstRunArticleListsMissing(t *testing.T) {
	html := firstRunArticle(ch.Readiness{}) // all false
	for _, want := range []string{"raw.attacks", "mart.fact_attack", "mart.dim_model", "mart.dim_payload"} {
		if !strings.Contains(html, want) {
			t.Errorf("first-run article missing reference to %s", want)
		}
	}
	for _, want := range []string{"dbt seed", "dbt run", "redbox bench"} {
		if !strings.Contains(html, want) {
			t.Errorf("first-run article missing instruction %q", want)
		}
	}
}
