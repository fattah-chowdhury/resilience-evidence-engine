# Security

REE 0.1.0 is experimental. It is a local small-data processor, not a sandbox for hostile files or a
critical warning system. Dependencies and external providers can change after the recorded audit date.

No secrets are required by the default demo. Never commit tokens, private inputs or private output runs.
Public mode suppresses records based on declarations; it is not automatic anonymization. Inspect config
paths, notes and rights before sharing. HTML/CSV output is escaped; unsafe YAML, XML entities, private
DNS destinations and HTTP redirects are rejected by the implemented paths. Endpoint DNS checking and
subsequent connection are separate; stronger address-pinning is future work.

Report suspected vulnerabilities privately to the repository owner's designated channel when established.
No security email or SLA is claimed. Include a minimal non-sensitive reproduction and version details;
avoid public disclosure of private records. Review audit/dependency-audit-status.json and
RELEASE_READINESS.md before deployment. An unavailable advisory service is recorded as BLOCKED.
