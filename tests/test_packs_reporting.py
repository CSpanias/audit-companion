import json
from pathlib import Path

import pytest

from audit_companion.engine import build_results
from audit_companion.models import AssessmentPack, AssessmentResults, QuestionResponse
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
        executive_summary="**The review assessed** remote access security for {client_name}.",
        commentary_intro="A remote access review was conducted for {client_name}.",
        context_labels={
            "access_platform": "Remote access solution",
            "organization": "Organisation",
        },
    )

    assert json_path is not None
    exported = json.loads(json_path.read_text(encoding="utf-8"))
    html_report = html_path.read_text(encoding="utf-8")
    commentary = html_report.split("<h2>Commentary</h2>", 1)[1].split(
        "<h2>Remediation</h2>",
        1,
    )[0]
    assert exported["findings"][0]["question_id"] == "mfa-enabled"
    assert "<h1>&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;</h1>" in html_report
    assert "<script>alert(" not in html_report
    assert "<strong>" not in html_report
    assert "**" not in html_report
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
    assert "<h3>Configuration Summary</h3>" not in html_report
    assert "<table>" in commentary
    assert "Configuration Summary" not in commentary
    assert "<th scope=\"row\">Remote access solution</th>" in html_report
    assert "<th scope=\"row\">Organisation</th>" in html_report
    assert "<h3>Authentication</h3>" in html_report
    assert (
        "Multi-factor authentication is not consistently required." in html_report
    )
    assert "&lt;script&gt;Review the MFA configuration.&lt;/script&gt;" in html_report
    assert "Scope:" not in commentary
    assert "Remote access can be used without multi-factor authentication." not in (
        commentary
    )
    assert "<h4>" not in html_report
    assert "#### " not in html_report
    assert "<h2>Remediation</h2>" in html_report
    assert "Require MFA for all remote access." in html_report
    assert "<h2>References</h2>" not in html_report
    assert "<h3>References</h3>" in html_report
    assert "### References" in html_report
    assert "\n## References\n" not in html_report
    assert "https://www.cisa.gov/secure-our-world/use-strong-passwords" in html_report
    assert "Copy All Markdown" in html_report
    assert html_report.count("Copy Markdown") == 3
    assert 'data-copy="references-markdown"' not in html_report
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


def test_mdm_report_groups_findings_and_positive_controls_by_platform(
    tmp_path,
) -> None:
    pack = load_builtin_pack("mdm")
    results = build_results(
        pack,
        {
            "client_name": "Example Council",
            "platforms": ["iOS", "Android"],
            "mdm_vendor": "Microsoft Intune",
        },
        {},
        [
            QuestionResponse(
                question_id="intune-unsupported-os-version",
                answer="non_compliant",
                scope={"platforms": "Android"},
            ),
            QuestionResponse(
                question_id="intune-ios-host-pairing-allowed",
                answer="non_compliant",
                scope={"platforms": "iOS"},
            ),
            *[
                QuestionResponse(
                    question_id=question_id,
                    answer="compliant",
                    scope={"platforms": platform},
                )
                for question_id in (
                    "intune-jailbroken-rooted-devices",
                    "intune-remote-wipe-disabled",
                )
                for platform in ("iOS", "Android")
            ],
        ],
    )

    json_path, html_path = export_results(results, tmp_path, report_pack=pack)
    assert json_path is not None
    html_report = html_path.read_text(encoding="utf-8")
    exported = json.loads(json_path.read_text(encoding="utf-8"))
    commentary = html_report.split("<h2>Commentary</h2>", 1)[1].split(
        "<h2>Remediation</h2>",
        1,
    )[0]
    summary = html_report.split("<h2>Executive Summary</h2>", 1)[1].split(
        "<h2>Commentary</h2>",
        1,
    )[0]

    assert "<h3>iOS Devices</h3>" in commentary
    assert "<h3>Android Devices</h3>" in commentary
    assert "Device Security and Hardening." in commentary
    assert "Lifecycle and Compliance." in commentary
    assert "<strong>" not in html_report
    assert "**" not in html_report
    assert "Positive Observations" in commentary
    assert "Key strengths included" in summary
    assert "receive security updates from the device vendor" in commentary
    assert (
        "<p>Lifecycle and Compliance. Findings related to device lifecycle "
        "management and compliance oversight.</p>"
    ) in commentary
    assert "Non-compliant enrolled devices" not in html_report
    assert "Default and system applications" not in html_report
    assert "<h4>" not in html_report
    assert "positive_summary_commentary" not in exported["positive_observations"][0]


