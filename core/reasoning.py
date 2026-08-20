"""Strip reasoning-model monologues out of LLM text.

Qwen/DeepSeek emit <think>...</think>. Token cutoff often leaves the tag
open; a closed-only regex then leaks the whole chain — including quoted
[PROTOCOL:] examples — into speech and into execute_single."""

from __future__ import annotations

import re

_CLOSED_THINK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_UNCLOSED_THINK = re.compile(r"<think>.*\Z", re.DOTALL | re.IGNORECASE)


def strip_reasoning(text: str | None) -> str:
    if not text:
        return ""
    cleaned = _CLOSED_THINK.sub("", text)
    cleaned = _UNCLOSED_THINK.sub("", cleaned)
    return cleaned.strip()
