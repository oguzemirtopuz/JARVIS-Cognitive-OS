"""[SÖZLEŞME D] GroqBrain lock.

Yürürlükteki sözleşme:
  * Lock __init__'te kurulur (eager). İlk think() yarışını kapatır.
  * Python 3.10+ asyncio.Lock() çalışan bir loop gerektirmez; GUI /
    worker thread'inde GroqBrain kurmak patlamamalı.
  * Aynı nesne daha sonra engine loop'unda think() ile kullanılabilmeli.
  * Eski test `_lock is None` diyordu — o lazy-init yarışının ta kendisi.
"""

import asyncio
import threading

import pytest
from unittest.mock import AsyncMock, MagicMock

from core.brain import GroqBrain


class DummyConfig:
    brain_models = ["dummy-model"]
    max_tokens = 100
    temperature = 0.5
    function_calling_enabled = False


def _brain_from_thread_without_loop(monkeypatch) -> GroqBrain:
    monkeypatch.setenv("GROQ_API_KEY", "test_key")
    holder = {"brain": None, "error": None}

    def _construct():
        try:
            try:
                asyncio.get_running_loop()
                holder["error"] = RuntimeError("worker thread must not have a running loop")
                return
            except RuntimeError:
                pass
            holder["brain"] = GroqBrain(config=DummyConfig())
        except Exception as e:
            holder["error"] = e

    t = threading.Thread(target=_construct)
    t.start()
    t.join()
    assert holder["error"] is None, f"Init on a loopless thread failed: {holder['error']}"
    assert holder["brain"] is not None
    return holder["brain"]


def _stub_client(brain: GroqBrain, reply: str = "test_reply") -> None:
    choice = MagicMock()
    choice.message.content = reply
    choice.message.tool_calls = None
    response = MagicMock()
    response.choices = [choice]
    brain.client = AsyncMock()
    brain.client.chat.completions.create = AsyncMock(return_value=response)
    brain.memory_manager = None


def test_brain_constructs_without_a_running_loop(monkeypatch):
    """Tk/worker thread: no event loop, construction must still succeed."""
    brain = _brain_from_thread_without_loop(monkeypatch)

    assert isinstance(brain._lock, asyncio.Lock)


@pytest.mark.asyncio
async def test_think_works_after_loopless_construction(monkeypatch):
    """Engine loop then uses that same instance — the real GUI/engine split."""
    brain = _brain_from_thread_without_loop(monkeypatch)
    _stub_client(brain)

    reply = await brain.think("test input")

    assert reply == "test_reply"
    assert isinstance(brain._lock, asyncio.Lock)


@pytest.mark.asyncio
async def test_think_without_a_lock_is_not_usable(monkeypatch):
    """Regresyon: eager lock kalkarsa think() sessizce yarışmaz, patlar."""
    brain = _brain_from_thread_without_loop(monkeypatch)
    _stub_client(brain)
    brain._lock = None

    with pytest.raises((TypeError, AttributeError)):
        await brain.think("test input")
