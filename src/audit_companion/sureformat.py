"""Internal SureFormat XML export for built-in assessments with finding mappings."""

import re
import xml.etree.ElementTree as ET
from collections.abc import Callable
from pathlib import Path

from audit_companion.models import AssessmentPack, AssessmentResults

ScopeKey = tuple[tuple[str, str], ...]


class SureFormatExportError(ValueError):
    """Raised when an assessment pack cannot be exported to SureFormat."""


def export_sureformat_xml(
    results: AssessmentResults,
    pack: AssessmentPack,
    output_dir: str | Path,
    hostname_for_scope: Callable[[dict[str, str]], str],
) -> tuple[list[Path], list[str]]:
    questions_by_id = {question.id: question for question in pack.questions}
    has_question_mappings = any(
        question.sureformat_id or question.sureformat_id_by_scope
        for question in pack.questions
    )
    if not pack.sureformat_assessment and not has_question_mappings:
        raise SureFormatExportError(
            f"Assessment pack {pack.id} has no SureFormat assessment or finding mappings."
        )

    grouped_findings: dict[ScopeKey, list[tuple[dict[str, object], str]]] = {}
    for response in results.responses:
        scope_key = tuple(sorted(response.scope.items()))
        grouped_findings.setdefault(scope_key, [])

    if not grouped_findings:
        grouped_findings[()] = []

    unmapped = []
    for finding in results.findings:
        question_id = str(finding["question_id"])
        question = questions_by_id[question_id]
        scope_value = finding.get("scope", {})
        scope = scope_value if isinstance(scope_value, dict) else {}
        vulnerability_id = question.sureformat_id or next(
            (
                question.sureformat_id_by_scope[value]
                for value in scope.values()
                if value in question.sureformat_id_by_scope
            ),
            None,
        )
        if not vulnerability_id:
            unmapped.append(question_id)
            continue
        scope_key = tuple(sorted(scope.items()))
        grouped_findings.setdefault(scope_key, []).append(
            (finding, vulnerability_id)
        )

    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    paths = []
    for scope_key, findings in sorted(grouped_findings.items()):
        scope = dict(scope_key)
        suffix = _scope_suffix(scope_key)
        output_path = destination / f"{pack.id}-findings{suffix}.xml"
        hostname = hostname_for_scope(scope).strip()
        if not hostname:
            raise SureFormatExportError(
                f"A non-empty hostname is required for scope {scope or 'assessment'}."
            )

        root = ET.Element("items", source="SureFormat", version="1.0.0")
        item = ET.SubElement(root, "item", ipaddress="", hostname=hostname)
        services = ET.SubElement(item, "services")
        service = ET.SubElement(
            services,
            "service",
            name="",
            port="",
            protocol="tcp",
        )
        vulnerabilities = ET.SubElement(service, "vulnerabilities")

        if pack.sureformat_assessment:
            vulnerability = ET.SubElement(
                vulnerabilities,
                "vulnerability",
                id=pack.sureformat_assessment.id,
            )
            ET.SubElement(vulnerability, "information").text = (
                pack.sureformat_assessment.description
            )

        for finding, vulnerability_id in findings:
            vulnerability = ET.SubElement(
                vulnerabilities,
                "vulnerability",
                id=vulnerability_id,
            )
            ET.SubElement(vulnerability, "information").text = str(
                finding["description"]
            )

        tree = ET.ElementTree(root)
        ET.indent(tree, space="    ")
        tree.write(output_path, encoding="utf-8", xml_declaration=False)
        paths.append(output_path)

    return paths, sorted(set(unmapped))


def _scope_suffix(scope_key: ScopeKey) -> str:
    if not scope_key:
        return ""
    parts = []
    for field_id, value in scope_key:
        parts.extend((_slug(field_id), _slug(value)))
    return "-" + "-".join(parts)


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "scope"
