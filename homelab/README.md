# Redlab

LLM red team homelab. Single command brings up: model server(s), unified
proxy, and an attackable agent target.

## Quick start

```bash
cd homelab
cp .env.example .env       # optional: add API keys for frontier models
./up.sh --heavy --models   # full bring-up: vLLM + Ollama + agent + model pulls
```

First run takes ~10–30 minutes (model downloads dominate). Subsequent runs
are seconds — model cache and Ollama data live in named volumes.

## What runs

| Service | Port | Purpose |
|---------|------|---------|
| Ollama | 11434 | Easy small/medium model swaps |
| vLLM | 8001 | High-throughput **Qwen3-32B FP8** for batch attacks |
| LiteLLM | 4000 | One OpenAI-compatible endpoint for everything |
| Agent | 8000 | Attackable target with 8 tools |
| Postgres | 5432 | (`--profile data`) results store |
| Qdrant | 6333 | (`--profile data`) vector DB for RAG attacks |
| Langfuse | 3000 | (`--profile obs`) trace inspection |

## Common commands

```bash
make up           # light stack
make up-heavy     # + vLLM (32GB VRAM model)
make up-full      # everything
make down         # stop
make logs         # tail all logs
make smoke        # functional tests against the agent
make models       # pull common Ollama models
make gpu          # nvidia-smi from inside the container
make clean        # also wipes volumes (loses model cache!)
```

## Talking to the stack

```bash
# direct to agent
curl -sX POST localhost:8000/chat -H 'content-type: application/json' \
  -d '{"message":"hello"}' | jq

# through litellm (any registered model)
curl localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer sk-redlab-dev" \
  -H "content-type: application/json" \
  -d '{"model":"qwen3-32b","messages":[{"role":"user","content":"hello"}]}'

# direct to vllm
curl localhost:8001/v1/chat/completions \
  -H "content-type: application/json" \
  -d '{"model":"qwen3-32b","messages":[{"role":"user","content":"hello"}]}'
```

## Model picks (5090 / 32GB)

The compose pre-configures a sensible set:

- **vLLM**: Qwen3-32B FP8 — best capability that fits cleanly in 32GB
- **Ollama defaults**: qwen2.5:14b (fast, agent default), qwen2.5:32b,
  llama3.1:8b, gemma3:27b, deepseek-r1:32b

Swap the vLLM model by editing the `--model` flag in `docker-compose.yml`.

## File layout

```
homelab/
├── docker-compose.yml    # full stack with profiles
├── litellm.yaml          # provider routing
├── up.sh                 # one-shot bring-up
├── Makefile              # everyday commands
├── .env.example
├── compose-vllm.yml      # standalone vLLM (alternative deploy)
└── agent/
    ├── agent.py          # FastAPI + Ollama tool-calling
    ├── tools.py          # 8 attack-surface tools
    ├── system_prompt.txt # canary string lives here
    ├── sandbox/          # files the agent can read (with seeded payloads)
    ├── outbox/           # send_email writes here — exfil canary
    ├── Dockerfile
    └── README.md         # attack matrix
```

## Safety reminders

- The agent has `eval()` in its calculator and unrestricted `http_get`.
  **Never** point it at production data.
- For full isolation, attach the agent + ollama services to a Docker
  network created with `--internal` and bridge only the LiteLLM service
  to it.
- Rotate canary strings between experiments so leaks are attributable.
