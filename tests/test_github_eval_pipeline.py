"""GitHub puanlama senaryosu — runtime kopuş sözleşmesi.

Log (19 Ağustos 2026): hafıza adresi bildi; Qwen kapanmamış <think>
içinde kural alıntıladı; motor [PROTOCOL: LLM_EVAL] sandı; WEB_SEARCH
hiç koşmadı; Data to LLM_EVAL: {}; düşünce ekrana döküldü.

Sözleşme:
  * Kapanmamış <think> protokol taramasından önce silinir.
  * Think içinde alıntılanan LLM_EVAL çalıştırılmaz.
  * LLM_EVAL kaynak adımı (WEB_SEARCH vb.) yoksa API çağırmaz.
  * SEARCH / 'araştır sonra puanla' planı WEB_SEARCH toplar, tab açmaz.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock

from core.config import EngineConfig
from core.engine import ExecutionEngine
from core.plan_executor import PlanExecutor
from core.planner import parse_plan
from core.reasoning import strip_reasoning
from tools.base_tool import ToolResult
from tools.system_tool import LLMEvalTool


LEAKED_THINK = """<think>
Here's a thinking process:
1. Analyze User Input
- Rule 10: Just use [PROTOCOL: LLM_EVAL] to read and interpret data.
- Rule 8: Do not use the
"""


def test_strip_reasoning_removes_closed_and_unclosed_think():
    assert strip_reasoning("<think>secret</think>\n[PROTOCOL: SPEAK] hi") == "[PROTOCOL: SPEAK] hi"
    assert "[PROTOCOL:" not in strip_reasoning(LEAKED_THINK)
    assert strip_reasoning(LEAKED_THINK) == ""


def test_search_alias_is_web_search_not_google_tab():
    plan = parse_plan("[PLAN]\n1. SEARCH github.com/oguzemirtopuz\n2. LLM_EVAL score\n[/PLAN]")
    assert [s.protocol_tag for s in plan.steps] == ["WEB_SEARCH", "LLM_EVAL"]


def test_google_search_before_eval_becomes_web_search():
    plan = parse_plan(
        "[PLAN]\n1. GOOGLE_SEARCH github.com/oguzemirtopuz\n2. LLM_EVAL score out of 10\n[/PLAN]"
    )
    assert plan.steps[0].protocol_tag == "WEB_SEARCH"
    assert plan.steps[1].protocol_tag == "LLM_EVAL"


def test_google_search_alone_stays_visible_tab():
    plan = parse_plan("[PLAN]\n1. GOOGLE_SEARCH python\n[/PLAN]")
    assert plan.steps[0].protocol_tag == "GOOGLE_SEARCH"


@pytest.mark.asyncio
async def test_llmeval_refuses_empty_step_data_without_calling_the_model():
    brain = MagicMock()
    brain.client = MagicMock()
    brain.client.chat.completions.create = AsyncMock()

    result = await LLMEvalTool().execute(
        {"question": "score the github profile out of 10"},
        engine_context={"brain": brain, "step_results": {}},
    )

    assert result.success is False
    assert result.message == "Data is missing"
    brain.client.chat.completions.create.assert_not_called()


@pytest.mark.asyncio
async def test_llmeval_strips_think_from_the_answer():
    brain = MagicMock()
    brain.model = "qwen/qwen3.6-27b"
    brain.config = MagicMock(max_tokens=2048)
    choice = MagicMock()
    choice.message.content = "<think>chain</think>\nScore: 7/10. READMEs are thin."
    brain.client = MagicMock()
    brain.client.chat.completions.create = AsyncMock(
        return_value=MagicMock(choices=[choice])
    )

    result = await LLMEvalTool().execute(
        {"question": "score"},
        engine_context={
            "brain": brain,
            "step_results": {"WEB_SEARCH": "github.com/oguzemirtopuz PyAuditor README"},
        },
    )

    assert result.success is True
    assert "<think>" not in result.speak
    assert "7/10" in result.speak
    kwargs = brain.client.chat.completions.create.await_args.kwargs
    assert kwargs["max_tokens"] >= 1024


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
    executor.execute_tool = AsyncMock(
        return_value=ToolResult(success=True, verified=True, message="ok")
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
async def test_leaked_think_does_not_run_quoted_llm_eval(engine, mock_brain, mock_executor):
    mock_brain.think.return_value = LEAKED_THINK

    await engine.process_input(
        "github adresime girip inceleyip 10 uzerinden puan ver"
    )

    mock_executor.execute_tool.assert_not_called()
    spoken = " ".join(str(c.args[0]) for c in engine.io_bridge.speak.await_args_list if c.args)
    assert "<think>" not in spoken
    assert "LLM_EVAL" not in spoken
    assert "WEB_SEARCH" not in spoken


@pytest.mark.asyncio
async def test_github_plan_runs_web_search_then_eval(engine, mock_brain, mock_executor):
    mock_brain.think.return_value = (
        "[PLAN]\n"
        "1. WEB_SEARCH github.com/oguzemirtopuz profile projects readme\n"
        "2. LLM_EVAL score the profile, projects and READMEs out of 10\n"
        "[/PLAN]"
    )
    mock_executor.execute_tool.side_effect = [
        ToolResult(
            success=True,
            verified=True,
            message="PyAuditor, README present",
            data={"content": "repos: PyAuditor"},
        ),
        ToolResult(success=True, verified=True, message="7/10", speak="Score 7/10"),
    ]

    await engine.process_input(
        "github adresime girip inceleyip 10 uzerinden puan ver"
    )

    tags = [c.args[0] for c in mock_executor.execute_tool.call_args_list]
    assert tags == ["WEB_SEARCH", "LLM_EVAL"]
