# CI/CD & release

<!-- summary: Reproducible builds, automated pipeline, progressive delivery with a rollback, no manual prod steps. -->
<!-- tier: domain -->
<!-- category: DevOps & Platform -->

Releasing should be boring. If a deploy is a tense manual ritual, that's a
process bug — automate it until it's a non-event you can do on a Friday.

**One reproducible build, promoted.** Build the artifact once; promote the same
artifact through environments (test → staging → prod). Don't rebuild per
environment — that's how "works in staging" stops meaning anything. Pin
dependencies so a build is reproducible.

**The pipeline is the gate.** Lint, tests, and `asdlc verify` run in CI on every
change, and a red pipeline blocks merge. What CI checks is what "done" means; a
check that only runs on someone's laptop doesn't exist.

**No manual production steps.** Deploys are scripted and repeatable — no hand-run
commands, no clicking through a console. A human may approve; a human should not
execute.

**Progressive delivery + a tested rollback.** Roll out gradually (canary /
blue-green / staged) and watch the telemetry. Every deploy has a rollback that
has actually been exercised — an untested rollback is a hope. Decouple deploy
from release with feature flags so shipping code and enabling it are separate
decisions.

**Migrations are forward-safe.** Schema changes are backward-compatible with the
currently-running version (expand, migrate, then contract) so a rollback doesn't
strand the database.

**Fast feedback.** Keep the pipeline quick enough that people wait for it. A
30-minute pipeline gets bypassed; a 5-minute one gets trusted.
