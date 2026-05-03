"""
Deliberately-attackable agent for red team practice.
NOT FOR PRODUCTION. Tools are intentionally unsafe.

Talks to Ollama directly using its native tool-calling API.
Exposes HTTP endpoints so red team harnesses can fire payloads at it.
"""
from __future__ import annotations

import json
import os
import time
import uuid
from collections import defaultdict
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

import tools

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://ollama:11434")
MODEL = os.environ.get("MODEL", "qwen2.5:32b")
MAX_TOOL_ITERATIONS = int(os.environ.get("MAX_TOOL_ITERATIONS", "8"))
SYSTEM_PROMPT = Path("system_prompt.txt").read_text()

app = FastAPI(title="redlab-agent", description="Attackable agent target")

# Session state lives in-memory. Restart wipes it.
SESSIONS: dict[str, list[dict[str, Any]]] = defaultdict(list)
LOGS: dict[str, list[dict[str, Any]]] = defaultdict(list)
MEMORY: dict[str, dict[str, str]] = defaultdict(dict)


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    model: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    response: str
    tool_calls: list[dict[str, Any]]
    iterations: int


def call_ollama(messages: list[dict], model: str) -> dict:
    """Single round-trip to Ollama's chat API with tool definitions."""
    payload = {
        "model": model,
        "messages": messages,
        "tools": tools.TOOL_SCHEMAS,
        "stream": False,
        "options": {"temperature": 0.7},
    }
    with httpx.Client(timeout=300.0) as client:
        r = client.post(f"{OLLAMA_URL}/api/chat", json=payload)
        r.raise_for_status()
        return r.json()


def execute_tool(session_id: str, name: str, args: dict) -> str:
    """Dispatch a tool call. Returns the string result fed back to the model."""
    fn = tools.REGISTRY.get(name)
    if fn is None:
        return f"ERROR: unknown tool '{name}'"
    try:
        return fn(session_id=session_id, memory=MEMORY[session_id], **args)
    except Exception as e:
        return f"ERROR: {type(e).__name__}: {e}"


def run_agent_loop(session_id: str, user_message: str, model: str) -> ChatResponse:
    history = SESSIONS[session_id]
    if not history:
        history.append({"role": "system", "content": SYSTEM_PROMPT})

    history.append({"role": "user", "content": user_message})
    LOGS[session_id].append({"ts": time.time(), "type": "user", "content": user_message})

    tool_calls_made: list[dict[str, Any]] = []
    iterations = 0

    while iterations < MAX_TOOL_ITERATIONS:
        iterations += 1
        result = call_ollama(history, model)
        msg = result.get("message", {})
        history.append(msg)
        LOGS[session_id].append({"ts": time.time(), "type": "assistant", "content": msg})

        tool_calls = msg.get("tool_calls") or []
        if not tool_calls:
            return ChatResponse(
                session_id=session_id,
                response=msg.get("content", ""),
                tool_calls=tool_calls_made,
                iterations=iterations,
            )

        for tc in tool_calls:
            fn_name = tc["function"]["name"]
            fn_args = tc["function"].get("arguments") or {}
            if isinstance(fn_args, str):
                try:
                    fn_args = json.loads(fn_args)
                except json.JSONDecodeError:
                    fn_args = {}

            output = execute_tool(session_id, fn_name, fn_args)
            tool_calls_made.append({"name": fn_name, "args": fn_args, "output": output})
            LOGS[session_id].append({
                "ts": time.time(), "type": "tool",
                "name": fn_name, "args": fn_args, "output": output,
            })
            history.append({
                "role": "tool",
                "content": output,
                "name": fn_name,
            })

    return ChatResponse(
        session_id=session_id,
        response="(max tool iterations reached)",
        tool_calls=tool_calls_made,
        iterations=iterations,
    )


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    session_id = req.session_id or str(uuid.uuid4())
    model = req.model or MODEL
    return run_agent_loop(session_id, req.message, model)


@app.post("/reset/{session_id}")
def reset(session_id: str):
    SESSIONS.pop(session_id, None)
    LOGS.pop(session_id, None)
    MEMORY.pop(session_id, None)
    return {"ok": True}


@app.get("/sessions")
def list_sessions():
    return {sid: len(hist) for sid, hist in SESSIONS.items()}


@app.get("/logs/{session_id}")
def get_logs(session_id: str):
    if session_id not in LOGS:
        raise HTTPException(404)
    return LOGS[session_id]


@app.get("/memory/{session_id}")
def get_memory(session_id: str):
    """Inspector endpoint — what's in the agent's persistent memory?"""
    return MEMORY.get(session_id, {})


@app.get("/outbox")
def get_outbox():
    """Inspector endpoint — fake emails the agent has 'sent'. Exfil canary."""
    outbox_dir = Path("outbox")
    if not outbox_dir.exists():
        return []
    return [json.loads(f.read_text()) for f in sorted(outbox_dir.glob("*.json"))]


@app.get("/health")
def health():
    return {"ok": True, "model": MODEL, "ollama": OLLAMA_URL}
