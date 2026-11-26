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
4. **Results** — turn non-compliant responses into findings and compliant
   responses into positive observations. Unknown and not-applicable answers
   remain in the response history without becoming findings.
5. **Export** — generate common machine-readable and human-readable outputs.

Questions can be repeated for each selected platform or other choice field,
keeping answers and findings scoped to the relevant environment.

## Outputs

The framework currently exports a JSON assessment result and a self-contained
HTML report suitable for sharing or printing. The HTML report presents a
unified executive summary, technical commentary, and remediation guidance,
followed by assessment context, findings, positive observations, and response
history. Each response records its question, answer, notes, and optional
scope.

Each assessment writes its reports into a dedicated timestamped directory
under `audit-companion/` by default. Use `--output-dir` to choose another
parent directory.

Assessment packs may later add specialized outputs through shared adapters,
without coupling those formats to the interview engine.
