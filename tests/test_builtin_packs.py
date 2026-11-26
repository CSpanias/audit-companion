import re
import sys
from pathlib import Path

import pytest

from audit_companion import cli
from audit_companion.cli import build_parser
from audit_companion.engine import (
    applicable_items,
    build_results,
    expand_question_scopes,
)
from audit_companion.models import AssessmentPack, AssessmentResults
from audit_companion.packs import load_builtin_pack


@pytest.mark.parametrize("pack_id", ["mdm", "remote-access", "voip"])
def test_builtin_assessment_packs_load(pack_id: str) -> None:
    pack = load_builtin_pack(pack_id)

    assert pack.id == pack_id
    assert pack.questions


@pytest.mark.parametrize("command", ["mdm", "remote-access", "voip"])
def test_domain_command_starts_without_a_pack_path(command: str) -> None:
    args = build_parser().parse_args([command])

    assert args.command == command
    assert args.output_dir == Path("audit-companion")
    assert not hasattr(args, "pack")


@pytest.mark.parametrize("command", ["run", "validate"])
def test_custom_pack_commands_are_not_available(command: str) -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args([command, "assessment.yaml"])


@pytest.mark.parametrize("command", ["mdm", "remote-access", "voip"])
def test_domain_command_runs_its_builtin_pack_and_exports_reports(
    command: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        ["audit-companion", command, "--output-dir", str(tmp_path)],
    )
    loaded_pack_ids: list[str] = []

    def fake_interview(pack: AssessmentPack) -> AssessmentResults:
        loaded_pack_ids.append(pack.id)
        return build_results(pack, {}, {}, [])

    monkeypatch.setattr(cli, "run_interview", fake_interview)

    cli.main()

    assert loaded_pack_ids == [command]
    run_dirs = list(tmp_path.iterdir())
    assert len(run_dirs) == 1
    assert run_dirs[0].is_dir()
    assert re.fullmatch(rf"{command}-\d{{8}}-\d{{6}}-\d{{6}}", run_dirs[0].name)
    assert (run_dirs[0] / f"{command}-findings.json").is_file()
    assert (run_dirs[0] / f"{command}-report.html").is_file()
    assert not (run_dirs[0] / f"{command}-report.md").exists()


def test_mdm_controls_are_filtered_and_scoped_by_selected_platform() -> None:
    pack = load_builtin_pack("mdm")
    context = {"platforms": ["iOS", "Android"]}
    questions = applicable_items(pack.questions, context)
    instances = expand_question_scopes(questions, context)
    scopes_by_id: dict[str, list[dict[str, str]]] = {}
    for question, scope in instances:
        scopes_by_id.setdefault(question.id, []).append(scope)

    assert scopes_by_id["intune-unrestricted-external-media"] == [
        {"platforms": "Android"}
    ]
    assert scopes_by_id["intune-jailbroken-rooted-devices"] == [
        {"platforms": "iOS"},
        {"platforms": "Android"},
    ]


def test_remote_access_controls_follow_the_selected_solution() -> None:
    pack = load_builtin_pack("remote-access")
    aovpn = {
        question.id
        for question in applicable_items(
            pack.questions,
            {"remote_access_solution": "Microsoft Always On VPN"},
        )
    }
    pra = {
        question.id
        for question in applicable_items(
            pack.questions,
            {"remote_access_solution": "BeyondTrust PRA"},
        )
    }

    assert "aovpn-prelogon-connectivity-disabled" in aovpn
    assert "aovpn-prelogon-connectivity-disabled" not in pra
    assert "pra-update-management-not-defined" in pra
    assert "pra-update-management-not-defined" not in aovpn


def test_voip_pack_includes_the_generic_reference() -> None:
    pack = load_builtin_pack("voip")
    reference = "https://www.ncsc.gov.uk/guidance/private-branch-exchange-best-practice"

    assert all(reference in question.references for question in pack.questions)
