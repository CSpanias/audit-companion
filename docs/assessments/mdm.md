# Mobile Device Management (MDM)

MDM-Audit is an interactive assessment tool for Mobile Device Management
security reviews. It guides assessors through a structured questionnaire,
shows platform-specific review guidance, and generates report text and
structured findings.

The existing assessment covers Microsoft Intune environments for:

- iOS and iPadOS
- Android

## Setup and context

The standalone tool collects the client or tenant name, platforms in scope,
MDM solution and service release, and platform-specific policy and device
counts. It uses this information to select controls and populate outputs.

## Guided review

For each applicable control, the assessor sees evidence requirements,
platform-specific review guidance, and the relevant configuration location.
The assessor records a compliance status and optional notes. Controls are
filtered to the selected platforms. Shared controls are assessed separately
for each platform so the resulting evidence and findings retain their scope.

## Outputs

The standard standalone outputs are:

- `mdm-findings.json`
- `mdm-report.md`
- `mdm-notes.json`

## Migration status

MDM is a planned Audit Companion assessment pack. Its original content has not
yet been migrated; the current prototype's `examples/minimal.yaml` is only a
framework example.
