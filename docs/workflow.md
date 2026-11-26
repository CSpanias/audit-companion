# Assessment workflow

Audit Companion is intended to support a guided configuration and governance
review, not to replace the assessor's judgement or automatically probe a
customer environment. The assessor shares the screen or conducts the review
over a call, asks the questions, and records the evidence and responses.

## Stages

1. **Assessment setup** — identify the organisation and select the in-scope
   platform or solution.
2. **Context collection** — record deployment and environment details. Fields
   can be conditional on information already collected.
3. **Control assessment** — present applicable controls, expected values,
   evidence guidance, and configuration locations. The assessor records
   compliant, non-compliant, not applicable, or unknown, with optional notes.
   A progress bar shows how many controls have been completed.
4. **Results** — turn non-compliant responses into findings and compliant
   responses into positive observations. Unknown and not-applicable answers
   remain in the response history without becoming findings.
5. **Export** — generate common machine-readable and human-readable outputs.

Built-in questions can repeat for selected platforms or other choice fields,
keeping answers and findings scoped to the relevant environment.

## Outputs

The framework currently exports a JSON assessment result and a self-contained
HTML report suitable for sharing or printing. The HTML report presents a
unified executive summary, an assessment configuration table, grouped
technical commentary, positive controls, remediation actions, and consolidated
references. Copy controls in the HTML report can copy each narrative section or
the complete report as Markdown; no Markdown report file is generated. The
structured findings output retains the response history and assessor notes.

Each assessment writes its reports into a dedicated timestamped directory
under `audit-companion/` by default. Use `--output-dir` to choose another
parent directory.

The built-in MDM, remote-access, and VoIP assessments use this shared workflow
while retaining their own questions, guidance, and applicability rules.
