# Surgical changes

<!-- summary: Change only what the task requires; match existing style; don't clean up adjacent code. -->
<!-- tier: core -->
<!-- category: Foundations -->

Change only what the task requires. Every line in a diff should trace directly
to the request. A reviewer must be able to find the actual change without
wading through unrelated edits.

**Do:**
- Touch only the lines the task needs.
- Match the surrounding style — naming, formatting, idioms — even if you'd do it
  differently. Consistency beats personal preference in someone else's code.
- Clean up only the orphans your own change created (an import you made unused,
  a now-dead branch you introduced).

**Don't:**
- "Improve" adjacent code, comments, or formatting while you're in there.
- Reformat, re-sort, or re-style regions you didn't need to modify.
- Delete unrelated dead code — mention it so it can be handled as its own
  change, but leave it.

**Cleanup and refactoring are separate requests.** "While I'm here" is how a
one-line fix becomes an unreviewable diff. If you spot a worthwhile improvement
outside the scope, note it and move on — don't fold it in.
