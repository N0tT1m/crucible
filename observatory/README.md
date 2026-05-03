# observatory (I6)

Long-running web dashboard over `redbox.sqlite`. Tracks how providers
drift over time. Single Go binary; serves HTML + JSON over HTTP.

This is the closest thing redbox has to a *public* artifact — point it
at a SQLite store fed by a periodic A5 run and you get a portfolio-grade
view of provider safety drift.

## Run

```bash
go build -o observatory .
./observatory -addr :7000 -db /path/to/redbox.sqlite
```

## Endpoints

| Path                | Description                              |
|---------------------|------------------------------------------|
| `/`                 | HTML dashboard (refusal-rate timeline)  |
| `/runs.json`        | All runs (paginated)                    |
| `/runs/<id>.json`   | One run with all results                |
| `/drift.json`       | Per-model refusal-rate over time        |

## Schema

Reads from the same `redbox.sqlite` schema produced by A5 (see
`redbox/core/results.py`). Read-only — never writes.
