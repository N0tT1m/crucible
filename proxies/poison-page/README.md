# poison-page (B1)

HTTP server that serves HTML pages with hidden prompt-injection payloads.

## Run

```bash
go build -o poison-page .
./poison-page -addr :8080 -corpus ./corpus
```

The corpus directory is a pile of `.payload.txt` files; one HTTP route is
generated per file at `/p/<basename>` rendering the payload through every
hiding channel (white-on-white text, `display:none`, hidden alt, comments,
shadow DOM, JS-rendered).

## Channels

| Path suffix    | Channel                                |
|----------------|----------------------------------------|
| `/<id>`        | All channels combined (default page)   |
| `/<id>/visible`| Visible body only — control            |
| `/<id>/raw`    | Raw payload text                       |

## Wire format

`GET /index.json` lists all loaded payloads as JSON:

```json
[{"id": "ignore_prior", "size": 421, "channels": ["hidden", "alt", "comment"]}]
```

## Logging

Every request is logged as one JSONL line on stdout:

```json
{"ts": "...", "remote": "...", "path": "/p/foo", "ua": "..."}
```

The Python `redbox/proxies/poison_client.py` shim (future) reads these
lines back to correlate browser-agent fetches with payload deliveries.
