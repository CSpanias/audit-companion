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
| MDM | Microsoft Intune for iOS/iPadOS and Android | Planned migration |
| Remote access | Microsoft Always On VPN and BeyondTrust PRA | Planned migration |
| VoIP | AudioCodes Session Border Controllers | Planned migration |

## Current status

The repository currently contains the reusable interview core, a validated
YAML pack format, and a small example pack. The original domain content and
specialized exports have not yet been migrated. Until then, the current CLI
accepts a pack file path; domain commands such as `audit-companion voip` are
the intended user-facing interface once the packs are available.

The planned command names are `mdm`, `remote-access`, and `voip`.

The current example workflow exports JSON findings, Markdown, and a
self-contained HTML report.

Start with [installation](installation.md) and the [workflow](workflow.md), or
read the [assessment pack format](framework/assessment-packs.md).
