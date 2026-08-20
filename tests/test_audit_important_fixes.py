"""[AUDIT ÖNEMLİ #10, #13, #31, #32] Regression tests.

Three failures that stayed invisible at runtime:

  #10  PlanExecutor.replan() ignored `failed_node`, so the brain replanned
       blind and tended to reproduce the same failing step.
  #13  MemoryManager.save_memory() swallowed a failing "I learned" callback,
       so a record could be written while the user saw no confirmation.
  #31  JarvisInterface voice wiring swallowed TTS/STT startup errors, so a
  #32  broken microphone or mute assistant looked like normal behaviour.
"""

import logging
import sys
import types

import pytest
from unittest.mock import AsyncMock, MagicMock

pytest.importorskip("gui.interface")

from gui.interface import JarvisInterface
from core.memory import MemoryManager
from core.plan_executor import PlanExecutor
from core.planner import ExecutionPlan, PlanNode
from core.state_manager import TaskState


# ── #10 — replan() must tell the brain what actually failed ──────────────────

def _plan_executor(brain):
    return PlanExecutor(
        brain=brain,
        memory=MagicMock(),
        executor=MagicMock(),
        state_manager=MagicMock(),
        io_bridge=MagicMock(),
        config=MagicMock(),
    )


@pytest.fixture
def failed_search_state():
    """A task whose WEB_SEARCH step failed with a concrete tool error."""
    task_state = TaskState(id="t-1", goal="github profilimi puanla")
    task_state.add_tool_call(
        "WEB_SEARCH",
        "github.com/oguzemirtopuz",
        {"success": False, "error": "HTTP 429", "message": "rate limited"},
    )
    return task_state


@pytest.mark.asyncio
async def test_replan_prompt_identifies_the_failed_step(failed_search_state):
    brain = MagicMock()
    brain.think = AsyncMock(return_value="[PLAN]\n1. SPEAK retrying\n[/PLAN]")

    failed_node = PlanNode(
        step_number=2, protocol_tag="WEB_SEARCH", argument="github.com/oguzemirtopuz"
    )
    old_plan = ExecutionPlan(
        steps=[PlanNode(1, "SPEAK", "starting"), failed_node]
    )

    new_plan = await _plan_executor(brain).replan(
        failed_search_state, old_plan, failed_node, "step failed"
    )

    prompt = brain.think.await_args[0][0]
    assert "WEB_SEARCH" in prompt
    assert "github.com/oguzemirtopuz" in prompt
    assert "step 2" in prompt
    assert new_plan is not None


@pytest.mark.asyncio
async def test_replan_prompt_carries_the_tool_error(failed_search_state):
    brain = MagicMock()
    brain.think = AsyncMock(return_value="[PLAN]\n1. SPEAK retrying\n[/PLAN]")

    failed_node = PlanNode(2, "WEB_SEARCH", "github.com/oguzemirtopuz")
    old_plan = ExecutionPlan(steps=[failed_node])

    await _plan_executor(brain).replan(
        failed_search_state, old_plan, failed_node, "step failed"
    )

    prompt = brain.think.await_args[0][0]
    assert "HTTP 429" in prompt


@pytest.mark.asyncio
async def test_replan_still_works_without_a_failed_node():
    """Callers may pass None; the old signature allowed it."""
    brain = MagicMock()
    brain.think = AsyncMock(return_value="[PLAN]\n1. SPEAK ok\n[/PLAN]")
    old_plan = ExecutionPlan(steps=[PlanNode(1, "SPEAK", "hi")])

    new_plan = await _plan_executor(brain).replan(
        TaskState(id="t-2", goal="x"), old_plan, None, "step failed"
    )

    assert new_plan is not None


@pytest.mark.asyncio
async def test_replan_returns_none_and_logs_when_brain_fails(caplog):
    brain = MagicMock()
    brain.think = AsyncMock(side_effect=RuntimeError("groq down"))
    old_plan = ExecutionPlan(steps=[PlanNode(1, "SPEAK", "hi")])

    with caplog.at_level(logging.WARNING, logger="JARVIS.PlanExecutor"):
        result = await _plan_executor(brain).replan(
            TaskState(id="t-3", goal="x"), old_plan, None, "step failed"
        )

    assert result is None
    assert any("groq down" in r.getMessage() for r in caplog.records)


def test_last_tool_error_ignores_successful_calls():
    task_state = TaskState(id="t-4", goal="x")
    task_state.add_tool_call("WEB_SEARCH", "a", {"success": False, "error": "boom"})
    task_state.add_tool_call("WEB_SEARCH", "b", {"success": True, "message": "fine"})

    # The successful retry must not be reported as the failure reason.
    assert PlanExecutor._last_tool_error(task_state, "WEB_SEARCH") == "boom"
    assert PlanExecutor._last_tool_error(task_state, "APP_OPEN") == ""


