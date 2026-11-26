"""Common JSON, Markdown, and HTML assessment exports."""

import json
from html import escape
from pathlib import Path
from urllib.parse import urlparse

from audit_companion.models import AssessmentResults


def export_results(
    results: AssessmentResults,
    output_dir: str | Path,
    include_json: bool = True,
) -> tuple[Path | None, Path, Path]:
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    json_path = destination / f"{results.pack_id}-findings.json" if include_json else None
    markdown_path = destination / f"{results.pack_id}-report.md"
    html_path = destination / f"{results.pack_id}-report.html"

    if json_path:
        json_path.write_text(
            results.model_dump_json(indent=2) + "\n",
            encoding="utf-8",
        )
    markdown_path.write_text(_render_markdown(results), encoding="utf-8")
    html_path.write_text(_render_html(results), encoding="utf-8")
    return json_path, markdown_path, html_path


def _render_markdown(results: AssessmentResults) -> str:
    lines = [
        f"# {results.pack_title}",
        "",
        f"Pack version: {results.pack_version}",
        "",
        "## Assessment context",
        "",
    ]
    for field_id, value in results.context.items():
        lines.append(f"- **{field_id}:** {value}")
        note = results.context_notes.get(field_id)
        if note:
            lines.append(f"  - Notes: {note}")

    lines.extend(["", "## Summary", ""])
    lines.append(f"- Findings: {len(results.findings)}")
    lines.append(f"- Positive observations: {len(results.positive_observations)}")
    lines.append(
        f"- Unknown / not applicable: "
        f"{sum(response.answer in ('unknown', 'not_applicable') for response in results.responses)}"
    )

    for heading, items in (
        ("Findings", results.findings),
        ("Positive observations", results.positive_observations),
    ):
        lines.extend(["", f"## {heading}", ""])
        if not items:
            lines.append("None recorded.")
            continue
        for item in items:
            lines.append(f"### {item['title']}")
            lines.append("")
            if item.get("scope"):
                lines.append(
                    "Scope: "
                    + ", ".join(
                        f"{field_id}={value}"
                        for field_id, value in item["scope"].items()
                    )
                )
                lines.append("")
            if item.get("section"):
                lines.append(f"Section: {item['section']}")
                lines.append("")
            lines.append(str(item["description"]))
            lines.append("")
            lines.append(f"Expected value: {item['expected_value']}")
            if heading == "Findings" and item.get("solution"):
                lines.extend(["", f"Recommended action: {item['solution']}"])
            if item.get("notes"):
                lines.extend(["", f"Assessor notes: {item['notes']}"])
            if item.get("references"):
                lines.extend(["", "References:"])
                lines.extend(f"- {reference}" for reference in item["references"])
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


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
    :root {{ color-scheme: light; --ink: #17212b; --muted: #596773; --line: #d7dee5; --accent: #145a72; }}
    body {{ margin: 0; background: #f3f6f8; color: var(--ink); font: 16px/1.55 Segoe UI, sans-serif; }}
    main {{ max-width: 1050px; margin: 2rem auto; padding: 0 1rem 2rem; }}
    header, section {{ background: white; border: 1px solid var(--line); border-radius: 8px; margin-bottom: 1rem; padding: 1.25rem; }}
    h1, h2, h3 {{ line-height: 1.2; }}
    h1 {{ color: var(--accent); margin: 0 0 .25rem; }}
    h2 {{ border-bottom: 1px solid var(--line); padding-bottom: .5rem; }}
    .muted {{ color: var(--muted); }}
    .summary {{ display: flex; flex-wrap: wrap; gap: .75rem; }}
    .metric {{ background: #eef4f6; border-radius: 6px; min-width: 150px; padding: .75rem; }}
    .metric strong {{ display: block; font-size: 1.5rem; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border-bottom: 1px solid var(--line); padding: .6rem; text-align: left; vertical-align: top; }}
    th {{ background: #f6f8f9; }}
    .observation {{ border-left: 4px solid var(--accent); margin: 1rem 0; padding: .25rem 1rem; }}
    .empty {{ color: var(--muted); font-style: italic; }}
    @media print {{ body {{ background: white; }} main {{ margin: 0; max-width: none; }} header, section {{ break-inside: avoid; }} }}
  </style>
</head>
<body>
<main>
  <header>
    <h1>{escape(results.pack_title)}</h1>
    <p class="muted">Assessment pack version {escape(results.pack_version)}</p>
    <div class="summary">
      <div class="metric"><strong>{len(results.findings)}</strong>Findings</div>
      <div class="metric"><strong>{len(results.positive_observations)}</strong>Positive observations</div>
      <div class="metric"><strong>{len(results.responses)}</strong>Responses</div>
    </div>
  </header>
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
</main>
</body>
</html>
"""


def _render_html_observations(
    observations: list[dict[str, object]],
    label: str,
) -> str:
    if not observations:
        return f'<p class="empty">No {escape(label)}s recorded.</p>'

    rendered = []
    for observation in observations:
        scope = observation.get("scope", {})
        scope_text = (
            ", ".join(f"{field_id}={value}" for field_id, value in scope.items())
            if isinstance(scope, dict)
            else ""
        )
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
        section = observation.get("section")
        if section:
            section_html = f'<p class="muted">{escape(str(section))}</p>'
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
