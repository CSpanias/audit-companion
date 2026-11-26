# Audit Companion

A framework for guided, live security assessments, with modular assessment
packs for MDM, remote access, VoIP, and beyond.

Audit Companion is being built from the shared workflow in the
[MDM-Audit](https://github.com/CSpanias/mdm-audit),
[Remote-Access-Audit](https://github.com/CSpanias/remote-access-audit), and
[VoIP-Audit](https://github.com/CSpanias/voip-audit) proof of concepts. The
framework owns the common interview, response, and export behavior; assessment
packs own their context, control content, and applicability rules.

## Current status

The initial core supports validated YAML assessment packs, guided terminal
interviews, conditional context and question selection, and JSON/Markdown
exports, together with a self-contained HTML report. The original assessment
content has not yet been migrated.

## Install for development

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev,docs]"
```

## Run a pack

```powershell
audit-companion validate path\to\assessment.yaml
audit-companion run path\to\assessment.yaml --output-dir .
```

The run command writes `<pack-id>-findings.json`, `<pack-id>-report.md`, and
`<pack-id>-report.html` to the chosen output directory.

Try the included example:

```powershell
audit-companion validate examples\minimal.yaml
audit-companion run examples\minimal.yaml --output-dir output
```

## Assessment pack format

Packs use a common structure while retaining domain-specific content and
selection logic in data:

```yaml
id: example
title: Example security review
version: "1.0"
context:
  - id: platform
    label: Which platform is in scope?
    type: choice
    phase: setup
    required: true
    options: [Platform A, Platform B]
  - id: tenant_name
    label: Tenant name
    type: text
    phase: context
    required: true
questions:
  - id: example-control
    question: Is the example control enabled?
    expected_value: The control is enabled.
    expected_answer: compliant
    positive: The example control is enabled.
    evidence: Review the relevant configuration with the customer.
    applies_when:
      platform: [Platform A]
    repeat_for: [platform]
    finding_title: Example control is disabled
    description: The control is not enabled.
    solution: Enable the control.
```

Context fields support `text`, `integer`, `choice`, and `multi_choice` input.
An `applies_when` mapping includes an item only when every named context value
matches; list-valued context (such as a multi-platform scope) matches when it
contains any configured value. Omit `applies_when` to make an item universal.
Questions can set `repeat_for` to choice context fields to ask the same control
separately for each selected value, preserving per-platform assessment results.

## Design direction

- Keep the interview and result lifecycle shared.
- Keep each assessment's question bank, evidence guidance, and specialized
  rules in its own pack.
- Migrate one proof of concept at a time and verify its generated outputs
  against the existing tool before retiring any behavior.
