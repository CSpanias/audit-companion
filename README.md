# Audit Companion

A framework for guided, live security assessments, with modular assessment
packs for MDM, remote access, VoIP, and beyond.

Audit Companion builds on the shared workflow in the
[MDM-Audit](https://github.com/CSpanias/mdm-audit),
[Remote-Access-Audit](https://github.com/CSpanias/remote-access-audit), and
[VoIP-Audit](https://github.com/CSpanias/voip-audit) proof of concepts. The
framework owns the common interview, response, and export behavior; assessment
packs own their context, control content, and applicability rules.

## Start an assessment

The built-in assessment packs start directly from their subcommand:

```powershell
audit-companion mdm
audit-companion remote-access
audit-companion voip
```

Each command begins the interactive setup and guided control review, then
writes JSON findings and a self-contained HTML report to a dedicated,
timestamped directory under `audit-companion/`. The HTML report contains a
unified executive summary, technical commentary, and remediation guidance.
Use `--output-dir reports` to choose another parent directory.

## Install for development

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev,docs]"
```

## Run a custom pack

```powershell
audit-companion validate path\to\assessment.yaml
audit-companion run path\to\assessment.yaml --output-dir .
```

Custom packs write `<pack-id>-findings.json` and `<pack-id>-report.html` to
their own timestamped subdirectory under the chosen output directory.

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
- Keep the source assessment content and guided workflow aligned as the packs
  evolve.
