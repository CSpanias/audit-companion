"""Shared Rich console presentation for guided assessments."""

from collections.abc import Callable

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()
MAX_PANEL_WIDTH = 96


def emit(
    message: str,
    output_fn: Callable[[str], None] | None = None,
    style: str | None = None,
) -> None:
    if output_fn is not None:
        output_fn(message)
        return
    console.print(Text(message, style=style))


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
    if output_fn is not None:
        output_fn(f"{label}: {message}")
        return
    text = Text()
    text.append(f"{label}: ", style=f"bold {style}")
    text.append(message)
    console.print(text)


def prompt(
    message: str,
    input_fn: Callable[[str], str] | None = None,
) -> str:
    return input_fn(message) if input_fn is not None else console.input(message)
