# Immutability

<!-- summary: Prefer new values over in-place mutation; mutation hides where state changed. -->
<!-- tier: core -->
<!-- category: Foundations -->

Prefer creating new values over mutating existing ones. Shared mutable state is
the hardest class of bug to trace: when a value can change anywhere, "who
changed it, and when?" has no local answer.

**Rule:** functions do not mutate their arguments or shared state. They return
new values.

```
// Avoid — mutates the caller's object
function rename(user, name) {
  user.name = name
  return user
}

// Prefer — returns a new object, original untouched
function rename(user, name) {
  return { ...user, name }
}
```

Applies equally to collections (build a new list/map rather than pushing into a
shared one) and to configuration and domain objects passed across module
boundaries.

**When mutation is justified:** only after profiling proves a real hot path, and
then contained inside a single function with a comment explaining why. "It might
be faster" is not a reason; a measurement is.
