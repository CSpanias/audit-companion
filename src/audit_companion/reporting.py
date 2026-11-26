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
    html_path.write_text(_render_html(results), encoding="utf-8")
    return json_path, html_path


def _render_html(results: AssessmentResults) -> str:
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
    executive_summary_html = _render_executive_summary(results)
    commentary_html = _render_commentary(results.findings)
    remediation_html = _render_remediation(results.findings)
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
  <section>
    <h2>Executive Summary</h2>
    {executive_summary_html}
  </section>
  <section>
    <h2>Technical Commentary</h2>
    {commentary_html}
  </section>
  <section>
    <h2>Remediation Guidance</h2>
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
</body>
</html>
"""


def _render_executive_summary(results: AssessmentResults) -> str:
    response_count = len(results.responses)
    finding_count = len(results.findings)
    unknown_count = sum(response.answer == "unknown" for response in results.responses)
    not_applicable_count = sum(
        response.answer == "not_applicable" for response in results.responses
    )

    paragraphs = []
    if response_count:
        paragraphs.append(
            f"The assessment reviewed {_quantity(response_count, 'control response')}."
        )
    else:
        paragraphs.append("No applicable control responses were recorded.")

    if finding_count:
        paragraphs.append(
            f"The review identified {_quantity(finding_count, 'non-compliant finding')} "
            "requiring remediation."
        )
    else:
        paragraphs.append(
            "No non-compliant controls were identified from the responses recorded."
        )

    if unknown_count:
        subject = (
            "One response was"
            if unknown_count == 1
            else f"{_quantity(unknown_count, 'response').capitalize()} were"
        )
        follow_up_verb = "requires" if unknown_count == 1 else "require"
        paragraphs.append(
            f"{subject} marked unknown and {follow_up_verb} "
            "follow-up before the assessment is conclusive."
        )
    if not_applicable_count:
        subject = (
            "One response was"
            if not_applicable_count == 1
            else f"{_quantity(not_applicable_count, 'response').capitalize()} were"
        )
        paragraphs.append(
            f"{subject} marked not applicable."
        )

    return "\n".join(f"<p>{escape(paragraph)}</p>" for paragraph in paragraphs)


def _quantity(count: int, singular: str) -> str:
    number_words = {
        0: "no",
        1: "one",
        2: "two",
        3: "three",
        4: "four",
        5: "five",
        6: "six",
        7: "seven",
        8: "eight",
        9: "nine",
    }
    number = number_words.get(count, str(count))
    noun = singular if count == 1 else f"{singular}s"
    return f"{number} {noun}"


def _render_commentary(findings: list[dict[str, object]]) -> str:
    groups: dict[str, list[dict[str, object]]] = {}
    for finding in findings:
        commentary = finding.get("commentary")
        if not commentary:
            continue
        group = str(
            finding.get("commentary_group")
            or finding.get("section")
            or "Assessment findings"
        )
        groups.setdefault(group, []).append(finding)

    if not groups:
        return '<p class="empty">No technical commentary was recorded.</p>'

    rendered_groups = []
    for group, observations in groups.items():
        rendered_observations = []
        for observation in observations:
            scope = _scope_text(observation.get("scope"))
            scope_html = (
                f'<p class="muted">Scope: {escape(scope)}</p>' if scope else ""
            )
            rendered_observations.append(
                '<article class="observation">'
                f"<h4>{escape(str(observation.get('title', '')))}</h4>"
                f"{scope_html}"
                f"<p>{escape(str(observation['commentary']))}</p>"
                "</article>"
            )
        rendered_groups.append(
            f"<h3>{escape(group)}</h3>{''.join(rendered_observations)}"
        )
    return "\n".join(rendered_groups)


def _render_remediation(findings: list[dict[str, object]]) -> str:
    groups: dict[str, list[_RemediationAction]] = {}
    actions: dict[tuple[str, str], _RemediationAction] = {}
    for finding in findings:
        solution = finding.get("solution")
        if not solution:
            continue
        group = str(
            finding.get("commentary_group")
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
                f"<p>{escape(str(action['solution']))}</p>"
                f"{controls_html}{scopes_html}"
                "</article>"
            )
        rendered_groups.append(
            f"<h3>{escape(group)}</h3>{''.join(rendered_actions)}"
        )
    return "\n".join(rendered_groups)


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
            references_html = f"<h4>References</h4><ul>{reference_items}</ul>"

        solution_html = ""
        solution = observation.get("solution")
        if solution:
            solution_html = f"<h4>Recommended action</h4><p>{escape(str(solution))}</p>"
        notes_html = ""
        notes = observation.get("notes")
        if notes:
            notes_html = f"<h4>Assessor notes</h4><p>{escape(str(notes))}</p>"
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
