"""Common JSON and HTML assessment exports."""

import json
import re
from collections.abc import Mapping
from html import escape
from pathlib import Path
from urllib.parse import urlparse

from audit_companion.engine import applies, expand_question_scopes
from audit_companion.models import AssessmentPack, AssessmentResults, ReportGroup


def export_results(
    results: AssessmentResults,
    output_dir: str | Path,
    include_json: bool = True,
    executive_summary: str | None = None,
    commentary_intro: str | None = None,
    context_labels: Mapping[str, str] | None = None,
    executive_summary_findings_intro: str | None = None,
    executive_summary_conclusion: str | None = None,
    commentary_findings_intro: str | None = None,
    configuration_intro: str | None = None,
    remediation_intro: str | None = None,
    report_groups: Mapping[str, ReportGroup] | None = None,
    report_pack: AssessmentPack | None = None,
) -> tuple[Path | None, Path]:
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    json_path = destination / f"{results.pack_id}-findings.json" if include_json else None
    html_path = destination / f"{results.pack_id}-report.html"

    if json_path:
        json_path.write_text(
            results.model_dump_json(indent=2) + "\n",
            encoding="utf-8",
        )
    render_results = results
    positive_summary_intro = None
    positive_summary_conclusion = None
    maintenance_recommendations: list[str] = []
    report_scope_field = None
    assessment_complete = False
    if report_pack:
        executive_summary = report_pack.executive_summary
        executive_summary_findings_intro = (
            report_pack.executive_summary_findings_intro
        )
        executive_summary_conclusion = report_pack.executive_summary_conclusion
        positive_summary_intro = report_pack.positive_summary_intro
        positive_summary_conclusion = (
            report_pack.executive_summary_positive_conclusion
        )
        commentary_intro = report_pack.commentary_intro
        commentary_findings_intro = report_pack.commentary_findings_intro
        configuration_intro = report_pack.configuration_intro
        remediation_intro = report_pack.remediation_intro
        report_groups = report_pack.report_groups
        maintenance_recommendations = report_pack.maintenance_recommendations
        report_scope_field = report_pack.report_scope_field
        assessment_complete = _assessment_is_complete(results, report_pack)
        context_labels = {
            field.id: field.report_label or field.label
            for field in report_pack.context
        }
        questions_by_id = {question.id: question for question in report_pack.questions}
        report_findings = []
        for finding in results.findings:
            question = questions_by_id.get(str(finding.get("question_id")))
            if question is None:
                report_findings.append(finding)
                continue
            report_findings.append(
                {
                    **finding,
                    "summary_commentary": question.summary_commentary,
                    "commentary_paragraph": question.commentary_paragraph,
                }
            )
        report_positives = []
        for observation in results.positive_observations:
            question = questions_by_id.get(str(observation.get("question_id")))
            if question is None:
                report_positives.append(observation)
                continue
            report_positives.append(
                {
                    **observation,
                    "positive_commentary": question.positive_commentary,
                    "positive_summary_commentary": (
                        question.positive_summary_commentary
                    ),
                    "positive_summary_priority": (
                        question.positive_summary_priority
                    ),
                }
            )
        render_results = results.model_copy(
            update={
                "findings": report_findings,
                "positive_observations": report_positives,
            }
        )
    html_path.write_text(
        _render_html(
            render_results,
            executive_summary,
            commentary_intro,
            context_labels,
            executive_summary_findings_intro,
            executive_summary_conclusion,
            commentary_findings_intro,
            configuration_intro,
            remediation_intro,
            report_groups,
            positive_summary_intro,
            positive_summary_conclusion,
            maintenance_recommendations,
            report_scope_field,
            assessment_complete,
        ),
        encoding="utf-8",
    )
    return json_path, html_path


