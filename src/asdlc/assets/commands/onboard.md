%%DESC: Skim the codebase once and fill in the context file with real project facts%%
%%HINT: [optional: area to focus on]%%
Onboard this repo: %%ARG%%

This is a **one-time** pass. Its whole point is that `/propose`, `/design`, and
`/implement` afterward read the context file instead of re-scanning the repo
every time. Do not repeat this skim on every future command.

1. Find the context file — `AGENTS.md`, or `CLAUDE.md` if this repo has no
   separate `AGENTS.md`. If it has no unfilled `<!-- TODO -->`/placeholder
   sections left, stop and ask before overwriting anything.
2. Check for a code knowledge graph. If a `codegraph` MCP server is already
   connected (an `mcp__codegraph__*` tool is in your tool list), skip
   straight to step 3 and call its `generate_report` tool for the module map
   alongside your skim. Otherwise ask: *"Want me to add the code knowledge
   graph MCP server (CodeGraphContext,
   https://github.com/CodeGraphContext/CodeGraphContext, MIT, local AST
   parsing — nothing leaves this machine) and index this repo before I
   skim?"* Skip to step 3 on no, or if this is a small/single-file repo where
   a graph adds nothing.
   - If yes, run `asdlc mcp add codegraph`. This writes the server into
     `.mcp.json` but does not connect it in the current session — tell the
     user their agent tool needs a reconnect/restart before its tools show
     up, and stop here.
   - Once connected, call `cgc mcp tools` (or list your own tools) and go by
     their actual names, not by memory — tool names and flags drift from
     docs. Call `add_code_to_graph` against `.` to index the repo — it
     returns a job ID; poll `check_job_status` until it finishes (a large or
     unfamiliar codebase can take a while).
   - Call `generate_report` for the module map instead of re-deriving it by
     hand.
   - Ask the user: *"Want to open the graph visualizer in your browser?"* If
     yes, run `cgc visualize` as a background process — it starts a local
     server (default `http://127.0.0.1:8000`) and does not return control on
     its own — and only give them that URL once it's actually listening; a
     link to a port nothing answers on yet is worse than no link. `/codegraph`
     re-runs this index-then-visualize pair later without repeating the rest
     of onboarding.
   - Note in the context file that the graph exists via the `codegraph` MCP
     server and how to refresh it (`add_code_to_graph` again, or `cgc hook
     install` so Git hooks keep it in sync automatically — unlike a one-off
     build, this one can stay current going forward).
3. Skim, don't exhaustively read: package manifests (`package.json`,
   `pyproject.toml`, `go.mod`, ...), the top-level directory layout, README,
   CI config, and existing tests. Pull real versions and real commands from
   these — do not guess or invent plausible-sounding ones. Lean on
   the `codegraph` MCP server's `generate_report` output for the module map
   if step 2 connected one, instead of re-deriving it by hand.
4. Fill in the context file itself — keep it short, this is always-loaded
   context, not documentation:
   - **What this is** — one paragraph, grounded in the README/manifest.
   - **Stack (pinned)** — actual pinned versions from the manifest/lockfile.
   - **Commands** — the real install/test/lint/build commands, read from
     `package.json` scripts, a Makefile, CI config, etc.
   - **Conventions** — 2-4 bullets, the most load-bearing ones only. Each
     needs two or more real examples you can point to; one is a coincidence.
   - **Do not touch** — generated code, vendored dirs, anything the repo's own
     `.gitignore`/CI treats as off-limits.
5. Deeper architecture doesn't belong in the context file — check
   `.asdlc/policy.yaml`'s `sdd:` field first, then do exactly one of these:
   - `sdd: none` or `openspec` — write `docs/architecture.md` yourself:
     module map (what each top-level dir is for), key domain concepts, how
     subsystems talk to each other, and the rationale behind the Conventions
     above. Add one line under Conventions pointing at it — a plain link, not
     an `@import`; it should load on demand, not every session.
   - `sdd: speckit` — Spec Kit already owns this via `/speckit-constitution`.
     Don't write a competing doc. If it hasn't been run yet, say so and stop
     — don't do its job for it.
   - `sdd: bmad` — BMAD's own installed workflow generates the PRD and
     architecture docs. Same rule: point at running that if it hasn't
     happened yet, don't duplicate it.
   - `sdd: kiro` — this repo already has `.kiro/steering/{product,tech,
     structure}.md`, scaffolded by `asdlc init` for exactly this purpose.
     Fill those in instead of creating a new file.
6. Uncertain about something? Leave a `<!-- CONFIRM: ... -->` marker for a
   human instead of guessing. A wrong fact here is worse than a blank section
   — every future command trusts this file.
7. If clear feature-boundary directories exist, propose `capabilities:`
   entries for `.asdlc/policy.yaml`'s drift gate — **show the diff and ask**,
   never write policy.yaml yourself.
8. Do not touch `proposal.md`/`spec.md`/`design.md`/`tasks.md` or any change
   folder. This command is about context, not a change.
9. Last step, once everything above is done: ask *"Want me to generate an
   interactive architecture diagram of this repo now (via the Archify
   skill, tt-a1i/archify, MIT)?"*
   - If yes and the `archify` skill isn't already installed, run
     `npx skills add tt-a1i/archify -g` (or without `-g` for a project-local
     install) yourself — this is the one place that installs it, no need to
     ask the user to run it. Skills are plain files, not a registered tool,
     so you can read the installed `SKILL.md` and follow it right away with
     no restart needed.
   - Then produce one bounded `architecture` diagram of the runtime
     components discovered in this skim — 8–12 core components, one primary
     path, external dependencies, trust boundaries. Link it from
     `docs/architecture.md` if step 5 wrote one.
   - If no, tell the user they can generate it any time later by running
     `/diagram`.
