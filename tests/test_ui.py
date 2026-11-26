from io import StringIO

from rich.console import Console

import audit_companion.ui as ui


def test_guidance_panels_are_capped_for_wide_terminals(monkeypatch) -> None:
    stream = StringIO()
    monkeypatch.setattr(
        ui,
        "console",
        Console(file=stream, width=180, color_system=None),
    )
    message = (
        "Review the configuration and confirm the expected security setting "
        "is present. "
    ) * 8

    ui.emit_panel("Evidence", message, "blue")

    rendered_lines = stream.getvalue().splitlines()
    assert max(map(len, rendered_lines)) <= ui.MAX_PANEL_WIDTH


def test_detail_guidance_uses_compact_label_without_a_panel(monkeypatch) -> None:
    stream = StringIO()
    monkeypatch.setattr(
        ui,
        "console",
        Console(file=stream, width=80, color_system=None),
    )

    ui.emit_detail("Where to check", "Devices > Compliance > Password", "yellow")

    rendered = stream.getvalue()
    assert "Where to check:" in rendered
    assert "Devices > Compliance > Password" in rendered
    assert "╭" not in rendered