def test_remote_access_report_narrates_aovpn_controls_and_ongoing_actions(
    tmp_path,
) -> None:
    pack = load_builtin_pack("remote-access")
    results = build_results(
        pack,
        {
            "client_name": "East Suffolk Council",
            "remote_access_solution": "Microsoft Always On VPN",
            "vpn_authentication_method": "Machine Certificate",
            "identity_provider": "Active Directory",
            "tunnel_type": "Device Tunnel",
            "certificate_authority": "Active Directory Certificate Services (AD CS)",
            "split_tunnel_mode": "Split-by-Exception",
        },
        {},
        [
            QuestionResponse(
                question_id="aovpn-device-authentication-not-enforced",
                answer="compliant",
            ),
            QuestionResponse(
                question_id="vpn-unrestricted-split-tunnelling",
                answer="compliant",
            ),
            QuestionResponse(
                question_id="aovpn-route-validation-not-enforced",
                answer="compliant",
            ),
            QuestionResponse(
                question_id="weak-cryptography",
                answer="compliant",
            ),
            QuestionResponse(
                question_id="insufficient-logging",
                answer="compliant",
            ),
            QuestionResponse(
                question_id="user-access-not-reviewed",
                answer="non_compliant",
            ),
        ],
    )

    json_path, html_path = export_results(results, tmp_path, report_pack=pack)
    assert json_path is not None
    html_report = html_path.read_text(encoding="utf-8")
    exported = json.loads(json_path.read_text(encoding="utf-8"))
    commentary = html_report.split("<h2>Commentary</h2>", 1)[1].split(
        "<h2>Remediation</h2>",
        1,
    )[0]
    remediation = html_report.split("<h2>Remediation</h2>", 1)[1].split(
        "</section>",
        1,
    )[0]

    assert "Microsoft Always On VPN" in html_report
    assert "<strong>" not in html_report
    assert "**" not in html_report
    assert (
        "Device Tunnel connections required machine certificate authentication"
        in commentary
    )
    assert "Route restrictions and validation controls were enforced" in commentary
    assert "Strong, modern cryptographic algorithms were enforced" in commentary
    assert "Remote access permissions were not subject to periodic review" in commentary
    remediation_actions = remediation.split("<h3>References</h3>", 1)[0]
    assert remediation_actions.count("<li>") == 5
    assert "Establish a formal access review process" in remediation
    assert "AES-128" not in html_report
    assert "Perfect Forward Secrecy" not in html_report
    assert "summary_commentary" not in exported["findings"][0]
    assert "positive_commentary" not in exported["positive_observations"][0]


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
    remediation = html_report.split("<h2>Remediation</h2>", 1)[1].split(
        "</section>",
        1,
    )[0]
    assert "<h3>References</h3>" in remediation
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


def _export_voip_report(
    pack: AssessmentPack,
    results: AssessmentResults,
    output_dir: Path,
) -> tuple[Path | None, Path]:
    return export_results(results, output_dir, report_pack=pack)


