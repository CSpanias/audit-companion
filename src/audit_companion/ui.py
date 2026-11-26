"""Shared Rich console presentation for guided assessments."""

import re
from collections.abc import Callable

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()
MAX_PANEL_WIDTH = 96
_DETAIL_LINE_START = re.compile(
    r"^(?:[-*]\s|/\S|(?:Setup|Management|Troubleshoot)\s*>)"
)


def _format_detail(message: str) -> str:
    lines = message.strip().splitlines()
    formatted = ""
    previous_blank = False
    for line in lines:
        line = line.strip()
        if not line:
            previous_blank = True
            continue
        is_list_item = line.startswith(("- ", "* "))
        if is_list_item:
            line = f"  {line}"
        if formatted:
            if previous_blank:
                formatted += "\n\n"
            elif _DETAIL_LINE_START.match(line.lstrip()):
                formatted += "\n"
            else:
                formatted += " "
        formatted += line
        previous_blank = False
    return formatted


def emit(
    message: str,
    output_fn: Callable[[str], None] | None = None,
    style: str | None = None,
) -> None:
    if output_fn is not None:
        output_fn(message)
        return
    console.print(Text(message, style=style))


def emit_progress(
    completed: int,
    total: int,
    counter: str,
    output_fn: Callable[[str], None] | None = None,
) -> None:
    filled = completed * 20 // total
    bar = "#" * filled + "-" * (20 - filled)
    emit(f"Progress: [{bar}] {counter}", output_fn, "cyan")


def emit_panel(
    title: str,
    message: str,
    border_style: str,
    output_fn: Callable[[str], None] | None = None,
) -> None:
    if output_fn is not None:
        output_fn(f"{title}: {message}")
        return
    console.print(
        Panel.fit(
            Text(message),
            title=title,
            border_style=border_style,
            width=min(MAX_PANEL_WIDTH, console.width),
        )
    )


def emit_detail(
    label: str,
    message: str,
    style: str,
    output_fn: Callable[[str], None] | None = None,
) -> None:
    message = _format_detail(message)
    separator = "\n" if message.startswith(("  - ", "  * ")) else " "
    if output_fn is not None:
        output_fn(f"{label}:{separator}{message}")
        return
    text = Text()
    text.append(f"{label}:{separator}", style=f"bold {style}")
    text.append(message)
    console.print(text)


def prompt(
    message: str,
    input_fn: Callable[[str], str] | None = None,
) -> str:
    return input_fn(message) if input_fn is not None else console.input(message)
