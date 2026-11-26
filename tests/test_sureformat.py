import xml.etree.ElementTree as ET

import pytest

from audit_companion.engine import build_results
from audit_companion.models import QuestionResponse
from audit_companion.packs import load_pack
from audit_companion.sureformat import (
    SureFormatExportError,
    export_sureformat_xml,
)


def test_sureformat_export_groups_findings_and_reports_unmapped(tmp_path) -> None:
    pack = load_pack("examples/minimal.yaml")
    pack.questions[0].sureformat_id = "SC-100"
    results = build_results(
        pack,
        {"access_platform": "Platform A", "organization": "Example"},
        {},
        [
            QuestionResponse(
                question_id="mfa-enabled",
                answer="non_compliant",
                scope={"access_platform": "Platform A"},
            ),
            QuestionResponse(
                question_id="access-review",
                answer="non_compliant",
                scope={"access_platform": "Platform B"},
            ),
        ],
    )

    xml_paths, unmapped = export_sureformat_xml(
        results,
        pack,
        tmp_path,
        lambda scope: f"asset-{scope['access_platform'].lower()}",
    )

    assert [path.name for path in xml_paths] == [
        "example-access-review-findings-access-platform-platform-a.xml",
        "example-access-review-findings-access-platform-platform-b.xml",
    ]
    assert unmapped == ["access-review"]
    root = ET.parse(xml_paths[0]).getroot()
    assert root.find(".//item").attrib["hostname"] == "asset-platform a"
    assert root.find(".//vulnerability").attrib["id"] == "SC-100"


def test_sureformat_export_requires_pack_mappings(tmp_path) -> None:
    pack = load_pack("examples/minimal.yaml")
    results = build_results(
        pack,
        {"access_platform": "Platform A", "organization": "Example"},
        {},
        [],
    )

    with pytest.raises(SureFormatExportError, match="no SureFormat finding mappings"):
        export_sureformat_xml(results, pack, tmp_path, lambda _scope: "asset")
