import json

from audit_companion.engine import build_results
from audit_companion.models import QuestionResponse
from audit_companion.packs import load_pack
from audit_companion.reporting import export_results


def test_example_pack_validates_and_exports_common_reports(tmp_path) -> None:
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

    results = results.model_copy(update={"pack_title": '<script>alert("x")</script>'})
    json_path, markdown_path, html_path = export_results(results, tmp_path)

    exported = json.loads(json_path.read_text(encoding="utf-8"))
    report = markdown_path.read_text(encoding="utf-8")
    html_report = html_path.read_text(encoding="utf-8")
    assert exported["findings"][0]["question_id"] == "mfa-enabled"
    assert "Findings: 1" in report
    assert "Positive observations: 0" in report
    assert "<h1>&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;</h1>" in html_report
    assert "<script>alert(" not in html_report
