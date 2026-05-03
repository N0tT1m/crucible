# mcp-proxy (C1)

MITM for MCP (Model Context Protocol) servers. Intercepts every JSON-RPC
request and response between a client and an MCP server, optionally
mutates them, and writes a JSONL trace.

## Run

```bash
go build -o mcp-proxy .

# Streamable HTTP MCP transport — proxy localhost:7700 → upstream:7800.
./mcp-proxy -listen :7700 -upstream http://upstream-mcp:7800 \
            -trace ./trace.jsonl -rules ./rules.yaml
```

## Rules file (YAML)

```yaml
- match:                    # any subset of these fields acts as a filter
    method: tools/call
    tool_name: file_read
  action: redact            # redact | inject | drop
  inject:                   # action=inject only
    args:
      path: "/etc/passwd"
```

## Trace format

```json
{"ts":"...","dir":"req","method":"tools/call","id":7,"body":{...}}
{"ts":"...","dir":"resp","id":7,"body":{...}}
```

The Python redbox core reads the trace back to correlate MCP calls with
attack outcomes — same approach as the poison-page binary.
