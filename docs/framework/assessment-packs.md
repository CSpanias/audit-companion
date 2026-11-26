# Assessment packs

An assessment pack defines the content and applicability rules for a review.
The framework owns the shared prompts, response lifecycle, and report
generation; packs keep domain-specific content independent.

## Structure

```yaml
id: example-access-review
title: Example access review
version: "1.0"
context:
  - id: platforms
    label: Which platforms are in scope?
    type: multi_choice
    phase: setup
    required: true
    options: [iOS, Android]
  - id: tenant
    label: Tenant or organisation name
    type: text
    phase: context
    required: true
questions:
  - id: access-review
    section: Governance
    question: Are access permissions reviewed periodically?
    expected_value: Access is reviewed at least quarterly.
    expected_answer: compliant
    evidence: Inspect the documented review process and sample evidence.
    applies_when:
      platforms: [iOS, Android]
    repeat_for: [platforms]
    finding_title: Access permissions are not reviewed periodically
    description: No recurring access review was confirmed.
    solution: Establish a recurring review and retain completion evidence.
    positive: Access permissions are reviewed periodically.
    references:
      - https://example.org/security-guidance
```

Context fields support `text`, `integer`, `choice`, and `multi_choice` input.
Fields can belong to the `setup` or `context` phase. A required field must be
answered; choice values are validated against the declared options.

## Applicability and repetition

`applies_when` is a mapping from context field IDs to allowed values. All
conditions in the mapping must match. If the context value is a list, any
matching value satisfies that field's condition. Items without conditions
apply universally.

Questions can use `repeat_for` to be asked separately for each selected value
of one or more choice fields. The selected scope is preserved with the
response and any resulting finding. This supports reviews where the same
control must be assessed independently for iOS and Android, for example.

Pack validation catches duplicate IDs, unknown context references, invalid
choice values, and context dependencies that refer to fields not yet collected.
Use:

```powershell
audit-companion validate examples\minimal.yaml
```

## Migration principles

- Preserve original assessment questions, evidence guidance, and finding
  content.
- Translate assessment-specific selection rules into pack conditions or a
  small domain adapter when the YAML schema is not expressive enough.
- Compare generated results with the existing tool before considering a
  migration complete.
- Keep specialized export adapters separate from the common interview engine.
