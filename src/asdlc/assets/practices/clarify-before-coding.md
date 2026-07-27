# Clarify before coding

<!-- summary: Surface assumptions and ask on ambiguity; be honest about uncertainty; check current docs. -->
<!-- tier: core -->
<!-- category: Foundations -->

When requirements are ambiguous, surface your assumptions and ask — don't guess
silently and build the wrong thing confidently. A minute of clarification is
cheaper than a day of rework, and far cheaper than a wrong thing shipped.

**When multiple interpretations exist, present them.** Don't pick one silently.
State the options and their trade-offs so the decision is made by whoever owns
it.

```
Before I build the data export, three things aren't specified:
  1. Scope — all records, or the current filter? (privacy implications)
  2. Delivery — synchronous download, or a background job + link?
  3. Fields — which, and do we exclude sensitive ones?
Simplest option that fits: a paginated JSON endpoint. Shall I go with that?
```

**Push back when a simpler path exists.** "This can be done in half the code by
…" is a service, not an overstep.

**Be honest about uncertainty.** "I'm not sure — here's how I'd verify" beats a
confident guess. Don't state as fact what you haven't checked.

**Check current documentation before coding against an API.** Library and
framework APIs drift between versions; verify the signature and behavior against
the version actually in use rather than trusting memory.
