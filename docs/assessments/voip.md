# Voice over IP (VoIP)

The VoIP assessment supports configuration and governance reviews of VoIP
platforms, not penetration testing. The current assessment focuses on
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
4. **Reporting** — generate an HTML report and structured JSON findings.

See [VoIP fundamentals](../background/voip-fundamentals.md) for architecture
and protocol background, and the [AudioCodes SBC assessment guide](../background/audiocodes-sbc-guide.md)
for platform-specific context.

## Start the assessment and reporting

Run the interactive assessment with:

```powershell
audit-companion voip
```

The assessment writes `voip-findings.json` and `voip-report.html`. The JSON
report includes the response history and assessor notes.

## References

The control pack includes this general reference:

- [NCSC: Private Branch Exchange (PBX) best practice](https://www.ncsc.gov.uk/guidance/private-branch-exchange-best-practice)
