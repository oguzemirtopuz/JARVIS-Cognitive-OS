"""[SÖZLEŞME B] verified kapısı.

Yürürlükteki sözleşme:
  * Bir araç etkisini kendisi gözlemlemeden başarı ilan edemez. Executor
    `verified=False` gelen sonucu `success=False`'a düşürür ("unreal
    success" kalkanı) — bu kasıtlı, kaldırılmayacak.
  * Bu yüzden gerçekten iş yapan her başarı yolu `verified=True`
    bildirmek ZORUNDA. Bildirmezse iş görmüş araç kullanıcıya
    başarısız raporlanır, gereksiz replan/fallback tetiklenir.
  * Kapı artık sessiz değil: bayrağı unutan araç logda görünür.
"""

import ast
import logging
import pathlib

import pytest
from unittest.mock import MagicMock

from core.executor import Executor
from tools.base_tool import BaseTool, ToolResult


class _StubTool(BaseTool):
    name = "StubTool"
    protocol_tag = "STUB_TOOL"
    domain = "test"
    parameters = {"arg": "string"}

    def __init__(self, result: ToolResult):
        self._result = result

    async def execute(self, params, context):
        return self._result


def _executor(result: ToolResult) -> Executor:
    ex = Executor(brain=MagicMock())
    ex.registry = MagicMock()
    ex.registry.get_by_protocol.return_value = _StubTool(result)
    return ex


# ── Kapının davranışı ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_verified_success_is_accepted():
    ex = _executor(ToolResult(success=True, verified=True, message="done"))

    result = await ex.execute_tool("STUB_TOOL", "arg")

    assert result.success is True
    assert result.message == "done"


@pytest.mark.asyncio
async def test_unverified_success_is_downgraded(caplog):
    """İş yaptığını kanıtlamayan araç başarı sayılmaz — ama sessiz kalmaz."""
    ex = _executor(ToolResult(success=True, verified=False, message="claimed"))

    with caplog.at_level(logging.WARNING, logger="JARVIS.Executor"):
        result = await ex.execute_tool("STUB_TOOL", "arg")

    assert result.success is False
    logged = " ".join(r.getMessage() for r in caplog.records)
    assert "Unverified success" in logged
    assert "StubTool" in logged


@pytest.mark.asyncio
async def test_genuine_failure_logs_no_mismatch_warning(caplog):
    """success=False + verified=False çelişki değil; uyarı basılmamalı."""
    ex = _executor(ToolResult(success=False, verified=False, message="failed"))

    with caplog.at_level(logging.WARNING, logger="JARVIS.Executor"):
        result = await ex.execute_tool("STUB_TOOL", "arg")

    assert result.success is False
    assert "Unverified success" not in " ".join(r.getMessage() for r in caplog.records)


# ── Depo genelinde sözleşme ──────────────────────────────────────────────────

def _success_without_verified() -> list[str]:
    """success=True ilan edip verified bildirmeyen ToolResult çağrıları."""
    root = pathlib.Path(__file__).resolve().parent.parent
    offenders = []

    for path in sorted(root.rglob("*.py")):
        rel = path.relative_to(root).as_posix()
        if rel.startswith(("tests/", "archive/")) or "_backup" in rel:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
            if name != "ToolResult":
                continue

            keywords = {k.arg for k in node.keywords if k.arg}
            success = None
            for k in node.keywords:
                if k.arg == "success" and isinstance(k.value, ast.Constant):
                    success = k.value.value
            if success is None and node.args and isinstance(node.args[0], ast.Constant):
                success = node.args[0].value

            if success is True and "verified" not in keywords:
                offenders.append(f"{rel}:{node.lineno}")

    return offenders


def test_no_tool_claims_success_without_verified():
    """Kapı yüzünden bu bir stil kuralı değil, çalışma zamanı sözleşmesi:
    verified bildirmeyen başarı yolu kullanıcıya HATA olarak döner."""
    offenders = _success_without_verified()

    assert offenders == [], (
        "Bu ToolResult(success=True) çağrıları verified bildirmiyor; "
        "Executor bunları success=False'a düşürür:\n  "
        + "\n  ".join(offenders)
    )
