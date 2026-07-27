# Data & privacy

<!-- summary: Minimize, classify, encrypt, and retain PII deliberately; least-privilege access with an audit trail. -->
<!-- tier: domain -->
<!-- category: Security & Data -->

Personal data is a liability, not an asset. Every field you store is something
you must protect, justify, and eventually delete. Handle it deliberately or it
becomes a breach headline.

**Minimize.** Collect and store the least data that does the job. The safest
field is the one you never captured. If you don't have a concrete use, don't
persist it.

**Classify.** Know which data is personal (PII), sensitive (health, financial,
credentials), or public. Handling rules follow the classification, and the
classification is written down, not folklore.

**Encrypt in transit and at rest.** TLS on the wire; encryption at rest for
stores holding personal or sensitive data. Secrets and keys come from a secrets
manager (see secure-by-default), never the codebase.

**Retention and deletion are features.** Define how long each class of data
lives and delete it when that expires. Support a real delete path (right-to-be-
forgotten), including backups and derived copies — not just a soft-delete flag.

**Least-privilege access, with an audit trail.** Access to personal data is
granted by need, scoped as narrowly as possible, and logged (who read/changed
what, when). Broad standing access to a production PII store is a finding.

**Don't leak it downstream.** Personal data must not flow into logs, traces,
analytics events, error reports, or test fixtures. Mask or tokenize before it
crosses those boundaries.

**Consent and purpose.** Use data only for the purpose it was collected for;
where consent is required, record it and honor its withdrawal.
