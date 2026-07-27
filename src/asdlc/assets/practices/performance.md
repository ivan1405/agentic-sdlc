# Performance

<!-- summary: Set budgets, measure before optimizing, watch tail latency, kill N+1s, cache with invalidation. -->
<!-- tier: domain -->
<!-- category: DevOps & Platform -->

Performance is a requirement with a number, not a vibe. "Fast" is not testable;
"p95 under 300ms at 50 rps" is. Set the budget, then defend it with measurement.

**Budgets, stated up front.** Define the targets that matter for this system —
latency (with a percentile), throughput, memory, bundle size, cost — and treat a
regression past budget like a failing test.

**Measure before you optimize.** Profile against a realistic workload and fix
what the data shows, not what you guess. Micro-optimizing an unmeasured path
trades readability for nothing. (This is also why immutability's "mutate only
after profiling" rule holds.)

**Watch the tail.** Averages hide the pain; users feel p95/p99. Track and alert
on tail latency, not the mean.

**Kill N+1s and unbounded work.** The most common real-world slowdown is a query
in a loop. Batch, join, or preload. Every query has a bound and an index for its
access pattern; every list operation is paginated.

**Cache deliberately — with invalidation.** A cache without a correct
invalidation story is a stale-data bug in waiting. Decide TTLs and eviction up
front, and know how a write propagates.

**Guard against regressions.** Keep a load/perf check on the paths with a budget
so a change that doubles latency is caught in CI, not by users. Do the expensive
work off the request path (async/queue) when the user doesn't need to wait for it.
