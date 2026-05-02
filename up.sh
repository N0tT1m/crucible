#!/usr/bin/env bash
# One-shot bring-up for the redlab.
# Usage:
#   ./up.sh              # light stack: ollama + litellm + agent
#   ./up.sh --heavy      # adds vLLM (Qwen3-32B FP8) — needs the 5090
#   ./up.sh --full       # adds vLLM + postgres + qdrant + langfuse
#   ./up.sh --models     # also pre-pull common Ollama models
#   ./up.sh --heavy --models

set -euo pipefail

cd "$(dirname "$0")"

# -------- args --------
PROFILES=()
PULL_MODELS=0
for arg in "$@"; do
  case "$arg" in
    --heavy) PROFILES+=("--profile" "heavy") ;;
    --full)  PROFILES+=("--profile" "heavy" "--profile" "data" "--profile" "obs") ;;
    --data)  PROFILES+=("--profile" "data") ;;
    --obs)   PROFILES+=("--profile" "obs") ;;
    --models) PULL_MODELS=1 ;;
    -h|--help)
      sed -n '2,8p' "$0"; exit 0 ;;
    *) echo "unknown flag: $arg"; exit 1 ;;
  esac
done

# -------- preflight --------
echo "==> preflight checks"
command -v docker >/dev/null || { echo "docker not found"; exit 1; }
docker compose version >/dev/null 2>&1 || { echo "docker compose plugin missing"; exit 1; }

if ! docker run --rm --gpus all nvidia/cuda:12.6.0-base-ubuntu24.04 nvidia-smi >/dev/null 2>&1; then
  echo "WARNING: GPU not visible to Docker. Install nvidia-container-toolkit and restart docker."
  echo "         Continuing — local CPU inference will work but be slow."
fi

if [[ ! -f .env ]]; then
  echo "==> creating .env from .env.example"
  cp .env.example .env
  echo "    (edit .env to add API keys before using frontier providers)"
fi

mkdir -p agent/outbox

# -------- bring up --------
echo "==> docker compose up ${PROFILES[*]:-(default profile)}"
docker compose "${PROFILES[@]}" up -d --build

# -------- model pull (optional) --------
if [[ $PULL_MODELS -eq 1 ]]; then
  echo "==> waiting for ollama"
  for i in {1..30}; do
    if curl -sf http://localhost:11434/api/tags >/dev/null; then break; fi
    sleep 2
  done
  echo "==> pulling ollama models (this takes a while on first run)"
  docker exec redlab-ollama ollama pull qwen2.5:14b
  docker exec redlab-ollama ollama pull qwen2.5:32b
  docker exec redlab-ollama ollama pull llama3.1:8b
  docker exec redlab-ollama ollama pull gemma3:27b || true
  docker exec redlab-ollama ollama pull deepseek-r1:32b || true
fi

# -------- wait for health --------
echo "==> waiting for services to come up"
wait_for() {
  local name="$1" url="$2" timeout="${3:-60}"
  for i in $(seq 1 "$timeout"); do
    if curl -sf "$url" >/dev/null 2>&1; then
      echo "   ✓ $name"; return 0
    fi
    sleep 1
  done
  echo "   ✗ $name (timeout after ${timeout}s — check 'docker compose logs $name')"
  return 1
}

wait_for ollama  http://localhost:11434/api/tags  60 || true
wait_for litellm http://localhost:4000/health      60 || true
wait_for agent   http://localhost:8000/health      60 || true

if [[ " ${PROFILES[*]} " == *" heavy "* ]]; then
  echo "   (vLLM cold-start can take 2-5 minutes while it loads the 32B model)"
  wait_for vllm http://localhost:8001/v1/models 600 || true
fi

# -------- summary --------
cat <<EOF

========================================
redlab is up.

  Ollama         http://localhost:11434
  LiteLLM proxy  http://localhost:4000   (OpenAI-compatible, key in .env)
  Agent          http://localhost:8000
EOF

if [[ " ${PROFILES[*]} " == *" heavy "* ]]; then
  echo "  vLLM (Qwen3-32B) http://localhost:8001/v1"
fi
if [[ " ${PROFILES[*]} " == *" data "* ]] || [[ " ${PROFILES[*]} " == *" obs "* ]]; then
  echo "  Postgres       localhost:5432"
fi
if [[ " ${PROFILES[*]} " == *" data "* ]] || [[ " ${PROFILES[*]} " == *" rag "* ]]; then
  echo "  Qdrant         http://localhost:6333/dashboard"
fi
if [[ " ${PROFILES[*]} " == *" obs "* ]]; then
  echo "  Langfuse       http://localhost:3000"
fi

cat <<EOF

quick smoke test:
  curl -sX POST http://localhost:8000/chat \\
    -H 'content-type: application/json' \\
    -d '{"message":"list my files"}' | jq

stop with:        docker compose down
follow logs:      docker compose logs -f
========================================
EOF
