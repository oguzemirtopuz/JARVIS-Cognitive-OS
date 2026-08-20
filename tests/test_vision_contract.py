"""[SÖZLEŞME C] Vision adımı vs yorumlama sinyali.

Yürürlükteki sözleşme:
  * Plan / protokol etiketi VISION'dır. Ekranı okuyan araç budur.
  * VISION_INTERPRET bir protokol değildir. Araç işi bitince
    `next_action` olarak bunu basar; PlanExecutor handler'ı
    ham analizi Master'a çevirir.
  * LLM bazen plan adımına sinyalin adını yazar. Parser ve
    execute_node bunu VISION'a katlar — adım yok sayılmaz,
    ayrı bir protokol de uydurulmaz.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from core.config import EngineConfig
from core.engine import ExecutionEngine
from core.plan_executor import PlanExecutor
from core.planner import PlanNode, parse_plan
from core.state_manager import TaskState
from tools.base_tool import ToolResult


def test_vision_interpret_in_a_plan_becomes_vision():
    plan = parse_plan("[PLAN]\n1. VISION_INTERPRET Check display status\n[/PLAN]")

    assert plan is not None
    assert plan.total_steps == 1
    assert plan.steps[0].protocol_tag == "VISION"
    assert plan.steps[0].argument == "Check display status"


def test_vision_plan_step_stays_vision():
    plan = parse_plan("[PLAN]\n1. VISION ekrani oku\n[/PLAN]")

    assert plan is not None
    assert plan.steps[0].protocol_tag == "VISION"


@pytest.fixture
def mock_brain():
    brain = MagicMock()
    brain.think = AsyncMock(return_value="Ekranda bir tarayici var.")
    brain.check_connection = AsyncMock(return_value=True)
    brain.client = MagicMock()
    return brain


@pytest.fixture
def mock_executor():
    executor = MagicMock()
    executor.execute_tool = AsyncMock(
        return_value=ToolResult(
            success=True,
            verified=True,
            message="Ekran okundu.",
            data={"raw_analysis": "browser window"},
            next_action="VISION_INTERPRET",
        )
    )
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


@pytest.mark.asyncio
async def test_vision_step_fires_interpret_handler(engine, mock_executor):
    """Asıl yol: plan adımı VISION, araç next_action basar, handler bir kez çalışır."""
    engine.brain.think.return_value = "[PLAN]\n1. VISION Check display status\n[/PLAN]"

    with patch.object(
        engine.plan_executor, "_handle_vision_interpret", new_callable=AsyncMock
    ) as handler:
        await engine.process_input("ekrani oku")
        handler.assert_called_once()

    mock_executor.execute_tool.assert_called()
    assert mock_executor.execute_tool.call_args[0][0] == "VISION"


@pytest.mark.asyncio
async def test_misnamed_plan_step_still_runs_vision(engine, mock_executor):
    """LLM plan adımına VISION_INTERPRET yazsa bile adım VISION olarak koşar."""
    engine.brain.think.return_value = (
        "[PLAN]\n1. VISION_INTERPRET Check display status\n[/PLAN]"
    )

    with patch.object(
        engine.plan_executor, "_handle_vision_interpret", new_callable=AsyncMock
    ) as handler:
        await engine.process_input("ekrani oku")
        handler.assert_called_once()

    assert mock_executor.execute_tool.call_args[0][0] == "VISION"


@pytest.mark.asyncio
async def test_single_protocol_alias_runs_as_vision():
    """[PROTOCOL: VISION_INTERPRET] de Iron Dome'da kayıtsız kalmamalı."""
    executor = MagicMock()
    executor.execute_tool = AsyncMock(
        return_value=ToolResult(success=True, verified=True, message="ok")
    )
    executor.registry = MagicMock()
    executor.registry.smart_aliases = {}
    executor.registry.is_registered.return_value = True

    pe = PlanExecutor(
        brain=MagicMock(),
        memory=MagicMock(),
        executor=executor,
        state_manager=MagicMock(),
        io_bridge=MagicMock(),
        config=MagicMock(),
    )
    pe.io_bridge.speak = AsyncMock()

    await pe.execute_node(
        TaskState(id="v1", goal="ekran"),
        PlanNode(1, "VISION_INTERPRET", "oku"),
    )

    assert executor.execute_tool.call_args[0][0] == "VISION"
