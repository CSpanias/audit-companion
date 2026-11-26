# BeyondTrust Privileged Remote Access

This guide provides background for assessors reviewing BeyondTrust Privileged
Remote Access (PRA). It is intended both as control context and as an
introduction for consultants who have not previously assessed PRA.

## What is Privileged Remote Access?

Traditional VPN solutions provide network connectivity into an organisation.
Depending on routing and permissions, connected users may reach a range of
internal services.

PRA platforms broker access to approved systems and sessions instead of
granting broad network-level access. A user authenticates to the PRA platform,
selects an authorised asset, and the platform establishes and controls the
remote session.

PRA can provide session recording, credential vaulting and injection,
approval workflows, session monitoring, access reviews, and detailed
auditing. It is commonly used for administrative, vendor, contractor, and
sensitive-system access.

## BeyondTrust PRA

BeyondTrust PRA provides controlled remote access for internal and external
users. Capabilities include enterprise identity integration, session
monitoring and recording, privileged credential management, granular access
policies, and third-party access management.

See the [BeyondTrust product documentation](https://docs.beyondtrust.com/pra/docs/welcome-to-privileged-remote-access).

## Assessment methodology

The review is divided into six areas:

1. Platform configuration
2. Authentication
3. Administrative security
4. Cryptography
5. Access control
6. Monitoring and detection

### Platform configuration

Understand whether PRA is cloud-hosted, customer-managed, or hybrid. The
deployment model affects responsibilities for infrastructure maintenance,
updates, backup, and disaster recovery. Identify the product version and
confirm there is a defined process to identify, test, approve, schedule, and
deploy updates.

References:

- [Product status](https://docs.beyondtrust.com/pra/docs/pf-status)
- [PRA updates](https://docs.beyondtrust.com/pra/docs/pf-updates)

### Authentication

Identify the user identity source and integrations, such as Microsoft Entra
ID, Active Directory, LDAP, SAML, or OpenID Connect. Review MFA separately
for users and administrators, vendor authentication settings, and whether
each person has a unique account.

References:

- [Identity providers](https://docs.beyondtrust.com/pra/docs/identity-providers)
- [Group policy settings](https://docs.beyondtrust.com/pra/docs/pf-group-policies#group-policy-settings)
- [Vendor authentication](https://docs.beyondtrust.com/pra/docs/pf-security#vendor-authentication)
- [Security providers](https://docs.beyondtrust.com/pra/docs/pf-security-providers)

### Administrative security

Determine whether credential injection is used so users do not need to see or
handle privileged passwords. Review automated password rotation, session
context requirements (such as ticket or change references), simultaneous
credential checkout, and malware inspection for file transfers where
applicable.

References:

- [Account policies](https://docs.beyondtrust.com/pra/docs/pf-account-policies)
- [Scheduled password rotation](https://docs.beyondtrust.com/pra/docs/pf-vault-options#scheduled-password-rotation-rules)
- [Jump policy context requirements](https://docs.beyondtrust.com/pra/docs/pf-jump-policies#context-requirement)
- [Account groups](https://docs.beyondtrust.com/pra/docs/pf-account-groups)
- [Simultaneous checkout rules](https://docs.beyondtrust.com/pra/docs/pf-vault-options#allow-simultaneous-checkout-rules)
- [ICAP configuration](https://docs.beyondtrust.com/pra/docs/pf-security#icap-configuration)

### Cryptography

Review TLS configuration, supported protocol versions, cipher suites, and
certificates against current vendor guidance. Current PRA versions enable
TLS 1.2 and TLS 1.3 by default and do not allow them to be disabled through
the appliance interface; focus the review on cipher suites, certificates,
and vendor recommendations.

Reference: [TLS configuration](https://docs.beyondtrust.com/pra/docs/pf-tls-configuration).

### Access control

Review how permissions are granted, periodically reviewed, and removed when
roles change. Govern Jump Clients carefully because they can provide
persistent access. Ensure third-party access expires when no longer needed,
and consider network restrictions on administrative interfaces where
appropriate.

References:

- [Jump Clients](https://docs.beyondtrust.com/pra/docs/jump-clients-1)
- [Vendor accounts](https://docs.beyondtrust.com/pra/docs/pf-vendors)
- [Network restrictions](https://docs.beyondtrust.com/pra/docs/pf-security#network-restrictions)

### Monitoring and detection

Confirm that authentication, session, and administrative activity is logged
and retained. Verify that session recording is enabled and policies do not
allow sessions to bypass recording. Configure appropriate inactivity
timeouts for privileged sessions.

References:

- [Reports](https://docs.beyondtrust.com/pra/docs/pf-reports)
- [Appliance administration](https://docs.beyondtrust.com/pra/docs/pf-appliance-administration)
- [PRA configuration](https://docs.beyondtrust.com/pra/docs/pf-configuration)
- [Jump policy recording controls](https://docs.beyondtrust.com/pra/docs/pf-jump-policies#disable-recordings)
- [Group policy settings](https://docs.beyondtrust.com/pra/docs/pf-group-policies)
- [Idle user timeout](https://docs.beyondtrust.com/pra/docs/pf-security#log-out-idle-user-after)
- [Session inactivity timeout](https://docs.beyondtrust.com/pra/docs/pf-security#remove-user-from-session-after-inactivity)

## Guided assessment

The standalone [Remote-Access-Audit](https://github.com/CSpanias/remote-access-audit)
tool provides a guided assessment for BeyondTrust PRA. Its assessment
questions and this background guide are planned for migration as a
Remote-Access assessment pack in Audit Companion.
