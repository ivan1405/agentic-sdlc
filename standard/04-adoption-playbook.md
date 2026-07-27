# 04 — Adoption playbook

## The failure mode to avoid

Announce a firm-wide AI SDLC standard. Roll it out to twelve teams. Discover in
month two that the gates don't fit the legacy monolith, grant exemptions, and by
month four have a wiki page nobody reads and twelve teams doing what they were
doing before, plus resentment.

The alternative is boring: two pilots, six weeks, real numbers.

## Weeks 1–6: two pilots

Pick **two engagements with different toolchains**. That is the point — one on
Claude Code, one on Codex or Copilot. Same gates, same artifacts, same skills.
If it only works on the tool you like, you don't have a standard, you have a
preference.

Prefer one brownfield repo with real users. A greenfield pilot proves nothing;
every framework demos beautifully on an empty directory.

Setup (half a day per repo):

```bash
asdlc init --tools <what the client has> --ci <what the client has>
# fill in AGENTS.md — this is 80% of the value and takes 2 hours
# map 3-5 capabilities in .asdlc/policy.yaml. Not 40.
# set spec-drift: warn, coverage-delta: enabled but modest
```

Then run normally for six weeks. Do not add gates mid-pilot.

## Measure these four

| Metric | Where from | Why |
|---|---|---|
| PR lead time (open → merge) | git/GitHub API | The claim your boss will make. Test it. |
| Review rework rate (% PRs needing >1 round) | PR reviews | The bottleneck actually moved here. |
| Escaped defects (bugs found post-merge / change) | tickets | The number that decides if this is safe. |
| % PRs with a current spec | `asdlc verify` history | Whether the standard is real or performed. |

`asdlc report` computes the two git-derivable ones — PR lead time (branch age at
merge) and % of merged PRs that carried a spec — plus merge throughput and, with
`--results-dir`, a gate pass-rate from archived `asdlc verify --json` runs. It
makes **no API call** (the zero-dependency rule holds), so review rework rate and
escaped defects it reports as needing the PR/issue API — wire those from your CI
(the `gh api`/`glab` step that already counts approvals is the place) or read them
off GitHub/GitLab directly.

Get a **two-week baseline before you start**, or you will be arguing from vibes in
the readout, and vibes lose to whoever has a slide.

Expect lead time to get *worse* in weeks 1–2. Say so up front, in writing, to the
boss. Specs are a real cost paid before the benefit; a leader who hasn't been warned
reads the week-2 dip as failure and kills it.

## The ratchet

- **Month 1:** `spec-drift: warn`, traceability without test refs, coverage off.
  Goal: the team stops noticing the workflow.
- **Month 2:** coverage-delta on at 70. Traceability test refs on.
- **Month 3:** `spec-drift: fail`. Coverage to 80. Capability map grows only along
  the paths the team actually worked.
- **Quarter 2:** strict preset on the engagements that warrant it.

Never back-fill specs for the whole system. You'll produce a beautiful fiction, in
week three, that nobody maintains. The spec grows where the work happens.

## Anti-patterns

**Standardising the framework instead of the contract.** OpenSpec vs Spec Kit is a
per-engagement choice, not a firm-wide religion. If the answer changes when the
client's procurement changes, it was never a standard.

**A pool of agents as the goal.** Generation was never the bottleneck. Faster PRs
than humans can trust just moves the queue and adds an outsourced review burden
nobody costed.

**Gates with an override.** The exemption list is the standard's actual content.
Every reasonable exception makes the next one easier.

**Skipping the design review to go faster.** It's the only cheap review in the
process. Ten minutes there or a day after 500 lines exist.

**Buying the token bill before the process.** A framework that simulates twelve
agent roles is not twelve times better than one that stops you shipping unspecified
code. Start at the floor and add ceremony when a gate is failing for real reasons.

**Selling agnosticism you haven't tested.** Run both pilots on different tools
before the word "agnostic" appears in a client deck.

## Readout to the boss

One page. Baseline vs pilot on the four metrics, both toolchains side by side, and
an honest section on what got worse. Then the ask: which engagements adopt next,
and who owns this repo. Because the last failure mode is a standard with no
maintainer — six months later it's a folder of stale templates and everyone quietly
went back to pasting prompts.

## Positioning question, worth settling early

Is this a **reusable accelerator you resell** (invest in the CLI, the skill packs,
the presets — it's a product with a roadmap and an owner) or a **methodology you
consult on** (invest in the templates, the gates, and training — it's IP that makes
your people faster)? Both are defensible. They pull in different directions on how
much you build, and deciding it at month six is expensive.
