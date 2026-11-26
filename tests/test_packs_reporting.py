import json

import pytest

from audit_companion.engine import build_results
from audit_companion.models import QuestionResponse
from audit_companion.packs import load_builtin_pack
from audit_companion.reporting import export_results


def test_assessment_exports_html_and_json(minimal_pack, tmp_path) -> None:
    results = build_results(
        minimal_pack,
        {"access_platform": "Platform A", "organization": "Example"},
        {},
        [
            QuestionResponse(question_id="mfa-enabled", answer="non_compliant"),
            QuestionResponse(question_id="access-review", answer="unknown"),
        ],
    )

    finding = dict(results.findings[0])
    finding.update(
        theme="Authentication",
        commentary="<script>Review the MFA configuration.</script>",
        solution="Require MFA for all remote access.",
    )
    results = results.model_copy(
        update={
            "pack_title": '<script>alert("x")</script>',
            "findings": [finding],
        }
    )
    json_path, html_path = export_results(
        results,
        tmp_path,
        executive_summary=minimal_pack.executive_summary,
        commentary_intro="A remote access review was conducted for {client_name}.",
        context_labels={
            "access_platform": "Remote access solution",
            "organization": "Organisation",
        },
    )

    assert json_path is not None
    exported = json.loads(json_path.read_text(encoding="utf-8"))
    html_report = html_path.read_text(encoding="utf-8")
    assert exported["findings"][0]["question_id"] == "mfa-enabled"
    assert "<h1>&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;</h1>" in html_report
    assert "<script>alert(" not in html_report
    assert "<h2>Executive Summary</h2>" in html_report
    assert "The review assessed remote access security for Example." in html_report
    assert "The assessment identified opportunities for improvement in Authentication." in html_report
    assert "Key observations included Multi-factor authentication" in html_report
    assert "The assessment reviewed" not in html_report
    assert "Some controls could not be verified and require further evidence" in (
        html_report
    )
    assert "<h2>Commentary</h2>" in html_report
    assert "A remote access review was conducted for Example." in html_report
    assert "<h3>Configuration Summary</h3>" in html_report
    assert "<th scope=\"row\">Remote access solution</th>" in html_report
    assert "<th scope=\"row\">Organisation</th>" in html_report
    assert "<h3>Authentication</h3>" in html_report
    assert (
        "<strong>Multi-factor authentication is not consistently required.</strong>"
        in html_report
    )
    assert "&lt;script&gt;Review the MFA configuration.&lt;/script&gt;" in html_report
    commentary = html_report.split("<h2>Commentary</h2>", 1)[1]
    commentary = commentary.split(
        "<h2>Remediation</h2>",
        1,
    )[0]
    assert "Scope:" not in commentary
    assert "Remote access can be used without multi-factor authentication." not in (
        commentary
    )
    assert "<h4>" not in html_report
    assert "#### " not in html_report
    assert "<h2>Remediation</h2>" in html_report
    assert "Require MFA for all remote access." in html_report
    assert "<h2>References</h2>" in html_report
    assert "https://www.cisa.gov/secure-our-world/use-strong-passwords" in html_report
    assert "Copy All Markdown" in html_report
    assert html_report.count("Copy Markdown") == 4
    assert 'data-copy="executive-summary-markdown"' in html_report
    assert "Copied Markdown to clipboard." in html_report
    assert not (tmp_path / "example-access-review-report.md").exists()


def test_mdm_summary_reflects_selected_platforms(tmp_path) -> None:
    pack = load_builtin_pack("mdm")
    results = build_results(
        pack,
        {"client_name": "Example", "platforms": ["iOS"]},
        {},
        [],
    )

    _, html_path = export_results(
        results,
        tmp_path,
        executive_summary=pack.executive_summary,
    )
    summary = html_path.read_text(encoding="utf-8").split(
        "<h2>Commentary</h2>",
        1,
    )[0]

    assert "managed iOS devices" in summary
    assert "managed Android devices" not in summary


def test_commentary_includes_positive_controls_and_global_references(
    minimal_pack,
    tmp_path,
) -> None:
    results = build_results(
        minimal_pack,
        {"access_platform": "Platform A", "organization": "Example"},
        {},
        [
            QuestionResponse(question_id="mfa-enabled", answer="compliant"),
            QuestionResponse(question_id="access-review", answer="non_compliant"),
        ],
    )

    _, html_path = export_results(
        results,
        tmp_path,
        context_labels={
            "access_platform": "Remote access solution",
            "organization": "Organisation",
        },
    )
    html_report = html_path.read_text(encoding="utf-8")
    commentary = html_report.split("<h2>Commentary</h2>", 1)[1]
    commentary = commentary.split("<h2>Remediation</h2>", 1)[0]

    assert "<h3>Positive Security Controls</h3>" in commentary
    assert "Multi-factor authentication is required for remote access." in commentary
    assert "<h2>References</h2>" in html_report
    assert "https://www.cisa.gov/secure-our-world/use-strong-passwords" in html_report
    assert "- [https://www.cisa.gov/secure-our-world/use-strong-passwords]" in (
        html_report
    )


@pytest.mark.parametrize("pack_id", ["mdm", "remote-access", "voip"])
def test_builtin_commentary_is_grouped_without_scope_labels(pack_id, tmp_path) -> None:
    pack = load_builtin_pack(pack_id)
    question = pack.questions[0]
    context: dict[str, str | list[str]] = {"client_name": "Example"}
    if pack_id == "mdm":
        context["platforms"] = ["iOS"]
    group = (
        question.commentary_group
        or question.theme
        or question.section
        or "Assessment findings"
    )
    results = build_results(
        pack,
        context,
        {},
        [
            QuestionResponse(
                question_id=question.id,
                answer="non_compliant",
                scope={"platforms": "iOS"},
            )
        ],
    )

    _, html_path = export_results(
        results,
        tmp_path,
        executive_summary=pack.executive_summary,
        commentary_intro=pack.commentary_intro,
        context_labels={
            field.id: field.report_label or field.label for field in pack.context
        },
    )
    html_report = html_path.read_text(encoding="utf-8")
    commentary = html_report.split("<h2>Commentary</h2>", 1)[1]
    commentary = commentary.split("<h2>Remediation</h2>", 1)[0]

    assert f"<h3>{group}</h3>" in commentary
    assert "Scope:" not in commentary


def test_html_export_can_omit_json_for_xml_mode(minimal_pack, tmp_path) -> None:
    results = build_results(minimal_pack, {}, {}, [])

    json_path, html_path = export_results(results, tmp_path, include_json=False)

    assert json_path is None
    assert html_path.is_file()
    assert not (tmp_path / "example-access-review-findings.json").exists()
    assert not (tmp_path / "example-access-review-report.md").exists()
