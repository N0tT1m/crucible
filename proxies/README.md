# proxies/

Go-language network binaries that the Python `redbox/` core talks to over
HTTP. Each binary is a single static executable with no Python dependency;
the cross-language contract is documented in the per-directory READMEs and
in the project root `PROJECT_IDEAS.md`.

| Binary          | Roadmap | Purpose                                             |
|-----------------|---------|-----------------------------------------------------|
| `poison-page/`  | B1      | HTTP server that serves HTML pages with hidden      |
|                 |         | prompt-injection payloads in many channels.         |
| `mcp-proxy/`    | C1      | MITM for MCP servers — intercept tool calls.        |
| `bus-tap/`      | N1      | MITM for CrewAI / AutoGen / LangGraph buses.        |
| `hub-mirror/`   | L5      | Typosquatted Hugging Face mirror.                   |

## Build all

```bash
cd proxies
for d in */; do (cd "$d" && go build ./...); done
```

Each binary has its own README with run flags.
