---
name: test-strategy
description: Derive the test suite from spec requirements — unit, integration, regression surface, and what must stay manual — with tests named after REQ- IDs so the traceability gate passes. Use this skill whenever the user mentions tests, testing, TDD, QA, coverage, or asks "how should I test this", and always when implementing a change folder's tasks.md, reviewing a PR's test quality, or when `asdlc verify` fails on the traceability or coverage-delta gate.
---

# Test strategy

Tests exist to prove requirements hold, not to raise a number. In an agentic
workflow they do something else too: they are the only thing standing between a
confident model and production.

## Derivation, not invention

Every test traces to a scenario in `spec.md`. Work down the file:

```
REQ-001 scenario "happy path"      -> unit test
REQ-001 scenario "upstream 5xx"    -> unit test with the failure injected
REQ-002 scenario "concurrent write"-> integration test
NFR latency p95 < 300ms            -> load test in CI (nightly, not per-PR)
```

If a scenario has no test, either write it or delete the scenario. Both are
honest; leaving it is not.

## Naming (the traceability gate reads this)

The requirement ID must appear in the test name or docstring:

```python
def test_REQ_001_returns_503_when_upstream_fails():
    """REQ-001: on upstream 5xx the system returns 503 with Retry-After."""
```

```typescript
it("REQ-002: rejects a second checkout for the same cart", async () => { ... });
```

## The regression surface

The question is not "did I break the thing I wrote" — the agent's tests always
pass. It is **"what existing behaviour shares state, schema, or a code path with
what I touched?"** Answer it explicitly in `design.md`:

- What calls the function I changed? (`git grep`, not intuition)
- What reads the table I altered?
- What subscribes to the event I renamed?
- What did the last three incidents in this module have in common?

Those get regression tests before the change lands, not after.

## What agents get wrong, consistently

1. **Tests that assert the implementation.** Mocking the thing under test, then
   asserting the mock was called. This passes forever and proves nothing.
2. **Deleting or skipping a failing test to go green.** Never do this. If a test
   is wrong, say so out loud and change it in its own commit with a reason.
3. **Coverage theatre.** Executing lines without asserting on them. The gate
   measures changed-file coverage precisely because that number is gameable —
   your job is to make it meaningful, not to hit it.
4. **No failure paths.** Happy paths only. The bugs are all in the other branch.
5. **Non-deterministic tests.** Real clocks, real network, `sleep()`, ordering
   assumptions. A flaky test is worse than no test: it trains the team to ignore
   red.

## Levels

- **Unit** — pure logic, no I/O, milliseconds. Most of your tests.
- **Integration** — the seams: DB, queue, HTTP boundary. The bugs live here.
- **Contract** — if you changed a public API or event schema, test both sides.
- **E2E** — one per critical user journey. They are slow and flaky; ration them.
- **Manual/exploratory** — say what a machine cannot check (does this actually
  make sense to a user?) and who will check it.

## Before claiming done

Run the suite. Read the diff of the tests you wrote as if you were reviewing a
stranger's PR: does each test fail if you break the code it claims to cover?
Delete one line of production logic and check that something goes red. If
nothing does, the test is decoration.
