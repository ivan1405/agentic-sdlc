# Small, focused units

<!-- summary: Small files and functions, low nesting, organized by feature; handle errors; no hardcoded values. -->
<!-- tier: core -->
<!-- category: Foundations -->

Many small, cohesive files beat a few large ones. Small units are easier to
name, test, review, and delete.

**Size ceilings** (split when exceeded, don't argue the edge):
- File: ~800 lines max; review for splitting at 400+.
- Function: ~50 lines max.
- Nesting: 4 levels max — deeper means extract a function or invert a guard.

**Organize by feature/domain, not by type.** A `checkout/` folder that holds its
model, service, and tests beats parallel `models/ services/ tests/` trees you
have to cross-reference to understand one feature.

**High cohesion, low coupling.** A module should do one thing; things that change
together live together; things that don't, don't.

**Handle errors deliberately.** Catch what you can act on, add context, and
surface a clear message — never swallow an error silently.

```
try {
  return await risky()
} catch (err) {
  log.error("risky() failed", err)
  throw new Error("Could not complete X: <actionable detail>")
}
```

**No hardcoded values.** Configuration, URLs, thresholds, and credentials come
from configuration or environment — never inlined literals.
