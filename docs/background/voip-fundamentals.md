# VoIP fundamentals

Voice over Internet Protocol (VoIP) carries telephone calls and other voice
communications over IP networks rather than traditional telephone
infrastructure. Organisations use VoIP for internal communications, contact
centres, conferencing, and collaboration platforms such as Microsoft Teams.

VoIP platforms are network-connected systems that often provide web-based
administration, integrate with directory services, support remote management,
and process sensitive business communications. A compromise can expose
communications, enable toll fraud, disrupt service, or provide access to
privileged administrative functions. VoIP infrastructure should therefore
receive security governance and configuration review appropriate to its
criticality.

## Components

- **IP phones and softphones** are the user endpoints. Softphones run on
  desktops, laptops, tablets, or mobile devices.
- **PBX (Private Branch Exchange)** provides call control, routing,
  extensions, voicemail, conferencing, user administration, and call-handling
  policies. Examples include Microsoft Teams Phone, Cisco Unified
  Communications Manager, 3CX, Asterisk, and FreePBX.
- **SIP trunks** connect an organisation's VoIP environment to external
  telephone networks using Session Initiation Protocol.
- **Session Border Controllers (SBCs)** control inbound and outbound call
  flows at network boundaries. They can validate SIP traffic, hide internal
  addressing, enforce security policy, manage encryption, detect malicious
  activity, and protect services from denial-of-service attacks.
- **Voice gateways** connect IP-based telephony with legacy technologies,
  including analogue devices and fax systems.

A simplified call flow is:

```text
User -> IP phone / softphone -> PBX / VoIP platform -> SBC
     -> SIP trunk provider -> public telephone network -> destination
```

## Protocols

- **SIP (Session Initiation Protocol)** establishes, manages, and terminates
  calls. It handles signalling, not the audio itself.
- **RTP (Real-Time Transport Protocol)** typically carries the audio after a
  call has been established.
- **SRTP (Secure Real-Time Transport Protocol)** encrypts RTP to help protect
  voice confidentiality and integrity.
- **TLS (Transport Layer Security)** commonly protects SIP signalling.
  Using TLS with SRTP protects both signalling and the voice stream.
- **SSH (Secure Shell)** is frequently used for administration. Reviews
  should consider access restrictions, authentication, and cryptographic
  configuration; public-key authentication is preferable where supported.

## Further reading

- [VoIP architecture and features](https://www.esds.co.in/blog/voip-understanding-architecture-and-features/)
- [SBC TLS and SRTP configuration guide](https://telcobridges.com/learning/voip-security/sbc-tls-srtp-configuration-guide/)
- [AudioCodes SBC assessment guidance](https://app.notion.com/p/AudioCodes-SBCs-40e5b866a8b480c48c42db081c49c26c?pvs=21)
