# Audit Companion

An interactive tool for guided, live security assessments of MDM, remote
access, and VoIP environments.

Audit Companion builds on the shared workflow in the
[MDM-Audit](https://github.com/CSpanias/mdm-audit),
[Remote-Access-Audit](https://github.com/CSpanias/remote-access-audit), and
[VoIP-Audit](https://github.com/CSpanias/voip-audit) proof of concepts. Each
subcommand runs its built-in assessment with default questions, evidence
guidance, and reporting.

## Start an assessment

Start the assessment you need:

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
