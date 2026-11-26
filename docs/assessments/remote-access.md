# Remote access

Audit Companion's remote-access assessment supports structured configuration
and governance reviews of remote access solutions. It is not intended to
perform penetration testing. The current assessment packs cover:

- Microsoft Always On VPN
- BeyondTrust Privileged Remote Access (PRA)

Review areas include authentication, cryptography, access control, privileged
access governance, monitoring, auditing, and platform configuration.

## Assessment stages

1. **Setup** — identify the organisation and remote access solution.
2. **Context collection** — record deployment-specific information such as
   authentication methods, identity providers, VPN configuration, deployment
   model, and product version.
3. **Control assessment** — review applicable controls with evidence and
   platform guidance; capture compliance status and assessor notes.
4. **Reporting** — generate an HTML report and structured JSON findings.

For BeyondTrust PRA background and control context, see
[BeyondTrust PRA](../background/beyondtrust-pra.md).

## Outputs

Start the guided review with:

```powershell
audit-companion remote-access
```

The assessment writes `remote-access-findings.json` and
`remote-access-report.html`. The JSON report includes the response history and
assessor notes.
