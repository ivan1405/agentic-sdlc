# Test first

<!-- summary: Write the failing test first; RED to GREEN to REFACTOR; cover the failure paths. -->
<!-- tier: core -->
<!-- category: Testing & QA -->

Write the test before the implementation. Tests written after the fact tend to
assert what the code already does — they codify bugs and skip the failure paths
that were never considered.

**The cycle:**
1. **RED** — write a test for the next small behavior. Run it; confirm it fails
   for the right reason. A test that passes before you write the code is testing
   nothing.
2. **GREEN** — write the minimum code to pass.
3. **REFACTOR** — clean up with the test as a safety net.

**Cover the failure path, not just the happy path.** The happy path is the part
the code was going to get right anyway; the bugs live in the error branches,
the empty inputs, and the boundaries.

**Test pyramid:** many fast unit tests, fewer integration tests (real
boundaries — API, database), a thin layer of end-to-end tests for critical user
flows. Push detail down to the fastest layer that can catch it.

**Coverage ≥ 80% on changed code** — but coverage is a floor, not a goal.
Coverage without assertions is theatre; a covered line with no assertion proves
only that it ran.

**When a test fails, fix the code, not the test.** Weakening or deleting a test
to get green is how a suite becomes a liar. Change the test only when the
requirement itself was wrong — and say so.
