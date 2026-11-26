"""Common JSON and HTML assessment exports."""

import json
from collections.abc import Mapping
from html import escape
from pathlib import Path
from urllib.parse import urlparse

from audit_companion.models import AssessmentResults


def export_results(
    results: AssessmentResults,
    output_dir: str | Path,
    include_json: bool = True,
    executive_summary: str | None = None,
    commentary_intro: str | None = None,
    context_labels: Mapping[str, str] | None = None,
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
    html_path.write_text(
        _render_html(results, executive_summary, commentary_intro, context_labels),
        encoding="utf-8",
    )
    return json_path, html_path


def _render_html(
    results: AssessmentResults,
    executive_summary: str | None = None,
    commentary_intro: str | None = None,
    context_labels: Mapping[str, str] | None = None,
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
        configuration_html = (
            "<h3>Configuration Summary</h3>"
            + _render_table(configuration_headers, configuration_rows)
        )

    summary_paragraphs = _executive_summary_paragraphs(results, executive_summary)
    executive_summary_html = "\n".join(
        f"<p>{escape(paragraph)}</p>" for paragraph in summary_paragraphs
    )
    rendered_commentary_intro = _format_report_text(commentary_intro, results)
    commentary_html = _render_commentary(
        results.findings,
        results.positive_observations,
        rendered_commentary_intro,
        configuration_html,
    )
    remediation_html = _render_remediation(results.findings)
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
        configuration_headers,
        configuration,
    )
    remediation_markdown = _remediation_markdown(results.findings)
    references_markdown = _references_markdown(references)
    all_markdown = "\n\n".join(
        (
            summary_markdown,
            commentary_markdown,
            remediation_markdown,
            references_markdown,
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
    h1, h2, h3 {{ line-height: 1.2; }}
    h2 {{ border-bottom: 1px solid #dce3ed; padding-bottom: .5rem; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #dce3ed; padding: .6rem; text-align: left; vertical-align: top; }}
    th {{ background: #f3f6fa; }}
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
  </section>
  <section>
    <h2>References</h2>
    {_render_copy_controls("references-markdown", references_markdown)}
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
) -> list[str]:
    template_values = _report_template_values(results)
    paragraphs = []
    if summary_template:
        paragraphs.append(summary_template.format_map(template_values))
    else:
        paragraphs.append(
            f"The {results.pack_title.lower()} reviewed security controls in "
            f"{template_values['client_name']}'s environment."
        )

    unknown_count = sum(response.answer == "unknown" for response in results.responses)
    positive_groups = _summary_groups(results.positive_observations)
    if results.findings:
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
        if positive_groups:
            paragraphs.append(
                f"Positive controls were also observed in {_human_list(positive_groups)}."
            )
        paragraphs.append(
            "Addressing these observations would strengthen assurance over the "
            "assessed environment and support ongoing security oversight."
        )
    else:
        paragraphs.append(
            "No non-compliant responses were recorded among the controls assessed."
        )
        if positive_groups:
            paragraphs.append(
                f"The review confirmed positive controls in {_human_list(positive_groups)}."
            )
    if unknown_count:
        paragraphs.append(
            "Some controls could not be verified and require further evidence "
            "before the assessment can be considered conclusive."
        )
    return paragraphs


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
    configuration_html: str,
) -> str:
    groups = _commentary_groups(findings)
    sections = []
    if intro:
        sections.append(f"<p>{escape(intro)}</p>")
    if configuration_html:
        sections.append(configuration_html)
    for group, observations in groups.items():
        rendered_observations = []
        for observation in observations:
            title = str(observation.get("title", "")).strip()
            title_html = f"<strong>{escape(title)}.</strong> " if title else ""
            rendered_observations.append(
                '<article class="observation">'
                f"<p>{title_html}{escape(_commentary_narrative(observation))}</p>"
                "</article>"
            )
        sections.append(
            f"<h3>{escape(group)}</h3>{''.join(rendered_observations)}"
        )

    positive_narratives = _positive_narratives(positive_observations)
    if positive_narratives:
        positive_items = "".join(
            f"<li>{escape(narrative)}</li>" for narrative in positive_narratives
        )
        sections.append(
            f"<h3>Positive Security Controls</h3><ul>{positive_items}</ul>"
        )
    if not groups and not positive_narratives:
        sections.append(
            '<p class="empty">No control observations were recorded.</p>'
        )
    return "\n".join(sections)


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
    narrative = str(observation.get("commentary") or "").strip()
    if not narrative:
        narrative = str(observation.get("description") or "").strip()
    narrative = " ".join(narrative.split())
    if narrative and not narrative.endswith((".", "!", "?")):
        narrative += "."
    return narrative


def _commentary_markdown(
    findings: list[dict[str, object]],
    positive_observations: list[dict[str, object]],
    intro: str,
    configuration_headers: tuple[str, ...],
    configuration: list[tuple[str, str, str]],
) -> str:
    lines = []
    if intro:
        lines.extend((intro, ""))
    if configuration:
        lines.extend(
            (
                "### Configuration Summary",
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
    for group, observations in groups.items():
        lines.append(f"### {group}")
        for observation in observations:
            title = str(observation.get("title", "")).strip()
            if title:
                lines.append(f"**{title}.** {_commentary_narrative(observation)}")
            else:
                lines.append(_commentary_narrative(observation))
            lines.append("")
    positive_narratives = _positive_narratives(positive_observations)
    if positive_narratives:
        lines.append("### Positive Security Controls")
        lines.extend(f"- {narrative}" for narrative in positive_narratives)
        lines.append("")
    if not groups and not positive_narratives:
        lines.append("No control observations were recorded.")
    body = "\n".join(lines).strip()
    return _markdown_section("Commentary", body)


def _positive_narratives(observations: list[dict[str, object]]) -> list[str]:
    narratives = []
    for observation in observations:
        narrative = _commentary_narrative(observation)
        if narrative and narrative not in narratives:
            narratives.append(narrative)
    return narratives


def _remediation_actions(findings: list[dict[str, object]]) -> list[str]:
    actions = []
    for finding in findings:
        solution = finding.get("solution")
        if not solution:
            continue
        action = " ".join(str(solution).split())
        if action and action not in actions:
            actions.append(action)
    return actions


def _render_remediation(findings: list[dict[str, object]]) -> str:
    actions = _remediation_actions(findings)
    if not actions:
        return (
            '<p class="empty">No corrective actions were identified for the '
            "assessed controls.</p>"
        )
    items = "".join(f"<li>{escape(action)}</li>" for action in actions)
    return (
        "<p>The following actions address the identified observations and "
        "support continued security assurance:</p>"
        f"<ul>{items}</ul>"
    )


def _remediation_markdown(findings: list[dict[str, object]]) -> str:
    actions = _remediation_actions(findings)
    if actions:
        body = (
            "The following actions address the identified observations and "
            "support continued security assurance:\n\n"
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
    return _markdown_section("References", body)


def _markdown_section(title: str, body: str) -> str:
    return f"## {title}\n\n{body}"


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
