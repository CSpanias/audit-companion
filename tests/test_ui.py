from io import StringIO

from rich.console import Console
from rich.text import Text

import audit_companion.ui as ui
from audit_companion.engine import collect_context, conduct_review
from audit_companion.packs import load_builtin_pack


def test_progress_uses_rich_bar_and_updates_with_completed_controls(monkeypatch) -> None:
    stream = StringIO()
    monkeypatch.setattr(
        ui,
        "console",
        Console(
            file=stream,
            width=80,
            color_system="standard",
            force_terminal=True,
            legacy_windows=False,
        ),
    )

    ui.emit_progress(0, 2, "1/2 iOS")
    ui.emit_progress(1, 2, "2/2 iOS")
    ui.emit_progress(2, 2, "2/2 iOS completed")

    lines = stream.getvalue().splitlines()
    plain_lines = [Text.from_ansi(line).plain for line in lines]
    assert [line.split()[-2:] for line in plain_lines[:2]] == [
        ["1/2", "iOS"],
        ["2/2", "iOS"],
    ]
    assert plain_lines[2].endswith("2/2 iOS completed")
    assert all("━" in line for line in plain_lines)
    assert lines[0].split("1/2")[0] != lines[1].split("2/2")[0]
    assert lines[1].split("2/2")[0] != lines[2].split("2/2")[0]


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


def test_voip_software_version_evidence_uses_available_terminal_width(monkeypatch) -> None:
    stream = StringIO()
    monkeypatch.setattr(
        ui,
        "console",
        Console(file=stream, width=220, color_system=None),
    )
    pack = load_builtin_pack("voip")
    field = next(field for field in pack.context if field.id == "software_version")
    answers = iter(["1", ""])

    collect_context(
        [field],
        context={"voip_solution": "AudioCodes"},
        input_fn=lambda _prompt: next(answers),
    )

    evidence_lines = [
        line for line in stream.getvalue().splitlines() if line.startswith("Evidence:")
    ]
    assert evidence_lines == [
        "Evidence: Record the currently installed software, firmware, or operating "
        "system version where available. This information is used to assess platform "
        "supportability and patch status."
    ]


def test_voip_mfa_guidance_reflows_prose_and_preserves_examples(monkeypatch) -> None:
    stream = StringIO()
    monkeypatch.setattr(
        ui,
        "console",
        Console(file=stream, width=200, color_system=None),
    )
    pack = load_builtin_pack("voip")
    question = next(
        question for question in pack.questions if question.id == "admin-mfa-not-enforced"
    )
    answers = iter(["1", ""])

    conduct_review(
        [question],
        {"voip_solution": "AudioCodes"},
        input_fn=lambda _prompt: next(answers),
    )

    rendered = stream.getvalue()
    assert (
        "If administrative access relies solely on local AudioCodes accounts, MFA may "
        "not be supported and the control may be assessed as Not Applicable."
    ) in rendered
    assert (
        "Expected: MFA is enforced for administrative access where the deployment "
        "architecture provides MFA capability."
    ) in rendered
    assert "Examples include:\n  - AudioCodes Live / IAM\n" in rendered


def test_voip_expected_values_render_as_an_indented_list(monkeypatch) -> None:
    stream = StringIO()
    monkeypatch.setattr(
        ui,
        "console",
        Console(file=stream, width=120, color_system=None),
    )
    pack = load_builtin_pack("voip")
    question = next(
        question for question in pack.questions if question.id == "insecure-ldap-communication"
    )
    answers = iter(["1", ""])

    conduct_review(
        [question],
        {"voip_solution": "AudioCodes"},
        input_fn=lambda _prompt: next(answers),
    )

    assert "Expected:\n  - Use TLS = Yes\n  - TLS Context assigned\n" in stream.getvalue()


def test_detail_wraps_long_prose_to_narrow_terminal(monkeypatch) -> None:
    stream = StringIO()
    monkeypatch.setattr(
        ui,
        "console",
        Console(file=stream, width=40, color_system=None),
    )

    ui.emit_detail(
        "Evidence",
        "Review authentication\nsettings and verify that access is restricted.",
        "blue",
    )

    lines = stream.getvalue().splitlines()
    assert len(lines) > 1
    assert max(map(len, lines)) <= 40
    assert " ".join(line.strip() for line in lines) == (
        "Evidence: Review authentication settings and verify that access is restricted."
    )


def test_detail_reflows_prose_and_preserves_lists_and_locations(monkeypatch) -> None:
    stream = StringIO()
    monkeypatch.setattr(
        ui,
        "console",
        Console(file=stream, width=180, color_system=None),
    )

    ui.emit_detail(
        "Evidence",
        "Review authentication\nsettings.\n\nConfirm:\n- First control\n- Second control",
        "blue",
    )
    ui.emit_detail(
        "Expected",
        "- Use TLS = Yes\n- TLS Context assigned",
        "green",
    )
    ui.emit_detail(
        "Where to check",
        "/login > Reports > Access\n/login > Reports > Vault",
        "yellow",
    )

    assert stream.getvalue().splitlines() == [
        "Evidence: Review authentication settings.",
        "",
        "Confirm:",
        "  - First control",
        "  - Second control",
        "Expected:",
        "  - Use TLS = Yes",
        "  - TLS Context assigned",
        "Where to check: /login > Reports > Access",
        "/login > Reports > Vault",
    ]
