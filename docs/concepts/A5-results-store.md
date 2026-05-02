# A5 — `drift-tracker` / results-store

Two related things in one project:

1. **The `ResultsStore`** — a SQLite schema with tables for runs, payloads, responses, and verdicts. The shared data layer every later project writes to.
2. **The drift tracker** — a recurring job that runs the vault against current models and charts refusal-rate over time.

The store is the more important deliverable. The drift tracker is its first useful application.

A5 is the **fourth piece of Tier 1**. With A1 + A2 + A4 + A5 you can persist results, query them, replay them, and watch them drift.

## Why a store, not just print-to-stdout

Without persistence, every run is a one-off. With a store you can:

- **Compare runs.** "Did refusal rate go up after the November 6 model release?" — a SQL `JOIN` on date.
- **Replay.** Reproduce a 6-month-old experiment exactly. The payload version is on file; the responses are on file; the judge's reasoning is on file. (I4 builds on this.)
- **Re-judge.** A4 came out today; you have 90 days of stored responses from yesterday's regex-only judge. Re-run the LLM judge over the responses table — instantly upgrade your historical data.
- **Dashboard.** I6 reads the store to render a long-running observatory. Provider drift visible at a glance.
- **Audit.** S2 tags payloads with NIST/EU-AI-Act metadata; S4 generates audit-grade PDFs by joining tags × verdicts × runs.
- **Cost track.** I3 reads token counts from the responses table to compute $/run.

The store is the **shared data layer**. Every B-V section writes here.

## The schema

Four tables, intentionally minimal:

### `runs`

| Column | Type | Notes |
|---|---|---|
| `run_id` | TEXT PK | UUID per `redbox bench` invocation. |
| `started_at` | TIMESTAMP | Wall-clock start. |
| `finished_at` | TIMESTAMP | Null while in progress. |
| `target_model` | TEXT | LiteLLM alias: `qwen-14b`, `claude-haiku`, etc. |
| `judge_kind` | TEXT | `regex`, `llm`, `ensemble`. |
| `judge_model` | TEXT | Null for regex. |
| `payload_count` | INTEGER | Cardinality of the run. |
| `notes` | TEXT | Free-form. |

### `payloads`

| Column | Type | Notes |
|---|---|---|
| `payload_id` | TEXT | Slug from the YAML. |
| `payload_version` | TEXT | Hash of the template content at run time — *not* the file's mtime. |
| `name` | TEXT | |
| `category` | TEXT | |
| `template` | TEXT | The raw text. |
| `tags` | JSON | |

Composite PK: `(payload_id, payload_version)`. Re-edit a YAML and the next run inserts a new row; old runs still reference the old version.

### `responses`

| Column | Type | Notes |
|---|---|---|
| `run_id` | TEXT FK → runs | |
| `payload_id` | TEXT | |
| `payload_version` | TEXT | |
| `target_query` | TEXT | The harm probe used. |
| `mutator_chain` | JSON | List like `["base64", "rot13"]`. Empty if no A3. |
| `content` | TEXT | The model's full reply. |
| `latency_ms` | INTEGER | |
| `tokens_in` | INTEGER | |
| `tokens_out` | INTEGER | |
| `error` | TEXT | Null on success. |

### `verdicts`

| Column | Type | Notes |
|---|---|---|
| `run_id` | TEXT FK | |
| `payload_id` | TEXT | |
| `judge_kind` | TEXT | Same row may have multiple verdicts (re-judging). |
| `judge_model` | TEXT | |
| `verdict` | TEXT | `REFUSED`, `COMPLIED`, `PARTIAL`, `MALFORMED`. |
| `confidence` | REAL | |
| `reasoning` | TEXT | |
| `judged_at` | TIMESTAMP | |

The `verdicts` table is *append-only*. Re-judging an old run produces new rows, not updates — historical verdicts stay queryable.

## Why SQLite

Single-process, embedded, zero ops. You ship a `.sqlite` file; anyone can `sqlite3 redbox.sqlite` and query.

When this stops being enough:

- Multiple writers (a CI runner + your laptop both writing) → upgrade to Postgres. The schema ports cleanly.
- Multi-user dashboards (I6 observatory) → Postgres mandatory.

That's months out. SQLite for now.

## Homelab grounding

After every `redbox bench`, results land in `redbox/redbox.sqlite` (gitignored). Inspect interactively:

