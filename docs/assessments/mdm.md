# Mobile Device Management (MDM)

Audit Companion's MDM assessment guides assessors through a structured
Mobile Device Management security review, shows platform-specific guidance,
and generates structured findings and a report.

The assessment covers Microsoft Intune environments for:

- iOS and iPadOS
- Android

## Setup and context

Setup collects the client or tenant name, platforms in scope, MDM solution
and service release, and platform-specific policy and device counts. This
information is used to select controls and populate outputs.

## Guided review

For each applicable control, the assessor sees evidence requirements,
platform-specific review guidance, and the relevant configuration location.
The assessor records a compliance status and optional notes. Controls are
filtered to the selected platforms. Shared controls are assessed separately
for each platform so the resulting evidence and findings retain their scope.

## Outputs

Start the guided review with:

```powershell
audit-companion mdm
```

The assessment writes `mdm-findings.json` and `mdm-report.html`. The JSON
report includes the response history and assessor notes.
