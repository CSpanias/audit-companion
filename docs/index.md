# Audit Companion

**An interactive tool for guided, live security assessments.**

Audit Companion brings the shared workflow of three existing assessment tools
into one interactive tool:

- [MDM-Audit](https://github.com/CSpanias/mdm-audit)
- [Remote-Access-Audit](https://github.com/CSpanias/remote-access-audit)
- [VoIP-Audit](https://github.com/CSpanias/voip-audit)

The tools are designed for an assessor-led review, including live walkthroughs
with a customer over a call. The assessor gathers context, asks structured
control questions, uses evidence and configuration guidance, records answers
and notes, then exports assessment results.

## Assessments

Each subcommand provides its own built-in questions, evidence guidance,
context collection, and platform-specific applicability.

| Assessment | Focus | Status |
| --- | --- | --- |
| MDM | Microsoft Intune for iOS/iPadOS and Android | Available |
| Remote access | Microsoft Always On VPN and BeyondTrust PRA | Available |
| VoIP | AudioCodes VoIP platforms | Available |

## Current status

The tool shares the interview, results, and reporting workflow across the
built-in assessments. It generates JSON findings and self-contained HTML
reports.

Start an assessment by running `audit-companion mdm`,
`audit-companion remote-access`, or `audit-companion voip`.

Start with [installation](installation.md) and the [workflow](workflow.md).
