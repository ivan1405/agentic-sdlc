%%DESC: Turn a Jira ticket into a drafted change (SDD-aware); tech-lead validates and either drafts or asks for clarification%%
%%HINT: <ticket-key>%%
Import a Jira ticket into a change: %%ARG%%

Best suited to the **technical-leader** agent, if your tool supports subagent
delegation — this is a scoping/judgement task: read the story, decide whether
it's implementable, and draft (or push back) accordingly. It does **not** write
code.

Preconditions — verify yourself and refuse if unmet:
- `.mcp.json`'s `mcpServers` has an `atlassian` or `atlassian-self-hosted`
  entry. Without it there's no way to read the ticket or comment back — stop and
  say so (`asdlc mcp add atlassian`). Exact Atlassian MCP tool names vary by
  version; treat your actual tool list as ground truth over the wording here.

Steps:
1. **Read the ticket `%%ARG%%`** via the Atlassian MCP tools — summary,
   description, acceptance criteria, and existing comments. Also read
   `%%CONTEXT_FILE%%` and `.asdlc/policy.yaml`.
2. **Detect the SDD front-end** from `.asdlc/policy.yaml`'s `sdd` field
   (`none` / `openspec` / `speckit` / `bmad` / `kiro`). It decides the shape you
   produce in step 6.
3. **Validate sufficiency** using the **spec-authoring** skill
   (`.asdlc/skills/spec-authoring/SKILL.md` — read it now). The bar: from this
   ticket, could you write testable requirements — stable REQ- IDs, SHALL
   statements, Given/When/Then scenarios **including a failure path** — plus a
   clear in/out scope and acceptance criteria, and can you tell whether it
   touches a sensitive surface (auth, payments, PII, a migration, a public API
   contract, infra)? Do not invent answers to fill gaps.
4. **If NOT sufficient — ask, don't guess.** Post a Jira comment on `%%ARG%%`
   (Atlassian MCP) listing the *specific* missing information as concrete
   questions (map each to the spec-authoring interview point it's missing).
   Do **not** create a change folder. Stop here.
5. **If sufficient — create the change** in the front-end's own shape, with a
   change-id derived from the ticket: `<ticket-key lowercased>-<short-slug-of-summary>`.
   Record the ticket key so `/implement` can sync it back later.
   - **`sdd: none`** → run `asdlc new <change-id>`, then fill
     `%%CHANGES_DIR%%/<change-id>/` — `proposal.md` (Problem, Outcome, Scope
     in/out, and the ticket key in the `Ticket:` field), `spec.md` (REQ- IDs,
     SHALL, Given/When/Then incl. failure paths, the `Capability:` line),
     `design.md`, and `tasks.md` (each task tagged with its REQ- ID). Run
     `asdlc verify --stage spec` and fix what it reports.
   - **`sdd: openspec`** → run `openspec new change <change-id>` and fill
     OpenSpec's own artifacts from the ticket. Implementation later runs through
     OpenSpec's own apply command, not asdlc's `/implement`.
   - **`sdd: speckit` / `bmad` / `kiro`** → use that tool's own create flow
     (e.g. Spec Kit's specify command, BMAD's PRD/story workflow, Kiro's Spec
     mode) and fill its artifacts from the ticket.
6. **Approval — whenever the change has a `design.md`.** That's always true
   for `sdd: none`; also true for `sdd: openspec` when OpenSpec's own flow
   produced one (OpenSpec treats it as optional, but when present it's a real
   `design.md` at the same path the gates check) and for `sdd: kiro`'s native
   Spec mode. `sdd: speckit` (`plan.md`) and `sdd: bmad` (`PRD.md`/
   `architecture.md`) never produce a `design.md` — skip this step for them,
   there's nothing to sign.

   Read `jira_import.auto_approve` from `.asdlc/policy.yaml` (default `true`).
   - **`auto_approve: true`** — once the change is complete (`sdd: none`: once
     `asdlc verify --stage spec` is green; other shapes: once step 3's
     sufficiency check is satisfied), write an `Approved-by: <name> <email>`
     trailer into that `design.md`, using this repo's `git config user.name` /
     `user.email`.
   - **`auto_approve: false`** — do **not** sign. Post a "spec ready for your
     approval" comment on the Jira ticket and stop; a human signs `design.md`
     before implementation (`/implement` for `sdd: none`, the front-end's own
     apply flow otherwise).

   > ⚠️ **`auto_approve: true` deliberately breaks the standard's accountability
   > boundary.** `standard/03-definition-of-done.md` lists "write its own
   > `Approved-by:` line" as something an agent must **never** do — a human is
   > supposed to sign `design.md` before implementation. Auto-signing lets a
   > well-specified ticket flow to implementation unattended, which means the
   > `human-approval` gate passes on agent authority, **including on sensitive
   > diffs**. It is on by default per engagement choice; flip
   > `jira_import.auto_approve` to `false` in `.asdlc/policy.yaml` to restore the
   > human-in-the-loop behaviour.
7. **Report on the ticket.** Post a Jira comment with the outcome: the change
   path, whether it was auto-approved, and the next step — `/implement
   <change-id>` for `sdd: none`, or the front-end's own apply flow otherwise.
   If (and only if) the ticket has a real transition meaning "in progress" or
   "ready for review", move it there; never guess a status that isn't an actual
   transition on that ticket.
8. **Stop.** This command never writes implementation code, never opens a PR,
   and never merges. It creates (and, for `sdd: none`, may approve) the change;
   implementation is a separate step.
