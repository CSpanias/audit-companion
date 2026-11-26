# Voice over IP (VoIP)

VoIP-Audit supports configuration and governance reviews of VoIP platforms,
not penetration testing. The current standalone assessment supports
AudioCodes Session Border Controllers (SBCs).

Review areas include authentication, cryptography, administrative security,
access control, threat protection, monitoring, logging, and platform lifecycle
management.

## Assessment stages

1. **Setup** — identify the organisation and VoIP solution.
2. **Context collection** — record platform model and version, deployment
   type, identity and SIP providers, management interfaces, and device type.
3. **Control assessment** — review platform controls using evidence and
   configuration guidance, recording status and optional notes.
4. **Reporting** — generate a Markdown report and structured findings.

See [VoIP fundamentals](../background/voip-fundamentals.md) for architecture
and protocol background. The existing AudioCodes-specific control context is
maintained in the [AudioCodes SBC guide](https://app.notion.com/p/AudioCodes-SBCs-40e5b866a8b480c48c42db081c49c26c?pvs=21).

## Outputs and downstream reporting

The standalone tool generates:

- `voip-findings.json`
- `voip-report.md`
- `voip-notes.json`

## References

The source assessment identifies the following general reference for future
inclusion in its control content:

- [NCSC: Private Branch Exchange (PBX) best practice](https://www.ncsc.gov.uk/guidance/private-branch-exchange-best-practice)

## Migration status

VoIP is a planned Audit Companion assessment pack. Its original controls and
AudioCodes-specific guidance have not yet been migrated.
