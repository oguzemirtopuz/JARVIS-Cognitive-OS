"""[AUDIT CRITICAL #25] Coordinated shutdown regression tests.

`JarvisInterface._on_close()` used to call `os._exit(0)`, which terminated the
process before the engine's daemon thread could release Playwright, ChromaDB
and its background tasks. These tests pin the sequence that replaced it:
signal the engine, wait for its cleanup, only then destroy the window.
"""

import asyncio
import os
import sys
import threading

import pytest
from unittest.mock import AsyncMock, MagicMock

pytest.importorskip("gui.interface")

import gui.interface as gui_interface
from gui.interface import JarvisInterface


# ── Doubles ──────────────────────────────────────────────────────────────────

class _FakeRoot:
    """Records window destruction plus the engine progress seen at that moment."""

    def __init__(self, progress):
        self.destroy_count = 0
        self._progress = progress
        self.progress_at_destroy = None

    def destroy(self):
        self.destroy_count += 1
        self.progress_at_destroy = list(self._progress)


class _FakeIOBridge:
    def __init__(self):
        self.shutdown_requests = 0

    def request_shutdown(self):
        self.shutdown_requests += 1


class _FakeEngine:
    def __init__(self):
        self.io_bridge = _FakeIOBridge()
        self.shutdown_calls = 0

    async def shutdown(self):
        self.shutdown_calls += 1


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _preserve_stdout():
    """_on_close() reassigns sys.stdout — keep pytest's capture intact."""
    saved = sys.stdout
    yield
    sys.stdout = saved


@pytest.fixture(autouse=True)
def _forbid_hard_exit(monkeypatch):
    """Any os._exit() during these tests means cleanup was skipped."""
    def _boom(code=0):
        raise AssertionError("os._exit() called — engine cleanup was skipped")

    monkeypatch.setattr(os, "_exit", _boom)


@pytest.fixture
def gui_stub():
    """JarvisInterface with only the shutdown-related state populated.

    Avoids building a real Tk window while still exercising the real methods.
    """
    app = object.__new__(JarvisInterface)
    app._closing = False
    app._running = True
    app.engine = _FakeEngine()
    app._engine_loop = None
    app._engine_stopped = threading.Event()
    app.engine_progress = []
    app.root = _FakeRoot(app.engine_progress)

    # The real watchdog would hard-exit the pytest process after a delay.
    app.forced_exits = []
    app._arm_force_exit = app.forced_exits.append
    return app


@pytest.fixture
def engine_loop():
    """A real asyncio loop in a side thread, mirroring the engine thread."""
    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=loop.run_forever, daemon=True)
    thread.start()
    yield loop
    loop.call_soon_threadsafe(loop.stop)
    thread.join(timeout=5)
    loop.close()


# ── GUI close sequence ───────────────────────────────────────────────────────

def test_on_close_signals_engine_and_closes_window(gui_stub):
    gui_stub._engine_stopped.set()  # engine already finished its own cleanup

    gui_stub._on_close()

    assert gui_stub.engine.io_bridge.shutdown_requests == 1
    assert gui_stub.root.destroy_count == 1
    assert gui_stub.forced_exits == [gui_interface.FORCE_EXIT_GRACE_S]
    assert gui_stub._running is False


def test_on_close_waits_for_engine_cleanup_before_destroying(gui_stub):
    """The window must not go down while the engine is still releasing things."""
    def _engine_thread():
        gui_stub.engine_progress.append("cleanup-started")
        gui_stub.engine_progress.append("cleanup-finished")
        gui_stub._engine_stopped.set()

    threading.Timer(0.2, _engine_thread).start()

    gui_stub._on_close()

    assert gui_stub.root.progress_at_destroy == ["cleanup-started", "cleanup-finished"]


def test_fallback_releases_subsystems_when_engine_loop_is_parked(
    gui_stub, engine_loop, monkeypatch
):
    """A parked loop (long STT listen) must still get its subsystems closed."""
    monkeypatch.setattr(gui_interface, "ENGINE_SHUTDOWN_WAIT_S", 0.05)
    gui_stub._engine_loop = engine_loop  # engine never sets _engine_stopped

    gui_stub._on_close()

    assert gui_stub.engine.shutdown_calls == 1
    assert gui_stub.root.destroy_count == 1


def test_shutdown_engine_reports_failure_without_a_usable_loop(
    gui_stub, monkeypatch
):
    monkeypatch.setattr(gui_interface, "ENGINE_SHUTDOWN_WAIT_S", 0.05)

    assert gui_stub._shutdown_engine() is False
    assert gui_stub.engine.io_bridge.shutdown_requests == 1


def test_on_close_is_reentrant_safe(gui_stub):
    """request_shutdown() echoes a status that schedules _on_close() again."""
    gui_stub._engine_stopped.set()

    gui_stub._on_close()
    gui_stub._on_close()

    assert gui_stub.root.destroy_count == 1
    assert gui_stub.engine.io_bridge.shutdown_requests == 1


def test_on_close_without_engine_still_closes_window(gui_stub):
    gui_stub.engine = None

    gui_stub._on_close()

    assert gui_stub.root.destroy_count == 1


# ── Engine side: shutdown is now reachable from two callers ──────────────────

@pytest.mark.asyncio
async def test_engine_shutdown_cleans_up_once_when_called_twice():
    from core.config import EngineConfig
    from core.engine import ExecutionEngine

    engine = ExecutionEngine(EngineConfig())
    engine.executor = MagicMock()
    engine.executor.cleanup = AsyncMock()

    await engine.shutdown()
    await engine.shutdown()

    assert engine.executor.cleanup.await_count == 1
    assert engine._running is False


@pytest.mark.asyncio
async def test_engine_second_shutdown_waits_for_the_first():
    """The GUI fallback must not return before in-flight cleanup finishes."""
    from core.config import EngineConfig
    from core.engine import ExecutionEngine

    engine = ExecutionEngine(EngineConfig())
    order = []

    async def _slow_cleanup():
        order.append("cleanup-started")
        await asyncio.sleep(0.2)
        order.append("cleanup-finished")

    engine.executor = MagicMock()
    engine.executor.cleanup = _slow_cleanup

    first = asyncio.create_task(engine.shutdown())
    await asyncio.sleep(0.05)  # let the first call take the lock
    await engine.shutdown()

    order.append("second-returned")
    await first

    assert order == ["cleanup-started", "cleanup-finished", "second-returned"]
