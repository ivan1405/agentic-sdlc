%%DESC: Generate or refresh a validated, interactive architecture/workflow/sequence/data-flow/lifecycle diagram with the archify skill%%
%%HINT: [optional: diagram type and/or scope, e.g. "architecture: auth service"]%%
Diagram %%ARG%%

This is the maintenance command for the `archify` skill (tt-a1i/archify, MIT)
that `/onboard` first offers to add. Use it any time you want a fresh diagram,
or an existing one needs to reflect recent code changes — it doesn't touch the
context file or re-run the rest of onboarding.

1. Confirm the `archify` skill is installed — its `SKILL.md` should show up
   in your skill list. If it isn't, tell the user to run
   `npx skills add tt-a1i/archify -g` (or without `-g` for a project-local
   install) and reconnect/restart their agent tool, then stop — don't install
   it yourself, `/onboard` is the only place that does that.
2. Work out scope from `%%ARG%%` (ask, if empty): which diagram type —
   `architecture`, `workflow`, `sequence`, `dataflow`, or `lifecycle` — and
   what part of the system. If it's ambiguous, run the skill's own
   `guide "<scenario>"` command rather than guessing the type yourself.
3. When the diagram must reflect real code rather than a proposed design,
   explore the actual repository first — read the relevant source, or call a
   `codegraph` MCP server's `analyze_code_relationships` if one is connected
   (refresh the index first if it predates recent changes to the affected
   area). If neither is available, fall back to hand-exploring; never invent
   components or relationships that aren't in the code.
4. Follow the archify skill's own fast authoring path: author the typed JSON
   IR, `validate --quality showcase`, then `deliver` once for the final HTML.
   A non-zero exit is never success — repair only the diagnosed subject and
   re-run, don't guess at geometry.
5. Tell the user the delivered HTML's path and offer `visual-check` before
   handing it over if they want confirmation it renders cleanly on a real
   screen. Save it under `docs/` unless the user names another location.