def test_voip_report_uses_grouped_narrative_and_curated_remediation(
    tmp_path,
) -> None:
    pack = load_builtin_pack("voip")
    context = {
        "client_name": "East Suffolk Council",
        "voip_solution": "AudioCodes",
        "device_type": "Session Border Controller (SBC)",
        "deployment_type": "On-Premises",
        "identity_provider": "Microsoft Entra ID",
        "sip_provider": "Gamma",
        "platform_model": "Mediant",
        "software_version": "1.1",
        "management_address": "192.0.2.1",
    }
    results = build_results(
        pack,
        context,
        {},
        [
            QuestionResponse(question_id=question.id, answer="non_compliant")
            for question in pack.questions
        ],
    )

    json_path, html_path = _export_voip_report(pack, results, tmp_path)
    assert json_path is not None
    exported = json.loads(json_path.read_text(encoding="utf-8"))
    html_report = html_path.read_text(encoding="utf-8")
    summary = html_report.split("<h2>Executive Summary</h2>", 1)[1].split(
        "<h2>Commentary</h2>",
        1,
    )[0]
    commentary = html_report.split("<h2>Commentary</h2>", 1)[1].split(
        "<h2>Remediation</h2>",
        1,
    )[0]
    remediation = html_report.split("<h2>Remediation</h2>", 1)[1].split(
        "</section>",
        1,
    )[0]

    assert (
        "A VoIP security configuration review was performed for the "
        "East Suffolk Council AudioCodes platform"
    ) in summary
    assert "<strong>" not in html_report
    assert "**" not in html_report
    assert "Key observations included" not in summary
    assert "Unsupported Software Version." not in commentary
    assert "<h3>Authentication and Identity Security</h3>" in commentary
    assert "Directory authentication communications were not protected" in commentary
    assert "The table below summarises the key attributes" in commentary
    assert '<th scope="row">Organisation</th>' in html_report
    assert '<th scope="row">VoIP Platform Vendor</th>' in html_report
    assert "To address the identified observations and strengthen the security posture" in (
        remediation
    )
    assert "Establish a periodic access-review process" in remediation
    assert "Configure an appropriate User Inactivity Timeout and periodically review" not in (
        remediation
    )
    assert "no evidence of active compromise" not in html_report.casefold()
    assert "summary_commentary" not in exported["findings"][0]
    assert "commentary_paragraph" not in exported["findings"][0]


def test_voip_summary_only_describes_groups_with_findings(tmp_path) -> None:
    pack = load_builtin_pack("voip")
    results = build_results(
        pack,
        {
            "client_name": "Example",
            "voip_solution": "AudioCodes",
            "device_type": "Session Border Controller (SBC)",
        },
        {},
        [
            QuestionResponse(
                question_id="unsupported-software-version",
                answer="non_compliant",
            )
        ],
    )

    _, html_path = _export_voip_report(pack, results, tmp_path)
    summary = html_path.read_text(encoding="utf-8").split(
        "<h2>Commentary</h2>",
        1,
    )[0]

    assert "platform lifecycle management" in summary
    assert "authentication and identity" not in summary
    assert "security monitoring" not in summary


def test_html_export_can_omit_json_for_xml_mode(minimal_pack, tmp_path) -> None:
    results = build_results(minimal_pack, {}, {}, [])

    json_path, html_path = export_results(results, tmp_path, include_json=False)

    assert json_path is None
    assert html_path.is_file()
    assert not (tmp_path / "example-access-review-findings.json").exists()
    assert not (tmp_path / "example-access-review-report.md").exists()


@pytest.mark.parametrize("pack_id", ["mdm", "remote-access", "voip"])
def test_builtin_reports_share_plain_emphasis_and_nested_references(
    pack_id,
    tmp_path,
) -> None:
    pack = load_builtin_pack(pack_id)
    context: dict[str, str | list[str]] = {"client_name": "Example"}
    if pack_id == "mdm":
        context.update(
            {
                "platforms": ["iOS", "Android"],
                "mdm_vendor": "Microsoft Intune",
            }
        )
    elif pack_id == "remote-access":
        context["remote_access_solution"] = "Microsoft Always On VPN"
    else:
        context.update(
            {
                "voip_solution": "AudioCodes",
                "device_type": "Session Border Controller (SBC)",
            }
        )
    results = build_results(pack, context, {}, [])

    _, html_path = export_results(results, tmp_path, report_pack=pack)
    html_report = html_path.read_text(encoding="utf-8")
    commentary = html_report.split("<h2>Commentary</h2>", 1)[1].split(
        "<h2>Remediation</h2>",
        1,
    )[0]
    remediation = html_report.split("<h2>Remediation</h2>", 1)[1].split(
        "</section>",
        1,
    )[0]

    assert "<strong>" not in html_report
    assert "**" not in html_report
    assert "font-weight: normal" in html_report
    assert "Configuration Summary" not in commentary
    assert "<table>" in commentary
    assert "<h2>References</h2>" not in html_report
    assert "<h3>References</h3>" in remediation
    assert "\n## References\n" not in html_report
    assert "### References" in remediation
