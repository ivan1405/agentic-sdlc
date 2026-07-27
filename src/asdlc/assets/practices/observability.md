# Observability

<!-- summary: Structured logs, correlation IDs, metrics and traces — enough to debug in production without a redeploy. -->
<!-- tier: domain -->
<!-- category: DevOps & Platform -->

You cannot fix what you cannot see. A change is not done when it works on your
machine; it is done when you could diagnose it failing in production from the
telemetry alone.

**Structured logs, not prose.** Emit machine-parseable events (key/value or
JSON), not free-text sentences. Every log line carries a level, a timestamp, and
the identifiers needed to find related lines.

**Correlation IDs.** A request/trace ID is generated at the edge and threaded
through every log line, downstream call, and queue message it touches, so one
request can be reconstructed end to end.

**The three signals, used for what they're good at:**
- **Logs** — discrete events, for "what happened at 14:03".
- **Metrics** — cheap aggregates (rate, error, duration), for dashboards and alerts.
- **Traces** — the path of one request across services, for "where did the time go".

**Instrument the failure paths.** Log and count errors with enough context to
act (what operation, which inputs' shape — not their secret values, what the
upstream returned). An error you can't triage from its log is a redeploy waiting
to happen.

**Alert on symptoms, not causes.** Alert on user-visible SLO breaches (latency,
error rate), not on every internal metric — noisy alerts get muted, and a muted
alert is worse than none.

**Never log secrets or PII.** Tokens, passwords, full card/PII fields must never
reach logs or traces. Redact at the logging boundary, not by remembering to omit
them at each call site.
