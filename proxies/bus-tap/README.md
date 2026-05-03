# bus-tap (N1)

MITM for multi-agent message buses (CrewAI, AutoGen, LangGraph). Records
every inter-agent message as JSONL and supports rule-based mutation in
flight, the same way `mcp-proxy` works for MCP servers.

## Trace format

```
{"sender":"...","recipient":"...","role":"...","content":"...","metadata":{...}}
```

Matches the `BusMessage` dataclass in `redbox/swarm/bus_tap.py` so Python
can read these traces back without a separate parser.
