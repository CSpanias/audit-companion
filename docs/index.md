# Audit Companion

**A framework for guided, live security assessments.**

Audit Companion brings the shared workflow of three existing assessment tools
into one extensible framework:

- [MDM-Audit](https://github.com/CSpanias/mdm-audit)
- [Remote-Access-Audit](https://github.com/CSpanias/remote-access-audit)
- [VoIP-Audit](https://github.com/CSpanias/voip-audit)

The tools are designed for an assessor-led review, including live walkthroughs
with a customer over a call. The assessor gathers context, asks structured
control questions, uses evidence and configuration guidance, records answers
and notes, then exports assessment results.

## Assessment packs

Each assessment pack owns its domain-specific questions, evidence guidance,
context, and applicability rules. The framework provides the common interview,
answer capture, result generation, and reporting lifecycle.

| Pack | Focus | Status |
| --- | --- | --- |
| MDM | Microsoft Intune for iOS/iPadOS and Android | Available |
| Remote access | Microsoft Always On VPN and BeyondTrust PRA | Available |
| VoIP | AudioCodes VoIP platforms | Available |

## Current status

The framework includes reusable interactive workflows, built-in assessment
packs, conditional context and control selection, and JSON and self-contained
HTML reports.

Start an assessment by running `audit-companion mdm`,
`audit-companion remote-access`, or `audit-companion voip`.

Start with [installation](installation.md) and the [workflow](workflow.md), or
read the [assessment pack format](framework/assessment-packs.md).