# ── #13 — a failing save notification must be logged, not swallowed ──────────

class _FakeCollection:
    def __init__(self):
        self.added = []

    def count(self):
        return 0

    def add(self, documents, metadatas, ids):
        self.added.append((documents, metadatas, ids))


def _memory_manager(callback):
    mm = object.__new__(MemoryManager)
    mm.collection = _FakeCollection()
    mm.logger = logging.getLogger("JARVIS.MemoryManager")
    mm.max_memory_limit = 100
    mm._enforce_limit = lambda: None
    mm._on_save_callback = callback
    return mm


def test_failing_save_notification_is_logged(caplog):
    def _boom(*args, **kwargs):
        raise RuntimeError("toast widget destroyed")

    mm = _memory_manager(_boom)

    with caplog.at_level(logging.WARNING, logger="JARVIS.MemoryManager"):
        doc_id = mm.save_memory("kullanicinin adi oguz", "semantic")

    # The record is committed, so the save must still succeed...
    assert doc_id is not None
    assert len(mm.collection.added) == 1
    # ...but the lost notification has to be visible somewhere.
    assert any("notification failed" in r.getMessage().lower() for r in caplog.records)


def test_successful_save_notification_logs_nothing(caplog):
    calls = []
    mm = _memory_manager(lambda text, mem_type, importance: calls.append(text))

    with caplog.at_level(logging.WARNING, logger="JARVIS.MemoryManager"):
        doc_id = mm.save_memory("kullanicinin adi oguz", "semantic")

    assert doc_id is not None
    assert len(calls) == 1
    assert caplog.records == []


# ── #31/#32 — TTS/STT startup failures must surface ──────────────────────────

def _fake_audio_modules(monkeypatch, tts_error=None, stt_error=None):
    """Replaces audio.tts / audio.stt so no real audio device is touched."""
    class _TTS:
        def __init__(self):
            if tts_error:
                raise tts_error

        def speak(self, text):
            pass

    class _STT:
        def __init__(self):
            if stt_error:
                raise stt_error

        def listen(self):
            pass

    tts_module = types.ModuleType("audio.tts")
    tts_module.TextToSpeech = _TTS
    stt_module = types.ModuleType("audio.stt")
    stt_module.SpeechToText = _STT

    monkeypatch.setitem(sys.modules, "audio.tts", tts_module)
    monkeypatch.setitem(sys.modules, "audio.stt", stt_module)


@pytest.fixture
def voice_stub():
    """JarvisInterface with only the GUI logging hook populated."""
    app = object.__new__(JarvisInterface)
    app.gui_logs = []
    app._append_log = lambda text, tag="system": app.gui_logs.append((text, tag))
    return app


def test_voice_startup_failures_are_reported(voice_stub, monkeypatch, caplog):
    _fake_audio_modules(
        monkeypatch,
        tts_error=RuntimeError("no audio device"),
        stt_error=RuntimeError("no microphone"),
    )
    engine = MagicMock()

    with caplog.at_level(logging.WARNING, logger="JARVIS.GUI"):
        voice_stub._attach_voice(engine)

    # Nothing was wired, and the user is told why — in the GUI, not just a log.
    engine.set_tts.assert_not_called()
    engine.set_stt.assert_not_called()

    gui_text = " ".join(text for text, _ in voice_stub.gui_logs)
    assert "no audio device" in gui_text
    assert "no microphone" in gui_text
    assert len(voice_stub.gui_logs) == 2

    logged = " ".join(r.getMessage() for r in caplog.records)
    assert "TTS unavailable" in logged
    assert "STT unavailable" in logged


def test_voice_startup_stays_silent_when_it_works(voice_stub, monkeypatch):
    _fake_audio_modules(monkeypatch)
    engine = MagicMock()

    voice_stub._attach_voice(engine)

    engine.set_tts.assert_called_once()
    engine.set_stt.assert_called_once()
    engine.set_stt_instance.assert_called_once()
    assert voice_stub.gui_logs == []


def test_tts_failure_does_not_block_stt(voice_stub, monkeypatch):
    """Voice output dying must not cost the user voice input as well."""
    _fake_audio_modules(monkeypatch, tts_error=RuntimeError("no audio device"))
    engine = MagicMock()

    voice_stub._attach_voice(engine)

    engine.set_tts.assert_not_called()
    engine.set_stt.assert_called_once()
    assert len(voice_stub.gui_logs) == 1
