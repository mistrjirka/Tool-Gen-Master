"""Load standalone stage prompts from packaged ``.md`` resources.

Prompts live as plain Markdown under ``tool_gen/prompts/`` so they can be read
and edited without touching code. No giant inline prompt strings, no runtime
``mkdir`` of prompt trees: resources ship inside the wheel via package data.
"""

from __future__ import annotations

from importlib import resources


def load_prompt(stage: str, name: str) -> str:
    """Read ``tool_gen/prompts/<stage>/<name>.md`` and return its stripped text."""
    text = (resources.files(__package__) / stage / f"{name}.md").read_text(
        encoding="utf-8"
    )
    stripped = text.strip()
    if not stripped:
        raise ValueError(f"prompt {stage}/{name} is empty")
    return stripped


def writer_prompt() -> str:
    return load_prompt("writer", "base") + "\n\n" + load_prompt("writer", "bias_fixes")


def reader_prompt() -> str:
    return load_prompt("reader", "base") + "\n\n" + load_prompt("reader", "targeted")
