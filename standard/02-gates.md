# 02 — The gates

`asdlc verify` is the standard. Everything else in this repo is scaffolding that
helps agents pass it. It runs identically on a laptop and in CI — if those two
diverge, you have a ritual, not a gate.

Design constraints, non-negotiable:

1. **Zero dependencies.** These run in whatever CI the client already has. No pip
   install step to argue with a client's security team about.
2. **Tool-blind.** A gate inspects git and files. It never asks who wrote the code,
   and it cannot be told. That is what makes the standard agnostic in practice
   rather than in the pitch deck.
3. **Fail closed.** A crashing check fails the build. Gates that fail open are theatre.
4. **Same command, both sides.** `asdlc verify` locally = `asdlc verify` in CI.

## Two stages

`--stage spec` runs in ~10 seconds on every push and fails before anyone burns a
runner — or a model — on unspecified work. `--stage code` runs the rest after tests.
Fast feedback on the cheapest fix.

## The checks

### spec-present (`--stage code`)
Production code changed with no change folder → block. Load-bearing: everything
downstream assumes the spec exists. **Tune:** `source_globs` defines production
code; `exempt_globs` is the escape hatch. Keep that list short and boring — it is
the crack the whole standard leaks out of.

### spec-lint (`--stage spec`)
Requirements need a stable `REQ-` ID, a SHALL statement, and Given/When/Then
scenarios. Also catches unfilled template placeholders (`TODO`, `{{VAR}}`,
`<angle placeholders>`), because an agent handed a template will produce a
plausible-looking document with the scaffolding still in it. **Tune:**
`min_scenarios_per_requirement` (2 on strict — forces a failure path).

### traceability (`--stage code`)
`spec.md` REQ → `tasks.md` REQ → a test naming that REQ. Mechanical, cheap, and the
reason QA stops being vibes. Agents comply readily once it's a hard gate; humans
skip it forever. **Tune:** `test_globs` per language; `require_test_reference: false`
for a first brownfield pass.

### spec-drift (`--stage code`)
Code under a mapped capability moved; the spec didn't → block. **This is the gate
that decides whether the standard survives.** At month six, specs are either the
source of truth or they're lies that agents read and act on; there is no stable
middle. Every SDD framework leaves reconciliation manual, and manual means never.
**Tune:** `capabilities` map (start with 3–5, not 40); `mode: warn` on legacy repos,
ratchet to `fail` after a quarter.

### coverage-delta (`--stage code`)
Changed files below threshold → block. Deliberately scoped to the diff: repo-wide
thresholds are a ratchet nobody can move on a brownfield codebase, so they get
disabled in week two. Reads Cobertura XML — one format, every language (pytest-cov,
jacoco, nyc, gocover-cobertura). **Tune:** `min_changed_file_coverage` (80 balanced,
90 strict, off for light). Note the number is gameable by design; the `test-strategy`
skill exists to make it mean something.

### security-scan (`--stage code`)
Regex secrets sweep (zero-dependency floor) plus whatever scanners the client owns
— semgrep, trivy, gitleaks, snyk, npm audit. We do not ship a scanner. We ship the
contract that one runs and that its exit code blocks the merge. False positives get
`# asdlc:allow-secret` plus a justification, in the diff, where review can see it —
never a silent policy edit. **Tune:** `scanners: [...]`.

### human-approval (`--stage code`)
Sensitive diffs (architecture, migrations, authz, money, public API, infra) need a
named `Approved-by:` trailer in `design.md` and, optionally, N PR approvals. Not all
diffs are equal: this is the gate that lets the rest of the pipeline run fast,
because it names precisely where it must not. It's also the one that makes the
whole thing sellable to a client's risk function. **Tune:** `sensitive` map,
`approver_domains`, `min_pr_reviews`.

## Presets

`gates/presets/{light,strict}.yaml` — copy over `.asdlc/policy.yaml` and tune.
Match the profile to the blast radius, not to the client's self-image. Everyone
believes they are strict.

## Adding a gate

1. `gates/checks/<name>.py` exposing `run(ctx) -> CheckResult`.
2. Register in `gates/checks/__init__.py: ALL_CHECKS`.
3. Add a policy block (default enabled, tunable).
4. **Add a case to `tests/test_gates.sh` that proves it fails.**

Step 4 is not optional. A gate nobody has watched fail is decoration.

## When a gate is wrong

Sometimes it is. The response is a PR to *this* repo with the failing case added to
the test suite — not an exempt glob in a client's policy. Exemptions are how a
standard dies: quietly, one reasonable exception at a time.

## Trusting this suite

Two claims in this document are the kind that quietly rot:

**"Zero dependencies."** Every developer machine has PyYAML, so the bundled
fallback parser is the least-run code in the repo — and it is what actually runs
in a clean CI venv. `tests/test_policy_parser.py` asserts it agrees with PyYAML on
every file we ship. It found a real crash the first time it ran.

**"`asdlc init` works."** It always works from a source checkout, because every
asset read resolves against the repo. It only breaks once installed, in a client's
terminal. `tests/test_packaging.sh` builds a wheel, installs it into a clean venv,
and drives the CLI from a directory nowhere near the source.

Both suites exist because both claims were false in v0.1.0 and the existing tests
were structurally incapable of noticing.