def _render_html(
    results: AssessmentResults,
    executive_summary: str | None = None,
    commentary_intro: str | None = None,
    context_labels: Mapping[str, str] | None = None,
    executive_summary_findings_intro: str | None = None,
    executive_summary_conclusion: str | None = None,
    commentary_findings_intro: str | None = None,
    configuration_intro: str | None = None,
    remediation_intro: str | None = None,
    report_groups: Mapping[str, ReportGroup] | None = None,
    positive_summary_intro: str | None = None,
    positive_summary_conclusion: str | None = None,
    maintenance_recommendations: list[str] | None = None,
    report_scope_field: str | None = None,
    assessment_complete: bool = False,
) -> str:
    configuration = _configuration_entries(results, context_labels or {})
    configuration_headers = (
        ("Configuration Item", "Setting", "Assessor Notes")
        if any(note for _, _, note in configuration)
        else ("Configuration Item", "Setting")
    )
    configuration_html = ""
    if configuration:
        configuration_rows = [
            _render_configuration_row(
                item,
                setting,
                note,
                len(configuration_headers) == 3,
            )
            for item, setting, note in configuration
        ]
        configuration_html = _render_table(configuration_headers, configuration_rows)

    report_groups = report_groups or {}
    summary_paragraphs = _executive_summary_paragraphs(
        results,
        executive_summary,
        executive_summary_findings_intro,
        executive_summary_conclusion,
        report_groups,
        positive_summary_intro,
        positive_summary_conclusion,
        assessment_complete,
    )
    executive_summary_html = "\n".join(
        f"<p>{_render_inline_text(paragraph)}</p>"
        for paragraph in summary_paragraphs
    )
    rendered_commentary_intro = _format_report_text(commentary_intro, results)
    findings_intro = _format_findings_intro(
        commentary_findings_intro,
        results,
        report_groups,
    )
    rendered_configuration_intro = _format_report_text(configuration_intro, results)
    commentary_html = _render_commentary(
        results.findings,
        results.positive_observations,
        rendered_commentary_intro,
        findings_intro,
        rendered_configuration_intro,
        configuration_html,
        report_groups,
        report_scope_field,
        results.context.get(report_scope_field) if report_scope_field else None,
    )
    remediation_html = _render_remediation(
        results.findings,
        remediation_intro,
        maintenance_recommendations or [],
    )
    references = _report_references(results)
    references_html = _render_references(references)
    summary_markdown = _markdown_section(
        "Executive Summary",
        "\n\n".join(summary_paragraphs),
    )
    commentary_markdown = _commentary_markdown(
        results.findings,
        results.positive_observations,
        rendered_commentary_intro,
        findings_intro,
        rendered_configuration_intro,
        configuration_headers,
        configuration,
        report_groups,
        report_scope_field,
        results.context.get(report_scope_field) if report_scope_field else None,
    )
    remediation_markdown = _remediation_markdown(
        results.findings,
        remediation_intro,
        maintenance_recommendations or [],
    )
    references_markdown = _references_markdown(references)
    remediation_markdown = "\n\n".join(
        (remediation_markdown, references_markdown)
    )
    all_markdown = "\n\n".join(
        (
            summary_markdown,
            commentary_markdown,
            remediation_markdown,
        )
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(results.pack_title)} - Assessment Report</title>
  <style>
    :root {{ color-scheme: light; font-family: system-ui, sans-serif; color: #172033; background: #f3f6fa; }}
    body {{ margin: 0; }}
    header {{ padding: 2rem max(1rem, calc((100% - 1100px) / 2)); background: #10233f; color: white; }}
    header h1 {{ margin: 0; }}
    main {{ max-width: 1100px; margin: 2rem auto; padding: 0 1rem 2rem; }}
    section {{ background: white; border: 1px solid #dce3ed; border-radius: .6rem; margin-bottom: 1rem; padding: 1.25rem; }}
    h1, h2, h3 {{ line-height: 1.2; font-weight: normal; }}
    h2 {{ border-bottom: 1px solid #dce3ed; padding-bottom: .5rem; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #dce3ed; padding: .6rem; text-align: left; vertical-align: top; }}
    th {{ background: #f3f6fa; font-weight: normal; }}
    .observation {{ border-left: 4px solid #607d9d; margin: 1rem 0; padding: .25rem 1rem; }}
    .empty {{ color: #53647b; font-style: italic; }}
    .copy-controls {{ display: flex; align-items: center; gap: .75rem; margin: .75rem 0; }}
    .copy-button {{ padding: .45rem .7rem; border: 1px solid #9aa8bb; border-radius: .35rem; background: #f3f6fa; color: inherit; cursor: pointer; }}
    .copy-button:disabled {{ cursor: wait; opacity: .7; }}
    .copy-status {{ color: #53647b; font-size: .9rem; }}
    .copy-buffer {{ position: fixed; left: -9999px; top: 0; }}
    footer {{ color: #53647b; margin: 2rem 0; font-size: .9rem; }}
    @media print {{ body {{ background: white; }} main {{ margin: 0; max-width: none; }} header, section {{ break-inside: avoid; }} }}
  </style>
</head>
<body>
<header>
  <h1>{escape(results.pack_title)}</h1>
  <p>Assessment pack version {escape(results.pack_version)}</p>
</header>
<main>
  {_render_copy_controls("all-markdown", all_markdown, "Copy All Markdown")}
  <section>
    <h2>Executive Summary</h2>
    {_render_copy_controls("executive-summary-markdown", summary_markdown)}
    {executive_summary_html}
  </section>
  <section>
    <h2>Commentary</h2>
    {_render_copy_controls("commentary-markdown", commentary_markdown)}
    {commentary_html}
  </section>
  <section>
    <h2>Remediation</h2>
    {_render_copy_controls("remediation-markdown", remediation_markdown)}
    {remediation_html}
    <h3>References</h3>
    {references_html}
  </section>
  <footer>Generated by Audit Companion. This report works offline and loads no external resources.</footer>
</main>
<script>
  async function copyMarkdown(text) {{
    if (navigator.clipboard?.writeText && window.isSecureContext) {{
      await navigator.clipboard.writeText(text);
      return;
    }}
    const buffer = document.createElement("textarea");
    buffer.value = text;
    buffer.className = "copy-buffer";
    document.body.append(buffer);
    buffer.select();
    let copied;
    try {{
      copied = document.execCommand("copy");
    }} finally {{
      buffer.remove();
    }}
    if (!copied) throw new Error("Clipboard access is unavailable.");
  }}

  for (const button of document.querySelectorAll(".copy-button")) {{
    button.addEventListener("click", async () => {{
      const status = button.nextElementSibling;
      button.disabled = true;
      status.textContent = "Copying...";
      try {{
        const source = document.getElementById(button.dataset.copy);
        await copyMarkdown(source.textContent);
        status.textContent = "Copied Markdown to clipboard.";
      }} catch {{
        status.textContent = "Copy failed. Select and copy the text manually.";
      }} finally {{
        button.disabled = false;
      }}
    }});
  }}
</script>
</body>
</html>
"""


def _executive_summary_paragraphs(
    results: AssessmentResults,
    summary_template: str | None,
    findings_intro: str | None,
    conclusion: str | None,
    report_groups: Mapping[str, ReportGroup],
    positive_summary_intro: str | None = None,
    positive_summary_conclusion: str | None = None,
    assessment_complete: bool = False,
) -> list[str]:
    template_values = _report_template_values(results)
    paragraphs: list[str] = []
    if summary_template:
        paragraphs.extend(
            _split_paragraphs(summary_template.format_map(template_values))
        )
    else:
        paragraphs.append(
            f"The {results.pack_title.lower()} reviewed security controls in "
            f"{template_values['client_name']}'s environment."
        )

    unknown_count = sum(response.answer == "unknown" for response in results.responses)
    positive_groups = _summary_groups(results.positive_observations)
    positive_summaries = _positive_summary_phrases(results)
    if positive_summary_intro and positive_summaries:
        positive_values = {
            **template_values,
            "strengths": _human_list(positive_summaries),
        }
        paragraphs.extend(
            _split_paragraphs(
                positive_summary_intro.format_map(positive_values)
            )
        )
    if results.findings:
        grouped_findings = _commentary_groups(results.findings)
        if report_groups and all(
            group in report_groups for group in grouped_findings
        ):
            areas = _human_list(
                [
                    report_groups[group].executive_summary_label
                    for group in grouped_findings
                ]
            )
            priorities = _human_list(
                [
                    report_groups[group].executive_summary_priority
                    for group in grouped_findings
                ]
            )
            group_values = {
                **template_values,
                "areas": areas,
                "priorities": priorities,
            }
            if findings_intro:
                paragraphs.extend(
                    _split_paragraphs(findings_intro.format_map(group_values))
                )
            if conclusion:
                paragraphs.extend(
                    _split_paragraphs(conclusion.format_map(group_values))
                )
        else:
            groups = _summary_groups(results.findings)
            titles = _summary_titles(results.findings)
            if groups:
                paragraphs.append(
                    f"The assessment identified opportunities for improvement in "
                    f"{_human_list(groups)}."
                )
            if titles:
                paragraphs.append(
                    f"Key observations included {_human_list(titles)}."
                )
            if not groups and not titles:
                paragraphs.append(
                    "The assessment identified control gaps that require remediation."
                )
            paragraphs.append(
                "Addressing these observations would strengthen assurance over the "
                "assessed environment and support ongoing security oversight."
            )
        if positive_groups:
            if not (positive_summary_intro and positive_summaries):
                paragraphs.append(
                    f"Positive controls were also observed in {_human_list(positive_groups)}."
                )
    else:
        paragraphs.append(
            "No non-compliant responses were recorded among the controls assessed."
        )
        if (
            positive_summary_conclusion
            and positive_summaries
            and not unknown_count
            and assessment_complete
        ):
            paragraphs.extend(
                _split_paragraphs(
                    positive_summary_conclusion.format_map(template_values)
                )
            )
        elif positive_groups and not (positive_summary_intro and positive_summaries):
            paragraphs.append(
                f"The review confirmed positive controls in {_human_list(positive_groups)}."
            )
    if unknown_count:
        paragraphs.append(
            "Some controls could not be verified and require further evidence "
            "before the assessment can be considered conclusive."
        )
    return paragraphs


def _assessment_is_complete(
    results: AssessmentResults,
    pack: AssessmentPack,
) -> bool:
    if any(
        field.required
        and applies(field.applies_when, results.context)
        and field.id not in results.context
        for field in pack.context
    ):
        return False
    expected = {
        (question.id, tuple(sorted(scope.items())))
        for question, scope in expand_question_scopes(pack.questions, results.context)
    }
    recorded = {
        (response.question_id, tuple(sorted(response.scope.items())))
        for response in results.responses
    }
    return bool(expected) and expected.issubset(recorded)


def _positive_summary_phrases(results: AssessmentResults) -> list[str]:
    values = _report_template_values(results)
    observations = sorted(
        enumerate(results.positive_observations),
        key=lambda item: (
            item[1].get("positive_summary_priority")
            if isinstance(item[1].get("positive_summary_priority"), int)
            else 1000,
            item[0],
        ),
    )
    phrases = []
    for _, observation in observations:
        template = observation.get("positive_summary_commentary")
        if not template:
            continue
        scoped_values = dict(values)
        scope = observation.get("scope")
        if isinstance(scope, Mapping):
            scoped_values.update(
                {str(field): str(value) for field, value in scope.items()}
            )
        phrase = " ".join(str(template).format_map(scoped_values).split())
        if phrase and phrase not in phrases:
            phrases.append(phrase)
    return phrases[:6]


def _report_template_values(results: AssessmentResults) -> dict[str, str]:
    values = {
        field_id: _summary_value(value)
        for field_id, value in results.context.items()
    }
    client_name = next(
        (
            str(value).strip()
            for field_id, value in results.context.items()
            if field_id.casefold()
            in {"client_name", "organization", "organisation", "tenant_name"}
            and value
        ),
        "the assessed organisation",
    )
    values["client_name"] = client_name
    for field_id, default in {
        "platforms": "mobile",
        "mdm_vendor": "the selected MDM solution",
        "remote_access_solution": "the selected remote access solution",
        "voip_solution": "the selected VoIP platform",
        "device_type": "assessed component",
    }.items():
        values[field_id] = values.get(field_id) or default
    return values


def _format_report_text(
    template: str | None,
    results: AssessmentResults,
) -> str:
    return template.format_map(_report_template_values(results)) if template else ""


def _format_findings_intro(
    template: str | None,
    results: AssessmentResults,
    report_groups: Mapping[str, ReportGroup],
) -> str:
    if not template or not results.findings:
        return ""
    areas = _finding_area_labels(results.findings, report_groups)
    if not areas:
        return ""
    values = {**_report_template_values(results), "areas": _human_list(areas)}
    return template.format_map(values)


def _finding_area_labels(
    findings: list[dict[str, object]],
    report_groups: Mapping[str, ReportGroup],
) -> list[str]:
    groups = []
    for finding in findings:
        group = str(
            finding.get("commentary_group")
            or finding.get("theme")
            or finding.get("section")
            or ""
        ).strip()
        if group and group not in groups:
            groups.append(group)
    return [
        report_groups[group].executive_summary_label
        if group in report_groups
        else group
        for group in groups
    ]


def _split_paragraphs(text: str) -> list[str]:
    return [
        " ".join(paragraph.split())
        for paragraph in re.split(r"\n\s*\n", text.strip())
        if paragraph.strip()
    ]


def _strip_bold_markup(text: str) -> str:
    return re.sub(r"\*\*(.+?)\*\*", r"\1", text)


def _render_inline_text(text: str) -> str:
    return escape(_strip_bold_markup(text))


def _summary_value(value: object) -> str:
    if isinstance(value, list):
        return _human_list([str(item) for item in value]) if value else ""
    return str(value)


def _summary_groups(observations: list[dict[str, object]]) -> list[str]:
    groups = []
    for observation in observations:
        group = str(
            observation.get("commentary_group")
            or observation.get("theme")
            or observation.get("section")
            or ""
        ).strip()
        if group and group not in groups:
            groups.append(group)
    return groups[:3]


def _summary_titles(observations: list[dict[str, object]]) -> list[str]:
    titles = []
    for observation in observations:
        title = str(observation.get("title") or "").strip()
        if title and title not in titles:
            titles.append(title)
    return titles[:3]


def _human_list(items: list[str]) -> str:
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{', '.join(items[:-1])}, and {items[-1]}"


def _configuration_entries(
    results: AssessmentResults,
    labels: Mapping[str, str],
) -> list[tuple[str, str, str]]:
    entries = []
    for field_id, value in results.context.items():
        label = labels.get(field_id) or field_id.replace("_", " ").capitalize()
        note = " ".join(results.context_notes.get(field_id, "").split())
        entries.append((label, _summary_value(value), note))
    return entries


def _render_configuration_row(
    item: str,
    setting: str,
    note: str,
    include_note: bool,
) -> str:
    note_cell = f"<td>{escape(note)}</td>" if include_note else ""
    return (
        "<tr>"
        f"<th scope=\"row\">{escape(item)}</th>"
        f"<td>{escape(setting)}</td>"
        f"{note_cell}"
        "</tr>"
    )


def _markdown_table(
    headers: tuple[str, ...],
    rows: list[tuple[str, ...]],
) -> str:
    def cell(value: str) -> str:
        return value.replace("|", r"\|").replace("\n", "<br>").strip()

    header_line = "| " + " | ".join(map(cell, headers)) + " |"
    separator_line = "| " + " | ".join("---" for _ in headers) + " |"
    row_lines = [
        "| " + " | ".join(map(cell, row)) + " |"
        for row in rows
    ]
    return "\n".join((header_line, separator_line, *row_lines))


def _render_commentary(
    findings: list[dict[str, object]],
    positive_observations: list[dict[str, object]],
    intro: str,
    findings_intro: str,
    configuration_intro: str,
    configuration_html: str,
    report_groups: Mapping[str, ReportGroup],
    report_scope_field: str | None = None,
    report_scope_values: object = None,
) -> str:
    sections = []
    if intro:
        sections.extend(
            f"<p>{_render_inline_text(paragraph)}</p>"
            for paragraph in _split_paragraphs(intro)
        )
    if findings_intro:
        sections.extend(
            f"<p>{_render_inline_text(paragraph)}</p>"
            for paragraph in _split_paragraphs(findings_intro)
        )
    if configuration_intro:
        sections.extend(
            f"<p>{_render_inline_text(paragraph)}</p>"
            for paragraph in _split_paragraphs(configuration_intro)
        )
    if configuration_html:
        sections.append(configuration_html)
    if report_scope_field:
        sections.extend(
            _render_scoped_commentary(
                findings,
                positive_observations,
                report_groups,
                report_scope_field,
                report_scope_values,
            )
        )
        return "\n".join(sections)

    groups = _commentary_groups(findings)
    for group, observations in groups.items():
        report_group = report_groups.get(group)
        group_sections = [f"<h3>{escape(group)}</h3>"]
        if report_group:
            group_sections.extend(
                f"<p>{_render_inline_text(paragraph)}</p>"
                for paragraph in _split_paragraphs(report_group.commentary_intro)
            )
            group_sections.extend(
                f"<p>{_render_inline_text(paragraph)}</p>"
                for paragraph in _commentary_paragraphs(observations)
            )
            group_sections.extend(
                f"<p>{_render_inline_text(paragraph)}</p>"
                for paragraph in _split_paragraphs(
                    report_group.commentary_conclusion
                )
            )
        else:
            for observation in observations:
                title = str(observation.get("title", "")).strip()
                title_html = (
                    f"{escape(_strip_bold_markup(title))}. " if title else ""
                )
                group_sections.append(
                    '<article class="observation">'
                    f"<p>{title_html}{escape(_commentary_narrative(observation))}</p>"
                    "</article>"
                )
        sections.extend(group_sections)

    positive_groups = _positive_commentary_groups(positive_observations)
    positive_without_commentary = [
        observation
        for observation in positive_observations
        if not observation.get("positive_commentary")
    ]
    positive_narratives = _positive_narratives(positive_without_commentary)
    if positive_groups or positive_narratives:
        positive_sections = ["<h3>Positive Security Controls</h3>"]
        for group, observations in positive_groups.items():
            narrative = " ".join(
                " ".join(str(item.get("positive_commentary") or "").split())
                for item in observations
                if item.get("positive_commentary")
            )
            if narrative:
                positive_sections.append(
                    "<p>"
                    f"{escape(group)}. "
                    f"{_render_inline_text(narrative)}"
                    "</p>"
                )
        if positive_narratives:
            positive_items = "".join(
                f"<li>{escape(narrative)}</li>" for narrative in positive_narratives
            )
            positive_sections.append(f"<ul>{positive_items}</ul>")
        sections.extend(positive_sections)
    if not groups and not positive_narratives:
        if not positive_groups:
            sections.append(
                '<p class="empty">No control observations were recorded.</p>'
            )
    return "\n".join(sections)


def _render_scoped_commentary(
    findings: list[dict[str, object]],
    positive_observations: list[dict[str, object]],
    report_groups: Mapping[str, ReportGroup],
    scope_field: str,
    scope_values: object,
) -> list[str]:
    scoped_observations = [*findings, *positive_observations]
    if isinstance(scope_values, list):
        rendered_scopes = [str(value) for value in scope_values]
    elif scope_values:
        rendered_scopes = [str(scope_values)]
    else:
        rendered_scopes = []
    for observation in scoped_observations:
        scope = observation.get("scope")
        if not isinstance(scope, Mapping):
            continue
        value = scope.get(scope_field)
        if value and str(value) not in rendered_scopes:
            rendered_scopes.append(str(value))
    if not rendered_scopes:
        rendered_scopes = ["General"]

    sections = []
    for scope_value in rendered_scopes:
        scope_findings = [
            item
            for item in findings
            if isinstance(item.get("scope"), Mapping)
            and str(item.get("scope", {}).get(scope_field, "")) == scope_value
        ]
        scope_positives = [
            item
            for item in positive_observations
            if isinstance(item.get("scope"), Mapping)
            and str(item.get("scope", {}).get(scope_field, "")) == scope_value
        ]
        sections.append(f"<h3>{escape(scope_value)} Devices</h3>")
        for group, observations in _commentary_groups(scope_findings).items():
            report_group = report_groups.get(group)
            label = (
                report_group.commentary_label
                if report_group and report_group.commentary_label
                else group
            )
            paragraphs = []
            if report_group:
                paragraphs.extend(_split_paragraphs(report_group.commentary_intro))
            paragraphs.extend(_commentary_paragraphs(observations))
            if report_group:
                paragraphs.extend(
                    _split_paragraphs(report_group.commentary_conclusion)
                )
            if paragraphs:
                sections.append(
                    f"<p>{escape(label)}. "
                    f"{_render_inline_text(paragraphs[0])}</p>"
                )
                sections.extend(
                    f"<p>{_render_inline_text(paragraph)}</p>"
                    for paragraph in paragraphs[1:]
                )
        positive_narratives = _positive_narratives(scope_positives)
        if positive_narratives:
            items = "".join(
                f"<li>{escape(narrative)}</li>"
                for narrative in positive_narratives
            )
            sections.append(
                "<p>Positive Observations</p>"
                f"<ul>{items}</ul>"
            )
        if not scope_findings and not positive_narratives:
            sections.append(
                '<p class="empty">No control observations were recorded.</p>'
            )
    return sections


def _positive_commentary_groups(
    observations: list[dict[str, object]],
) -> dict[str, list[dict[str, object]]]:
    groups: dict[str, list[dict[str, object]]] = {}
    for observation in observations:
        if not observation.get("positive_commentary"):
            continue
        group = str(
            observation.get("commentary_group")
            or observation.get("theme")
            or observation.get("section")
            or "Assessment findings"
        )
        groups.setdefault(group, []).append(observation)
    return groups


def _commentary_groups(
    findings: list[dict[str, object]],
) -> dict[str, list[dict[str, object]]]:
    groups: dict[str, list[dict[str, object]]] = {}
    for finding in findings:
        if not _commentary_narrative(finding):
            continue
        group = str(
            finding.get("commentary_group")
            or finding.get("theme")
            or finding.get("section")
            or "Assessment findings"
        )
        groups.setdefault(group, []).append(finding)
    return groups


def _commentary_narrative(observation: dict[str, object]) -> str:
    description = " ".join(str(observation.get("description") or "").split())
    commentary = " ".join(str(observation.get("commentary") or "").split())
    if not description:
        narrative = commentary
    elif (
        not commentary
        or description.rstrip(".!?").casefold() in commentary.casefold()
    ):
        narrative = commentary or description
    else:
        narrative = f"{description} {commentary}"
    if narrative and not narrative.endswith((".", "!", "?")):
        narrative += "."
    return narrative


def _commentary_paragraphs(
    observations: list[dict[str, object]],
) -> list[str]:
    grouped: dict[tuple[str, object], list[str]] = {}
    for index, observation in enumerate(observations):
        paragraph_id = observation.get("commentary_paragraph")
        if isinstance(paragraph_id, int):
            key = ("paragraph", paragraph_id)
        else:
            key = ("observation", index)
        grouped.setdefault(key, []).append(_commentary_narrative(observation))
    keys = list(grouped)
    if all(key[0] == "paragraph" for key in keys):
        keys.sort(key=lambda key: int(key[1]))
    return [" ".join(grouped[key]) for key in keys]


def _commentary_markdown(
    findings: list[dict[str, object]],
    positive_observations: list[dict[str, object]],
    intro: str,
    findings_intro: str,
    configuration_intro: str,
    configuration_headers: tuple[str, ...],
    configuration: list[tuple[str, str, str]],
    report_groups: Mapping[str, ReportGroup],
    report_scope_field: str | None = None,
    report_scope_values: object = None,
) -> str:
    lines = []
    if intro:
        lines.extend(("\n\n".join(_split_paragraphs(intro)), ""))
    if findings_intro:
        lines.extend(("\n\n".join(_split_paragraphs(findings_intro)), ""))
    if configuration_intro:
        lines.extend(("\n\n".join(_split_paragraphs(configuration_intro)), ""))
    if configuration:
        lines.extend(
            (
                _markdown_table(
                    configuration_headers,
                    [
                        (item, setting, note)
                        if len(configuration_headers) == 3
                        else (item, setting)
                        for item, setting, note in configuration
                    ],
                ),
                "",
            )
        )
    groups = _commentary_groups(findings)
    if report_scope_field:
        lines.extend(
            _scoped_commentary_markdown(
                findings,
                positive_observations,
                report_groups,
                report_scope_field,
                report_scope_values,
            )
        )
        return _markdown_section("Commentary", "\n".join(lines).strip())

    for group, observations in groups.items():
        lines.append(f"### {group}")
        report_group = report_groups.get(group)
        if report_group:
            paragraphs = [
                *_split_paragraphs(report_group.commentary_intro),
                *_commentary_paragraphs(observations),
                *_split_paragraphs(report_group.commentary_conclusion),
            ]
            for paragraph in paragraphs:
                lines.extend((paragraph, ""))
        else:
            for observation in observations:
                title = str(observation.get("title", "")).strip()
                if title:
                    lines.append(
                        f"{_strip_bold_markup(title)}. "
                        f"{_commentary_narrative(observation)}"
                    )
                else:
                    lines.append(_commentary_narrative(observation))
                lines.append("")
    positive_groups = _positive_commentary_groups(positive_observations)
    positive_without_commentary = [
        observation
        for observation in positive_observations
        if not observation.get("positive_commentary")
    ]
    positive_narratives = _positive_narratives(positive_without_commentary)
    if positive_groups or positive_narratives:
        lines.append("### Positive Security Controls")
        for group, observations in positive_groups.items():
            narrative = " ".join(
                " ".join(str(item.get("positive_commentary") or "").split())
                for item in observations
                if item.get("positive_commentary")
            )
            if narrative:
                lines.extend((f"{group}. {narrative}", ""))
        lines.extend(f"- {narrative}" for narrative in positive_narratives)
        lines.append("")
    if not groups and not positive_narratives and not positive_groups:
        lines.append("No control observations were recorded.")
    body = "\n".join(lines).strip()
    return _markdown_section("Commentary", body)


def _scoped_commentary_markdown(
    findings: list[dict[str, object]],
    positive_observations: list[dict[str, object]],
    report_groups: Mapping[str, ReportGroup],
    scope_field: str,
    scope_values: object,
) -> list[str]:
    observations = [*findings, *positive_observations]
    if isinstance(scope_values, list):
        rendered_scopes = [str(value) for value in scope_values]
    elif scope_values:
        rendered_scopes = [str(scope_values)]
    else:
        rendered_scopes = []
    for observation in observations:
        scope = observation.get("scope")
        if not isinstance(scope, Mapping):
            continue
        value = scope.get(scope_field)
        if value and str(value) not in rendered_scopes:
            rendered_scopes.append(str(value))
    if not rendered_scopes:
        rendered_scopes = ["General"]

    lines = []
    for scope_value in rendered_scopes:
        scope_findings = [
            item
            for item in findings
            if isinstance(item.get("scope"), Mapping)
            and str(item.get("scope", {}).get(scope_field, "")) == scope_value
        ]
        scope_positives = [
            item
            for item in positive_observations
            if isinstance(item.get("scope"), Mapping)
            and str(item.get("scope", {}).get(scope_field, "")) == scope_value
        ]
        lines.extend((f"### {scope_value} Devices", ""))
        for group, group_findings in _commentary_groups(scope_findings).items():
            report_group = report_groups.get(group)
            label = (
                report_group.commentary_label
                if report_group and report_group.commentary_label
                else group
            )
            paragraphs = []
            if report_group:
                paragraphs.extend(_split_paragraphs(report_group.commentary_intro))
            paragraphs.extend(_commentary_paragraphs(group_findings))
            if report_group:
                paragraphs.extend(
                    _split_paragraphs(report_group.commentary_conclusion)
                )
            if paragraphs:
                lines.extend((f"{label}. {paragraphs[0]}", ""))
                for paragraph in paragraphs[1:]:
                    lines.extend((paragraph, ""))
        positive_narratives = _positive_narratives(scope_positives)
        if positive_narratives:
            lines.extend(
                (
                    "Positive Observations",
                    "",
                    *[f"- {narrative}" for narrative in positive_narratives],
                    "",
                )
            )
        if not scope_findings and not positive_narratives:
            lines.extend(("No control observations were recorded.", ""))
    return lines


def _positive_narratives(observations: list[dict[str, object]]) -> list[str]:
    narratives = []
    for observation in observations:
        narrative = _commentary_narrative(observation)
        if narrative and narrative not in narratives:
            narratives.append(narrative)
    return narratives


def _remediation_actions(
    findings: list[dict[str, object]],
    maintenance_recommendations: list[str] | None = None,
) -> list[str]:
    actions = []
    for finding in findings:
        solution = finding.get("solution")
        if not solution:
            continue
        action = " ".join(str(solution).split())
        if action and action not in actions:
            actions.append(action)
    for recommendation in maintenance_recommendations or []:
        action = " ".join(recommendation.split())
        if action and action not in actions:
            actions.append(action)
    return actions


def _render_remediation(
    findings: list[dict[str, object]],
    intro: str | None,
    maintenance_recommendations: list[str] | None = None,
) -> str:
    actions = _remediation_actions(findings, maintenance_recommendations)
    if not actions:
        return (
            '<p class="empty">No corrective actions were identified for the '
            "assessed controls.</p>"
        )
    items = "".join(f"<li>{escape(action)}</li>" for action in actions)
    rendered_intro = (
        f"<p>{_render_inline_text(intro)}</p>"
        if intro
        else (
            "<p>The following actions address the identified observations and "
            "support continued security assurance:</p>"
        )
    )
    return (
        f"{rendered_intro}<ul>{items}</ul>"
    )


def _remediation_markdown(
    findings: list[dict[str, object]],
    intro: str | None,
    maintenance_recommendations: list[str] | None = None,
) -> str:
    actions = _remediation_actions(findings, maintenance_recommendations)
    if actions:
        body = (
            (intro or (
                "The following actions address the identified observations and "
                "support continued security assurance:"
            ))
            + "\n\n"
            + "\n".join(f"- {action}" for action in actions)
        )
    else:
        body = "No corrective actions were identified for the assessed controls."
    return _markdown_section("Remediation", body)


def _report_references(results: AssessmentResults) -> list[str]:
    references = []
    for observation in [*results.findings, *results.positive_observations]:
        values = observation.get("references")
        if not isinstance(values, list):
            continue
        for value in values:
            reference = str(value).strip()
            if reference and reference not in references:
                references.append(reference)
    return references


def _render_references(references: list[str]) -> str:
    if not references:
        return '<p class="empty">No references were recorded.</p>'
    items = "".join(
        f"<li>{_render_reference(reference)}</li>" for reference in references
    )
    return f"<ul>{items}</ul>"


def _references_markdown(references: list[str]) -> str:
    body = (
        "\n".join(f"- [{reference}]({reference})" for reference in references)
        if references
        else "No references were recorded."
    )
    return f"### References\n\n{_strip_bold_markup(body)}"


def _markdown_section(title: str, body: str) -> str:
    return f"## {title}\n\n{_strip_bold_markup(body)}"


def _render_copy_controls(
    source_id: str,
    markdown: str,
    label: str = "Copy Markdown",
) -> str:
    return (
        '<div class="copy-controls">'
        f'<button type="button" class="copy-button" data-copy="{escape(source_id, quote=True)}">'
        f"{escape(label)}</button>"
        '<span class="copy-status" role="status" aria-live="polite"></span>'
        "</div>"
        f'<pre id="{escape(source_id, quote=True)}" hidden>{escape(markdown)}</pre>'
    )


def _render_table(headers: tuple[str, ...], rows: list[str]) -> str:
    if not rows:
        return '<p class="empty">No entries recorded.</p>'
    header_html = "".join(f"<th>{escape(header)}</th>" for header in headers)
    return (
        f"<table><thead><tr>{header_html}</tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )


def _render_reference(reference: str) -> str:
    escaped_reference = escape(reference)
    parsed = urlparse(reference)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return (
            f'<a href="{escape(reference, quote=True)}" '
            f'rel="noopener noreferrer">{escaped_reference}</a>'
        )
    return escaped_reference