```bash
sqlite3 redbox/redbox.sqlite
sqlite> .tables
sqlite> .schema runs
sqlite> SELECT run_id, target_model, payload_count FROM runs ORDER BY started_at DESC LIMIT 5;
sqlite> SELECT verdict, COUNT(*) FROM verdicts WHERE run_id = ? GROUP BY verdict;
sqlite> .exit
```

Or via the CLI:

```bash
redbox runs                         # recent runs
redbox report <run_id>              # JSON summary
```

## Recommended first experiments

### 1. Two runs, one model, two judges

```bash
redbox bench -m qwen-14b --judge regex
redbox bench -m qwen-14b --judge llm --judge-model claude-haiku
redbox runs
```

You should see two rows. Both have the same `responses` (same payloads, same model) but different `verdicts`.

### 2. Compare verdicts across judges

```sql
-- run inside sqlite3 redbox/redbox.sqlite
SELECT
  v_regex.payload_id,
  v_regex.verdict AS regex_verdict,
  v_llm.verdict   AS llm_verdict
FROM verdicts v_regex
JOIN verdicts v_llm USING (run_id, payload_id)
WHERE v_regex.judge_kind = 'regex' AND v_llm.judge_kind = 'llm';
```

Disagreements between regex and LLM are exactly where the LLM judge earned its cost.

### 3. Refusal rate by model

```bash
for m in qwen-14b llama3-8b claude-haiku; do
  redbox bench -m $m --judge llm --judge-model claude-haiku
done
```

Then:

```sql
SELECT r.target_model,
       SUM(v.verdict = 'COMPLIED') * 1.0 / COUNT(*) AS compliance_rate
FROM runs r
JOIN verdicts v USING (run_id)
GROUP BY r.target_model
ORDER BY compliance_rate DESC;
```

That's your refusal-rate ladder across the homelab.

### 4. Drift over time (if you wait a week)

Re-run the same bench in a week and compare:

```sql
SELECT DATE(started_at) AS day, target_model,
       SUM(verdict = 'COMPLIED') * 1.0 / COUNT(*) AS rate
FROM runs JOIN verdicts USING (run_id)
WHERE target_model = 'qwen-14b'
GROUP BY DATE(started_at);
```

If the rate moves and you didn't change payloads, either the model was updated or you've found drift in the judge.

### 5. Replay a stored run

```bash
redbox replay <run_id>     # re-runs the exact (model, payload, mutator) tuples
```

Verify determinism: with `--temp 0`, the new responses should match the old ones byte-for-byte (modulo backend non-determinism).

## Where it plugs into later projects

| Project | How it uses A5 |
|---|---|
| **All targets / probes** | Write responses + verdicts here. |
| **I1** parallel-runner | Streams writes to A5 while running. Crash-resumable from the last completed task. |
| **I3** cost-tracker | Reads `tokens_in / tokens_out` × per-provider pricing. |
| **I4** replay-recorder | Reconstructs runs from the schema. |
| **I5** diff-viewer | Joins two runs to show side-by-side. |
| **I6** observatory | Long-running dashboard reading A5 (forces the Postgres upgrade). |
| **A5 drift tracker** | Cron'd version of bench writes to the same store; chart refusal-rate by date. |
| **S2** policy-mapper | Adds NIST/EU-AI-Act tags to payloads via a sidecar table. |
| **S4** audit-reporter | Generates compliance PDFs from joined runs × policy tags. |
| **U5** eval-vs-deploy-drift | Re-runs historical A5 rows with prod-style framing; tracks delta. |

If something in B–V "produces a result," the result lands here.

## When you've internalized A5

You should be able to answer:

- *Why version payloads instead of just storing the template inline on every response?* Storage efficiency (the same template is reused across many responses) and clean joins (re-edit a YAML, old runs still reference the old version).
- *Why is the verdicts table append-only?* Re-judging is normal; you want to keep the regex verdict alongside the new LLM verdict, not overwrite it.
- *Why store `mutator_chain` as JSON, not as foreign keys to a mutators table?* Mutators are stateless and the chain is small. Inlining the JSON keeps the schema readable. If A3 grows mutator-config (parameters per mutator), revisit.
- *When do you outgrow SQLite?* When more than one process writes concurrently, or when I6 (observatory) lands and multiple users query simultaneously.

When those land, move to I1.

## Reference implementation

- `redbox/core/results.py` — A5's `ResultsStore`. The schema is in code, migrations are forward-only.
- `redbox/cli.py` — `runs`, `report`, and (later) `replay` subcommands.
- `redbox/redbox.sqlite` — the actual file (gitignored). Treat it as ephemeral; everything reproducible should be reproducible from the vault + the run command.
