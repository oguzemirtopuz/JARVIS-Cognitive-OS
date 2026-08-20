"""[SÖZLEŞME A] Plan algılama sözleşmesi.

Yürürlükteki sözleşme:
  * Metin planı `[PLAN] ... [/PLAN]` bloğudur. Beynin sistem prompt'u bunu
    üretir (`function_calling_enabled = False`), ana akış ve watcher bunu okur.
  * JSON planlama BU yola ait DEĞİL: o `PlannerEngine.create_plan` →
    `ExecutionGraph` alt sistemidir (cognitive_core / multi_agent).
  * Ayrıştırılamayan bir `[PLAN]` bloğu kullanıcıya HAM okunmamalıdır;
    protokol etiketi sızdırmak sistem prompt'unun 3. kuralına aykırı.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock

from core.config import EngineConfig
from core.engine import ExecutionEngine
from core.plan_executor import PlanExecutor
from tools.base_tool import ToolResult


JSON_PLAN = (
    '```json\n'
    '{"hedef": "test", "alt_gorevler": ['
    '{"protocol": "GOOGLE_SEARCH", "arg": "python"}]}\n'
    '```'
)


def _plan_executor() -> PlanExecutor:
    return PlanExecutor(
        brain=MagicMock(),
        memory=MagicMock(),
        executor=MagicMock(),
        state_manager=MagicMock(),
        io_bridge=MagicMock(),
        config=MagicMock(),
    )


# ── Metin planı tanınır ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_plan_block_is_parsed():
    plan = await _plan_executor().detect_and_parse_plan(
        "[PLAN]\n1. GOOGLE_SEARCH python\n2. APP_OPEN discord\n[/PLAN]",
        "python ara discord ac",
    )

    assert plan is not None
    assert [s.protocol_tag for s in plan.steps] == ["GOOGLE_SEARCH", "APP_OPEN"]
    assert plan.original_request == "python ara discord ac"


@pytest.mark.asyncio
async def test_single_line_plan_block_is_parsed():
    plan = await _plan_executor().detect_and_parse_plan(
        "[PLAN] 1. GOOGLE_SEARCH hava durumu [/PLAN]", "hava durumu"
    )

    assert plan is not None
    assert plan.total_steps == 1
    assert plan.steps[0].protocol_tag == "GOOGLE_SEARCH"


# ── Plan olmayan girdiler plan sayılmaz ──────────────────────────────────────

@pytest.mark.asyncio
async def test_json_response_is_not_a_text_plan():
    """JSON, ExecutionGraph alt sistemine ait — bu yolda plan değil."""
    assert await _plan_executor().detect_and_parse_plan(JSON_PLAN, "python ac") is None


@pytest.mark.asyncio
async def test_prose_mentioning_the_word_plan_is_not_a_plan():
    """Cevabın içinde 'plan' kelimesi geçmesi onu plan yapmaz."""
    assert await _plan_executor().detect_and_parse_plan(
        "[PROTOCOL: SPEAK] Yarin icin planini hazirladim efendim.", "plan"
    ) is None


# ── Ayrıştırılamayan plan bloğu kullanıcıya sızmaz ───────────────────────────

@pytest.fixture
def mock_brain():
    brain = MagicMock()
    brain.think = AsyncMock()
    brain.check_connection = AsyncMock(return_value=True)
    brain.client = MagicMock()
    return brain


@pytest.fixture
def mock_executor():
    executor = MagicMock()
    executor.execute_tool = AsyncMock()
    executor.cleanup = AsyncMock()
    executor.registry = MagicMock()
    executor.registry.smart_aliases = {}
    executor.registry.is_registered.return_value = True
    return executor


@pytest_asyncio.fixture
async def engine(mock_brain, mock_executor):
    from core.io_bridge import IOBridge
    from core.state_manager import StateManager

    eng = ExecutionEngine(config=EngineConfig(max_replan_attempts=2))
    eng.brain = mock_brain
    eng.memory = MagicMock()
    eng.memory.save_memory_async = AsyncMock()
    eng.executor = mock_executor
    eng.state_manager = StateManager()

    eng.io_bridge = IOBridge(config=eng.config)
    eng.io_bridge.speak = AsyncMock()
    eng.io_bridge.get_input = AsyncMock(return_value="test")
    eng.io_bridge.update_gui = MagicMock()

    eng.plan_executor = PlanExecutor(
        brain=eng.brain,
        memory=eng.memory,
        executor=eng.executor,
        state_manager=eng.state_manager,
        io_bridge=eng.io_bridge,
        config=eng.config,
    )
    eng.reflector = MagicMock()
    eng.reflector.reflect = AsyncMock(return_value={"summary": "mock"})

    yield eng
    await eng.shutdown()


def _spoken(engine) -> str:
    return " ".join(
        str(call.args[0]) for call in engine.io_bridge.speak.await_args_list if call.args
    )


@pytest.mark.asyncio
async def test_unparsable_plan_block_is_not_spoken_raw(engine, mock_brain):
    """Bilinmeyen etiketli plan → adım yok. Blok kullanıcıya okunmamalı."""
    mock_brain.think.return_value = (
        "[PLAN]\n1. NOT_A_REAL_PROTOCOL ekrani kontrol et\n[/PLAN]"
    )

    await engine.process_input("ekrani kontrol et")

    spoken = _spoken(engine)
    assert "[PLAN]" not in spoken
    assert "[/PLAN]" not in spoken


@pytest.mark.asyncio
async def test_plain_text_answer_is_still_spoken(engine, mock_brain):
    """Sızıntı temizliği normal konuşmayı susturmamalı."""
    mock_brain.think.return_value = "Anlamsiz bir metin"

    await engine.process_input("test")

    assert "Anlamsiz bir metin" in _spoken(engine)
