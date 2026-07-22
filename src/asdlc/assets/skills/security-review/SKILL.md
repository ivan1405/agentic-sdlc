---
name: security-review
description: Threat-model a change and review a diff for vulnerabilities before it reaches a PR — trust boundaries, injection, authz, secrets, dependencies, and the OWASP surface relevant to the code that actually changed. Use this skill whenever the user mentions security, vulnerabilities, threat modelling, pentest, CVEs, dependencies, secrets, auth, or PII, and always when a change touches authentication, authorization, payments, personal data, file upload, deserialization, a public API, or infrastructure. Also use when `asdlc verify` fails the security-scan gate.
---

# Security review

Scanners find known patterns. You are here for the other half: the logic flaws a
scanner cannot see, on the specific diff in front of you.

## Scope discipline

Review the **delta**, not the codebase. A full-repo security essay is unactionable
and will be ignored. If the change adds one endpoint, review that endpoint and
what it can reach.

## The threat model delta (four questions)

Answer these in `design.md`. If all four are no, write "no threat model delta"
and move on — that is a legitimate outcome and saves everyone's time.

1. **New trust boundary?** Does data now cross from less-trusted to more-trusted?
   (new endpoint, new consumer, new webhook, new file upload)
2. **New input?** Anything the user, a partner, or another service controls that
   reaches a parser, a query, a shell, a template, a deserializer, or a filesystem path.
3. **New secret or credential?** Where does it live, who can read it, how is it rotated?
4. **New dependency or new permission?** What does it pull in, who maintains it,
   what does it get access to?

## The review pass

Walk the diff against this list. Stop at the ones that apply; skip the rest.

- **Authorization** — the flaw scanners miss most. For every new handler: *who*
  is allowed to call this, is that checked, and is it checked against the
  resource being accessed (not just "is logged in")? IDOR lives here.
- **Injection** — parameterized queries only; no string-built SQL, no shelling
  out with user input, no `eval`, no template rendering of user data as code.
- **Secrets** — nothing hardcoded, nothing in logs, nothing in error responses,
  nothing in a fixture "just for tests".
- **Data exposure** — does the response return more fields than the spec asked
  for? Serializers that leak by default are the classic agent mistake.
- **Crypto** — no homemade crypto, no MD5/SHA1 for passwords, no ECB, no static
  IV. If the diff implements crypto primitives, that is a stop-and-ask.
- **SSRF / path traversal** — any URL or path derived from input gets an
  allowlist, not a denylist.
- **Deserialization** — never deserialize untrusted data into objects.
- **Rate limiting & DoS** — unbounded loops, unbounded queries, missing
  pagination, regexes with catastrophic backtracking.
- **Dependencies** — new package: check it is the real one (typosquatting),
  maintained, and licensed compatibly.

## Reporting

For each finding: **file:line — what an attacker does — impact — fix.** Rank by
exploitability, not by CWE tidiness. Three real findings beat thirty
informational ones; a report nobody reads has negative value.

Findings that are real but out of scope for this change go in the proposal's
open questions or a new ticket — not silently into the diff.

## Never

- Never write, extend, or "demo" an exploit, even to prove a point. Describe the
  attack path in prose and fix the code.
- Never weaken a security control to make a test pass.
- Never treat a clean scanner run as a clean review. `security-scan` passing
  means no *known pattern* matched.
- Never assume a client-side check is a control.
