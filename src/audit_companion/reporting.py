"""Common JSON and HTML assessment exports."""

import json
from html import escape
from pathlib import Path
from typing import TypedDict
from urllib.parse import urlparse

from audit_companion.models import AssessmentResults


class _RemediationAction(TypedDict):
    solution: str
    controls: list[str]
    scopes: list[str]


def export_results(
    results: AssessmentResults,
    output_dir: str | Path,
    include_json: bool = True,
    executive_summary: str | None = None,
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
        _render_html(results, executive_summary),
        encoding="utf-8",
    )
    return json_path, html_path


def _render_html(
    results: AssessmentResults,
    executive_summary: str | None = None,
) -> str:
    context_rows = []
    for field_id, value in results.context.items():
        rendered_value = (
            ", ".join(map(str, value))
            if isinstance(value, list)
            else str(value)
        )
        context_rows.append(
            "<tr>"
            f"<th scope=\"row\">{escape(field_id)}</th>"
            f"<td>{escape(rendered_value)}</td>"
            f"<td>{escape(results.context_notes.get(field_id, ''))}</td>"
            "</tr>"
        )

    findings_html = _render_html_observations(results.findings, "finding")
    positives_html = _render_html_observations(
        results.positive_observations,
        "positive observation",
    )
    summary_paragraphs = _executive_summary_paragraphs(results, executive_summary)
    executive_summary_html = "\n".join(
        f"<p>{escape(paragraph)}</p>" for paragraph in summary_paragraphs
    )
    commentary_html = _render_commentary(results.findings)
    remediation_html = _render_remediation(results.findings)
    summary_markdown = _markdown_section(
        "Executive Summary",
        "\n\n".join(summary_paragraphs),
    )
    commentary_markdown = _commentary_markdown(results.findings)
    remediation_markdown = _remediation_markdown(results.findings)
    all_markdown = "\n\n".join(
        (summary_markdown, commentary_markdown, remediation_markdown)
    )
    response_rows = []
    for response in results.responses:
        scope = ", ".join(
            f"{field_id}={value}" for field_id, value in response.scope.items()
        )
        response_rows.append(
            "<tr>"
            f"<td>{escape(response.question_id)}</td>"
            f"<td>{escape(response.answer.replace('_', ' ').title())}</td>"
            f"<td>{escape(scope)}</td>"
            f"<td>{escape(response.notes or '')}</td>"
            "</tr>"
        )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(results.pack_title)} - Assessment Report</title>
  <style>
    :root {{ color-scheme: light; font-family: system-ui, sans-serif; color: #172033; background: #f3f6fa; --muted: #53647b; }}
    body {{ margin: 0; }}
    header {{ padding: 2rem max(1rem, calc((100% - 1100px) / 2)); background: #10233f; color: white; }}
    header h1 {{ margin: 0; }}
    main {{ max-width: 1100px; margin: 2rem auto; padding: 0 1rem 2rem; }}
    section {{ background: white; border: 1px solid #dce3ed; border-radius: .6rem; margin-bottom: 1rem; padding: 1.25rem; }}
    h1, h2, h3 {{ line-height: 1.2; }}
    h2 {{ border-bottom: 1px solid #dce3ed; padding-bottom: .5rem; }}
    .muted {{ color: var(--muted); }}
    .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 1rem; }}
    .metric {{ background: #eef2f7; border-radius: .6rem; padding: 1rem; }}
    .metric strong {{ display: block; font-size: 1.6rem; margin-top: .35rem; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #dce3ed; padding: .6rem; text-align: left; vertical-align: top; }}
    th {{ background: #f3f6fa; }}
    .observation, .recommendation {{ border-left: 4px solid #607d9d; margin: 1rem 0; padding: .25rem 1rem; }}
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
  <section class="summary" aria-label="Assessment summary">
    <div class="metric">Findings<strong>{len(results.findings)}</strong></div>
    <div class="metric">Positive observations<strong>{len(results.positive_observations)}</strong></div>
    <div class="metric">Unknown responses<strong>{sum(response.answer == "unknown" for response in results.responses)}</strong></div>
    <div class="metric">Not applicable<strong>{sum(response.answer == "not_applicable" for response in results.responses)}</strong></div>
  </section>
  {_render_copy_controls("all-markdown", all_markdown, "Copy All Markdown")}
  <section>
    <h2>Executive Summary</h2>
    {_render_copy_controls("executive-summary-markdown", summary_markdown)}
    {executive_summary_html}
  </section>
  <section>
    <h2>Technical Commentary</h2>
    {_render_copy_controls("technical-commentary-markdown", commentary_markdown)}
    {commentary_html}
  </section>
  <section>
    <h2>Remediation Guidance</h2>
    {_render_copy_controls("remediation-guidance-markdown", remediation_markdown)}
    {remediation_html}
  </section>
  <section>
    <h2>Assessment context</h2>
    {_render_table(("Context field", "Value", "Notes"), context_rows)}
  </section>
  <section>
    <h2>Findings</h2>
    {findings_html}
  </section>
  <section>
    <h2>Positive observations</h2>
    {positives_html}
  </section>
  <section>
    <h2>Response history</h2>
    {_render_table(("Question", "Answer", "Scope", "Notes"), response_rows)}
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
    paragraphs = []
    if summary_template:
        summary_values = {
            field_id: _summary_value(value)
            for field_id, value in results.context.items()
        }
        summary_values["client_name"] = client_name
        summary_values["platforms"] = summary_values.get("platforms") or "mobile"
        paragraphs.append(
            summary_template.format_map(summary_values)
        )
    else:
        paragraphs.append(
            f"The {results.pack_title.lower()} reviewed security controls in "
            f"{client_name}'s environment."
        )

    unknown_count = sum(response.answer == "unknown" for response in results.responses)
    if results.findings:
        groups = _summary_groups(results.findings)
        titles = _summary_titles(results.findings)
        if groups:
            paragraphs.append(
                f"Control gaps were identified in {_human_list(groups)}."
            )
        if titles:
            paragraphs.append(f"Representative findings include {_human_list(titles)}.")
        if not groups and not titles:
            paragraphs.append(
                "The assessment identified control gaps that require remediation."
            )
        paragraphs.append(
            "Address the identified gaps according to business risk and validate "
            "the changes through a follow-up review."
        )
    else:
        paragraphs.append(
            "No non-compliant controls were identified among the responses with "
            "a conclusive outcome. This point-in-time review does not guarantee "
            "that all security risks are absent."
        )

    positive_groups = _summary_groups(results.positive_observations)
    if positive_groups:
        paragraphs.append(
            f"Positive controls were observed in {_human_list(positive_groups)}."
        )
    if unknown_count:
        paragraphs.append(
            "Some controls could not be verified. Collect further evidence before "
            "treating those areas as compliant or drawing final conclusions."
        )
    return paragraphs


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


def _render_commentary(findings: list[dict[str, object]]) -> str:
    groups = _commentary_groups(findings)
    if not groups:
        return '<p class="empty">No technical commentary was recorded.</p>'

    rendered_groups = []
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
        rendered_groups.append(
            f"<h3>{escape(group)}</h3>{''.join(rendered_observations)}"
        )
    return "\n".join(rendered_groups)


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


def _commentary_markdown(findings: list[dict[str, object]]) -> str:
    lines = []
    for group, observations in _commentary_groups(findings).items():
        lines.append(f"### {group}")
        for observation in observations:
            title = str(observation.get("title", "")).strip()
            if title:
                lines.append(f"**{title}.** {_commentary_narrative(observation)}")
            else:
                lines.append(_commentary_narrative(observation))
            lines.append("")
    body = "\n".join(lines).strip()
    if not body:
        body = "No technical commentary was recorded."
    return _markdown_section("Technical Commentary", body)


def _render_remediation(findings: list[dict[str, object]]) -> str:
    groups = _remediation_groups(findings)
    if not groups:
        return '<p class="empty">No remediation actions were recorded.</p>'

    rendered_groups = []
    for group, group_actions in groups.items():
        rendered_actions = []
        for action in group_actions:
            controls = ", ".join(action["controls"])
            scopes = ", ".join(action["scopes"])
            controls_html = (
                f'<p class="muted">Related controls: {escape(controls)}</p>'
                if controls
                else ""
            )
            scopes_html = (
                f'<p class="muted">Scope: {escape(scopes)}</p>' if scopes else ""
            )
            rendered_actions.append(
                '<article class="recommendation">'
                f"<p>{escape(action['solution'])}</p>"
                f"{controls_html}{scopes_html}"
                "</article>"
            )
        rendered_groups.append(
            f"<h3>{escape(group)}</h3>{''.join(rendered_actions)}"
        )
    return "\n".join(rendered_groups)


def _remediation_groups(
    findings: list[dict[str, object]],
) -> dict[str, list[_RemediationAction]]:
    groups: dict[str, list[_RemediationAction]] = {}
    actions: dict[tuple[str, str], _RemediationAction] = {}
    for finding in findings:
        solution = finding.get("solution")
        if not solution:
            continue
        group = str(
            finding.get("commentary_group")
            or finding.get("theme")
            or finding.get("section")
            or "General"
        )
        action_text = str(solution)
        key = (group, action_text)
        action = actions.get(key)
        if action is None:
            action = {"solution": action_text, "controls": [], "scopes": []}
            actions[key] = action
            groups.setdefault(group, []).append(action)

        title = str(finding.get("title", ""))
        if title and title not in action["controls"]:
            action["controls"].append(title)
        scope = _scope_text(finding.get("scope"))
        if scope and scope not in action["scopes"]:
            action["scopes"].append(scope)
    return groups


def _remediation_markdown(findings: list[dict[str, object]]) -> str:
    lines = []
    for group, group_actions in _remediation_groups(findings).items():
        lines.append(f"### {group}")
        for action in group_actions:
            lines.append(f"- {action['solution']}")
            if action["controls"]:
                lines.append(
                    f"  - Related controls: {', '.join(action['controls'])}"
                )
            if action["scopes"]:
                lines.append(f"  - Scope: {', '.join(action['scopes'])}")
        lines.append("")
    body = "\n".join(lines).strip()
    if not body:
        body = "No remediation actions were recorded."
    return _markdown_section("Remediation Guidance", body)


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


def _scope_text(scope: object) -> str:
    if not isinstance(scope, dict):
        return ""
    return ", ".join(f"{field_id}={value}" for field_id, value in scope.items())


def _render_html_observations(
    observations: list[dict[str, object]],
    label: str,
) -> str:
    if not observations:
        return f'<p class="empty">No {escape(label)}s recorded.</p>'

    rendered = []
    for observation in observations:
        scope_text = _scope_text(observation.get("scope"))
        references = observation.get("references", [])
        references_html = ""
        if isinstance(references, list) and references:
            reference_items = "".join(
                f"<li>{_render_reference(str(reference))}</li>"
                for reference in references
            )
            references_html = (
                f"<p><strong>References</strong></p><ul>{reference_items}</ul>"
            )

        solution_html = ""
        solution = observation.get("solution")
        if solution:
            solution_html = (
                f"<p><strong>Recommended action:</strong> "
                f"{escape(str(solution))}</p>"
            )
        notes_html = ""
        notes = observation.get("notes")
        if notes:
            notes_html = (
                f"<p><strong>Assessor notes:</strong> "
                f"{escape(str(notes))}</p>"
            )
        section_html = ""
        theme = observation.get("theme")
        if theme:
            section_html = f'<p class="muted">Theme: {escape(str(theme))}</p>'
        section = observation.get("section")
        if section:
            section_html += f'<p class="muted">Section: {escape(str(section))}</p>'
        commentary_html = ""
        commentary = observation.get("commentary")
        if commentary:
            commentary_html = f"<p>{escape(str(commentary))}</p>"
        scope_html = (
            f'<p class="muted">Scope: {escape(scope_text)}</p>'
            if scope_text
            else ""
        )

        rendered.append(
            '<article class="observation">'
            f"<h3>{escape(str(observation.get('title', '')))}</h3>"
            f"{section_html}{scope_html}"
            f"<p>{escape(str(observation.get('description', '')))}</p>"
            f"{commentary_html}"
            f"<p><strong>Expected value:</strong> "
            f"{escape(str(observation.get('expected_value', '')))}</p>"
            f"{solution_html}{notes_html}{references_html}"
            "</article>"
        )
    return "\n".join(rendered)


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
