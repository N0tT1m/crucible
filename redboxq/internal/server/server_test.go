package server

import (
	"strings"
	"testing"
	"time"
)

func TestThousands(t *testing.T) {
	fm := funcMap()
	thousands := fm["thousands"].(func(any) string)
	cases := map[any]string{
		uint64(0):       "0",
		uint64(42):      "42",
		uint64(1000):    "1,000",
		uint64(1247):    "1,247",
		uint64(1000000): "1,000,000",
	}
	for in, want := range cases {
		if got := thousands(in); got != want {
			t.Errorf("thousands(%v) = %q, want %q", in, got, want)
		}
	}
}

func TestPct(t *testing.T) {
	fm := funcMap()
	pct := fm["pct"].(func(float64) string)
	cases := map[float64]string{
		0.0:   "0.0%",
		0.5:   "50.0%",
		0.784: "78.4%",
		1.0:   "100.0%",
	}
	for in, want := range cases {
		if got := pct(in); got != want {
			t.Errorf("pct(%v) = %q, want %q", in, got, want)
		}
	}
}

func TestFnum(t *testing.T) {
	fm := funcMap()
	fnum := fm["fnum"].(func(float64, int) string)
	if got := fnum(3.14159, 2); got != "3.14" {
		t.Errorf("fnum 2dp: %q", got)
	}
	if got := fnum(3.14159, 0); got != "3" {
		t.Errorf("fnum 0dp: %q", got)
	}
}

func TestShortid(t *testing.T) {
	fm := funcMap()
	shortid := fm["shortid"].(func(string) string)
	if got := shortid("abc"); got != "abc" {
		t.Errorf("short string: %q", got)
	}
	if got := shortid("4f8a2c1e-deadbeef-0000"); !strings.HasPrefix(got, "4f8a2c1e") || !strings.HasSuffix(got, "…") {
		t.Errorf("long string: %q", got)
	}
}

func TestTruncate(t *testing.T) {
	fm := funcMap()
	tr := fm["truncate"].(func(int, string) string)
	if got := tr(10, "short"); got != "short" {
		t.Errorf("under: %q", got)
	}
	if got := tr(5, "hello world"); got != "hello…" {
		t.Errorf("over: %q", got)
	}
}

func TestDateFormatters(t *testing.T) {
	fm := funcMap()
	tm := time.Date(2026, 5, 2, 15, 4, 5, 0, time.UTC)

	if got := fm["isodate"].(func(time.Time) string)(tm); got != "2026-05-02" {
		t.Errorf("isodate: %q", got)
	}
	if got := fm["hhmm"].(func(time.Time) string)(tm); got != "15:04" {
		t.Errorf("hhmm: %q", got)
	}
	if got := fm["hms"].(func(time.Time) string)(tm); got != "15:04:05" {
		t.Errorf("hms: %q", got)
	}
}

func TestDeref(t *testing.T) {
	fm := funcMap()
	deref := fm["deref"].(func(any) any)

	v := 1.5
	if got := deref(&v); got != 1.5 {
		t.Errorf("*float64: %v", got)
	}

	var nilFloat *float64
	if got := deref(nilFloat); got != 0.0 {
		t.Errorf("nil *float64: %v", got)
	}

	if got := deref("plain"); got != "plain" {
		t.Errorf("non-pointer pass-through: %v", got)
	}
}
