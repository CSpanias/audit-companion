import xml.etree.ElementTree as ET

import pytest

from audit_companion import cli
from audit_companion.engine import build_results
from audit_companion.models import (
    AssessmentResults,
    QuestionResponse,
    SureFormatAssessment,
)
from audit_companion.packs import load_builtin_pack
from audit_companion.sureformat import (
    SureFormatExportError,
    export_sureformat_xml,
)


@pytest.mark.parametrize(
    ("platform", "expected_hostname"),
    [("Android", "android"), ("iOS", "ios")],
)
def test_sureformat_hostname_defaults_for_mobile_platforms(
    monkeypatch,
    platform,
    expected_hostname,
) -> None:
    prompts = []
    monkeypatch.setattr(
        cli.console,
        "input",
        lambda prompt: prompts.append(prompt) or "",
    )

    assert cli._prompt_hostname({"platforms": platform}) == expected_hostname
    assert prompts == [
        f"SureCloud hostname for platforms={platform} [{expected_hostname}]: "
    ]


def test_sureformat_export_groups_findings_and_reports_unmapped(minimal_pack, tmp_path) -> None:
    pack = minimal_pack
    pack.sureformat_assessment = SureFormatAssessment(
        id="SC-9941",
        description="A remote access review was performed.",
    )
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
    assert [
        item.attrib["id"] for item in root.findall(".//vulnerability")
    ] == ["SC-9941", "SC-100"]
    second_root = ET.parse(xml_paths[1]).getroot()
    assert [
        item.attrib["id"] for item in second_root.findall(".//vulnerability")
    ] == ["SC-9941"]


def test_sureformat_export_requires_pack_mappings(minimal_pack, tmp_path) -> None:
    pack = minimal_pack
    results = build_results(
        pack,
        {"access_platform": "Platform A", "organization": "Example"},
        {},
        [],
    )

    with pytest.raises(
        SureFormatExportError,
        match="no SureFormat assessment or finding mappings",
    ):
        export_sureformat_xml(results, pack, tmp_path, lambda _scope: "asset")


@pytest.mark.parametrize(
    ("pack_id", "expected_id"),
    [
        ("mdm", "SC-2142"),
        ("remote-access", "SC-9941"),
        ("voip", "SC-1830"),
    ],
)
def test_sureformat_export_always_includes_assessment_mapping(
    pack_id: str,
    expected_id: str,
    tmp_path,
) -> None:
    pack = load_builtin_pack(pack_id)
    results = AssessmentResults(
        pack_id=pack.id,
        pack_title=pack.title,
        pack_version=pack.version,
        context={},
        context_notes={},
        responses=[],
        findings=[],
        positive_observations=[],
    )

    xml_paths, unmapped = export_sureformat_xml(
        results,
        pack,
        tmp_path,
        lambda _scope: "assessment-asset",
    )

    assert unmapped == []
    assert len(xml_paths) == 1
    assert [
        item.attrib["id"]
        for item in ET.parse(xml_paths[0]).findall(".//vulnerability")
    ] == [expected_id]


def test_sureformat_export_can_map_a_finding_by_scope(minimal_pack, tmp_path) -> None:
    pack = minimal_pack
    pack.questions[0].sureformat_id_by_scope = {"Platform A": "SC-101"}
    results = build_results(
        pack,
        {"access_platform": "Platform A", "organization": "Example"},
        {},
        [
            QuestionResponse(
                question_id="mfa-enabled",
                answer="non_compliant",
                scope={"access_platform": "Platform A"},
            )
        ],
    )

    xml_paths, unmapped = export_sureformat_xml(
        results,
        pack,
        tmp_path,
        lambda _scope: "asset-platform-a",
    )

    assert unmapped == []
    assert ET.parse(xml_paths[0]).find(".//vulnerability").attrib["id"] == "SC-101"
