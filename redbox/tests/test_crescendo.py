"""A7 Crescendo + MultiTurnSession tests (no network)."""
from __future__ import annotations

import pytest

from redbox.core.types import Judgement, Response, Verdict
from redbox.sessions.crescendo import Crescendo
from redbox.sessions.multiturn import MultiTurnSession, Turn


class EchoTarget:
    name = "echo"
    model = "echo-1"

    def __init__(self):
        self.seen: list[str] = []

    async def send(self, user, system=None, temperature=0.7):
        self.seen.append(user)
        return Response(text=f"reply to: {user[:60]}", latency_ms=1)


class ChatEchoTarget:
    name = "chatecho"
    model = "echo-2"

    def __init__(self):
        self.last_messages: list[dict] | None = None

    async def chat(self, messages, temperature=0.7):
        self.last_messages = messages
        return Response(text=f"reply to last={messages[-1]['content'][:40]}", latency_ms=1)

    async def send(self, user, system=None, temperature=0.7):
        msgs = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.append({"role": "user", "content": user})
        return await self.chat(msgs, temperature=temperature)


@pytest.mark.asyncio
async def test_session_appends_history():
    s = MultiTurnSession(target=EchoTarget())
    r1 = await s.turn("hi")
    r2 = await s.turn("more")
    assert r1.text.startswith("reply to:")
    assert r2.text.startswith("reply to:")
    assert [t.role for t in s.history] == ["user", "assistant", "user", "assistant"]


@pytest.mark.asyncio
async def test_session_uses_chat_when_available():
    t = ChatEchoTarget()
    s = MultiTurnSession(target=t, system="be terse")
    await s.turn("hi")
    await s.turn("again")
    assert t.last_messages[0] == {"role": "system", "content": "be terse"}
    # 1 system + 2 user + 1 assistant = 4
    assert len(t.last_messages) == 4
    assert t.last_messages[-1]["role"] == "user"


@pytest.mark.asyncio
async def test_session_prepend_injects_history():
    s = MultiTurnSession(target=EchoTarget())
    s.prepend([Turn("user", "earlier"), Turn("assistant", "ok")])
    await s.turn("now")
    roles = [t.role for t in s.history]
    assert roles == ["user", "assistant", "user", "assistant"]


class CountdownJudge:
    """Refuses for the first N turns, then complies."""
    name = "countdown"

    def __init__(self, refuse_for: int):
        self._left = refuse_for

    async def judge(self, prompt, response):
        if self._left > 0:
            self._left -= 1
            return Judgement(
                verdict=Verdict.REFUSED, confidence=0.9,
                reasoning="early", judge_name=self.name,
            )
        return Judgement(
            verdict=Verdict.COMPLIED, confidence=0.9,
            reasoning="late", judge_name=self.name,
        )


@pytest.mark.asyncio
async def test_crescendo_stops_when_judge_says_complied():
    cre = Crescendo(
        target=EchoTarget(),
        judge=CountdownJudge(refuse_for=2),
        topic="bridges",
        final_goal="describe how to weaken one",
    )
    res = await cre.run()
    assert res.tipped_at == 2
    # After tipping at index 2 we stop — 3 user turns, 3 assistant turns.
    assert len([t for t in res.turns if t.role == "user"]) == 3


@pytest.mark.asyncio
async def test_crescendo_runs_full_ladder_if_judge_holds():
    cre = Crescendo(
        target=EchoTarget(),
        judge=CountdownJudge(refuse_for=999),
        topic="x",
        final_goal="y",
    )
    res = await cre.run()
    assert res.tipped_at is None
    assert len(res.judgements_per_turn) == 5  # default ladder length
