import json

from audit_companion.engine import build_results
from audit_companion.models import QuestionResponse
from audit_companion.packs import load_pack
from audit_companion.reporting import export_results


def test_example_pack_validates_and_exports_html_and_json(tmp_path) -> None:
    pack = load_pack("examples/minimal.yaml")
    results = build_results(
        pack,
        {"access_platform": "Platform A", "organization": "Example"},
        {},
        [
            QuestionResponse(question_id="mfa-enabled", answer="non_compliant"),
            QuestionResponse(question_id="access-review", answer="unknown"),
        ],
    )

    finding = dict(results.findings[0])
    finding.update(
        commentary_group="Authentication",
        commentary="<script>Review the MFA configuration.</script>",
        solution="Require MFA for all remote access.",
    )
    results = results.model_copy(
        update={
            "pack_title": '<script>alert("x")</script>',
            "findings": [finding],
        }
    )
    json_path, html_path = export_results(results, tmp_path)

    assert json_path is not None
    exported = json.loads(json_path.read_text(encoding="utf-8"))
    html_report = html_path.read_text(encoding="utf-8")
    assert exported["findings"][0]["question_id"] == "mfa-enabled"
    assert "<h1>&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;</h1>" in html_report
    assert "<script>alert(" not in html_report
    assert "<h2>Executive Summary</h2>" in html_report
    assert "one non-compliant finding requiring remediation" in html_report
    assert "One response was marked unknown" in html_report
    assert "<h2>Technical Commentary</h2>" in html_report
    assert "&lt;script&gt;Review the MFA configuration.&lt;/script&gt;" in html_report
    assert "<h2>Remediation Guidance</h2>" in html_report
    assert "Require MFA for all remote access." in html_report
    assert not (tmp_path / "example-access-review-report.md").exists()


def test_html_export_can_omit_json_for_xml_mode(tmp_path) -> None:
    pack = load_pack("examples/minimal.yaml")
    results = build_results(pack, {}, {}, [])

    json_path, html_path = export_results(results, tmp_path, include_json=False)

    assert json_path is None
    assert html_path.is_file()
    assert not (tmp_path / "example-access-review-findings.json").exists()
    assert not (tmp_path / "example-access-review-report.md").exists()
