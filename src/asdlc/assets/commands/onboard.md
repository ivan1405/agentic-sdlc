%%DESC: Skim the codebase once and fill in the context file with real project facts%%
%%HINT: [optional: area to focus on]%%
Onboard this repo: %%ARG%%

This is a **one-time** pass. Its whole point is that `/propose`, `/design`, and
`/implement` afterward read the context file instead of re-scanning the repo
every time. Do not repeat this skim on every future command.

1. Find the context file — `AGENTS.md`, or `CLAUDE.md` if this repo has no
   separate `AGENTS.md`. If it has no unfilled `<!-- TODO -->`/placeholder
   sections left, stop and ask before overwriting anything.
2. Skim, don't exhaustively read: package manifests (`package.json`,
   `pyproject.toml`, `go.mod`, ...), the top-level directory layout, README,
   CI config, and existing tests. Pull real versions and real commands from
   these — do not guess or invent plausible-sounding ones.
3. Fill in the context file itself — keep it short, this is always-loaded
   context, not documentation:
   - **What this is** — one paragraph, grounded in the README/manifest.
   - **Stack (pinned)** — actual pinned versions from the manifest/lockfile.
   - **Commands** — the real install/test/lint/build commands, read from
     `package.json` scripts, a Makefile, CI config, etc.
   - **Conventions** — 2-4 bullets, the most load-bearing ones only. Each
     needs two or more real examples you can point to; one is a coincidence.
   - **Do not touch** — generated code, vendored dirs, anything the repo's own
     `.gitignore`/CI treats as off-limits.
4. Deeper architecture doesn't belong in the context file — check
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
5. Uncertain about something? Leave a `<!-- CONFIRM: ... -->` marker for a
   human instead of guessing. A wrong fact here is worse than a blank section
   — every future command trusts this file.
6. If clear feature-boundary directories exist, propose `capabilities:`
   entries for `.asdlc/policy.yaml`'s drift gate — **show the diff and ask**,
   never write policy.yaml yourself.
7. Do not touch `proposal.md`/`spec.md`/`design.md`/`tasks.md` or any change
   folder. This command is about context, not a change.
