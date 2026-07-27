# Evidence-based completion

<!-- summary: No completion claim without fresh verification evidence you produced this run. -->
<!-- tier: core -->
<!-- category: Testing & QA -->

**The iron law: no claim of success without fresh verification evidence.** "It's
done" without evidence is a guess. If you did not run the check in this session,
you cannot say it passed — the code may have changed since the last run.

**The gate — run it before any success claim:**
1. **IDENTIFY** — what command would prove this claim?
2. **RUN** — execute the full command, fresh and complete.
3. **READ** — read the whole output; check the exit code; count failures.
4. **VERIFY** — does the output actually confirm the claim? If not, report the
   real state with the evidence.
5. **CLAIM** — only now state the result, with the numbers.

| Claim | Evidence that earns it |
|---|---|
| Tests pass | This run's output: 0 failures |
| Build succeeds | Build command: exit 0 |
| Bug fixed | A regression test that fails without the fix, passes with it |
| Requirements met | Line-by-line check against the spec |
| Delegated work done | You inspected the diff — not the report that it was done |

**Red-green for regression tests:** write the test → confirm it FAILS without
the fix → apply the fix → confirm it PASSES. If it never failed, it isn't
testing the fix.

**Banned:** "should work", "probably passes", "looks correct", declaring victory
before running anything. **Required:** "34/34 passed", "build exit 0". Confidence
is not evidence.
