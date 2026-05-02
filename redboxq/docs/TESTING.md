# Testing

How to run the test suite, what's covered, and where the gaps are.

## Run everything

```bash
# Go (5 packages, ~25 tests)
cd redboxq && go test ./...

# Python (~50 tests)
cd /path/to/crucible
source .venv/bin/activate
python -m pytest homelab/tests -q

# dbt data tests (need a populated CH)
cd redboxq/dbt && dbt test
```

## What's covered

### Go (`redboxq/`)

| Package | Tests | What it catches |
|---|---|---|
| `internal/ch` | `client_test.go` | `MissingTable` heuristics, `Freshness` buckets, `hasLimit` parser. |
| `internal/config` | `config_test.go` | Default ports (must not collide with smoothies' 9000), env override, `IssueNo` arithmetic. |
| `internal/server` | `server_test.go` | Every template func (`thousands`, `pct`, `fnum`, `shortid`, `truncate`, date formatters, `deref`). |
| `internal/handlers` | `handlers_test.go` | `atoiDefault`, `truncate`, `fmtTime`, the sections nav array, `articleSummary` doesn't NaN, `firstRunArticle` lists every missing table. |
| `internal/alerts` | `rules_test.go` | All 4 rules registered, cooldowns reasonable. |

The handler-level integration tests are deferred until `ch.Client` is
behind an interface — testing through the router would need a real
ClickHouse, which CI doesn't have.

### Python (`homelab/tests/`)

| File | What it catches |
|---|---|
| `test_smoke.py` | A1/A2/A4/A5/I1 wiring end-to-end with fake targets + the SqliteSink. |
| `test_runner_helpers.py` | `_template_hash` is deterministic + collision-free; `_classify_error` buckets right; `_cost_at_attack` math + null fall-through. |
| `test_sinks.py` | `SqliteSink` is `isinstance` of the Protocol; `fanout` swallows per-sink failures; an incomplete impl is rejected by the runtime check. |
| `test_ch_sink.py` | `_row()` has every column the schema expects; verdict serialisation; buffered flush triggers on `flush_every`; `finish_run` flushes; HTTP failure doesn't propagate. |
| `test_judges.py` | The "As an AI assistant" false positive is gone; real refusals still fire; LLM judge handles fenced JSON, clamps confidence, returns `unknown` on garbage. |
| `test_seed_payload.py` | The vault → CSV script writes one row per YAML, preserves metadata, returns expected column header. |

### dbt (`redboxq/dbt/`)

Schema tests in `models/marts/schema.yml`:
- `dim_payload.payload_id`: unique + not_null
- `dim_model.model_name`: unique + not_null
- `dim_model.provider`: in `{anthropic, openai, ollama, vllm}`
- `dim_judge.judge_name`: unique + not_null
- `dim_judge.kind`: in `{regex, llm}`
- `fact_attack.run_id`: not_null
- `fact_attack.verdict`: in `{refused, complied, partial, unknown}`

Custom data tests in `dbt/tests/`:
- `no_future_attacks.sql` — `ts` must be ≤ now+1m. Catches clock skew.
- `no_orphan_payloads.sql` — every `fact_attack.payload_id` must exist in
  `dim_payload`. Catches "ran a bench with a payload not in the seed."
- `refusal_rate_in_range.sql` — `refusal_rate ∈ [0, 1]`. Catches divide-by-zero leaks.
- `judge_name_matches_dim.sql` — every `judge_name` (non-empty) must
  exist in `dim_judge`. Catches typos and unseeded judges.

## What's not covered

These would be valuable but need infra we don't have in CI:

- **End-to-end smoke against a real ClickHouse.** Spin up a CH
  container in CI, run a bench against a fake target, assert rows
  land in `raw.attacks` and `dbt build` succeeds. Probably an
  `integration/` directory with a docker-compose used only for tests.
- **Live LLM judge round-trip.** Needs an API key and a mock provider.
- **SSE log stream.** The `LogsStream` handler is currently
  uninstrumented. A `httptest.NewRecorder` + `httptest.ResponseRecorder`
  doesn't fully exercise SSE — a real server + client is cleaner.
- **dbt model output shape.** dbt has its own contract testing; once
  the marts have a stable shape, add model-level contracts.
- **Discord/Telegram fan-out.** Mock the HTTP client and assert the
  payload format. Cheap, just hasn't been written yet.

## Adding a test

For each layer:

- **Go**: file alongside the code as `*_test.go`. Use table-driven
  tests for parsers/formatters; use `httptest` for handlers once the
  CH client is interface-able.
- **Python**: file in `homelab/tests/`. Use `pytest.mark.asyncio` for
  async judges/runner code (see `test_judges.py` for the pattern).
- **dbt schema test**: `redboxq/dbt/models/marts/schema.yml` for
  column-level tests. Use `dbt-utils` for `accepted_range`,
  `expression_is_true`, etc.
- **dbt data test**: a `.sql` file in `redboxq/dbt/tests/`. The query
  must return zero rows when the test passes.

## CI sketch

If you wire CI later, the minimum job set:

```yaml
go-test:
  cd: redboxq
  run: go test ./...

python-test:
  setup: pip install -e '.[dev]'
  run:   pytest homelab/tests -q

dbt-test:
  needs: clickhouse service
  run:
    - dbt seed
    - dbt build
    - dbt test
```

The dbt job is the slow one — it stands up ClickHouse — so it's the
last gate, not the first.
