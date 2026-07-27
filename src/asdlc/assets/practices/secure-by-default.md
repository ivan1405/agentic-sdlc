# Secure by default

<!-- summary: Secrets in env vars; validate inputs; parameterize queries; check authz; don't leak errors. -->
<!-- tier: core -->
<!-- category: Security & Data -->

Security is a default, not a later pass.

**Secrets never live in code.** Read them from the environment or a secrets
manager, and fail fast if a required one is missing — never fall back to a
baked-in default.

```
const key = process.env.API_KEY
if (!key) throw new Error("API_KEY not configured")
```

A secret committed once is compromised forever, even in a test fixture, even in
a private repo. If one leaks: rotate it immediately, then find the others.

**Before merging code that touches untrusted input, auth, or data:**
- All external input validated at the boundary (see boundary validation).
- Database access uses parameterized queries — never string-concatenated SQL.
- Rendered/user-controlled HTML is escaped/sanitized.
- Authentication and authorization checked on every protected path — not just
  the UI that hides the button.
- Rate limiting on public endpoints.
- Error messages and logs reveal nothing sensitive (stack traces, secrets, PII,
  internal hostnames) to the caller.

**When you find a vulnerability:** stop, fix the critical issue before
continuing, rotate anything exposed, and scan the codebase for the same pattern
elsewhere — one instance is rarely the only one.
