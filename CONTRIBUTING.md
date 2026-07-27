# Contributing

Thanks for helping. This repo is a *standard*, not just a tool — clients pin a
tag of it in their CI (`pip install "asdlc @ git+...@vX.Y.Z"`), so a change here
can move under someone else's feet. Read this before opening a PR.

## Dev setup

Uses [uv](https://astral.sh/uv). No runtime dependencies — the gates run in
whatever CI a client already has — so the only thing to install is the test
tooling.

```bash
uv venv
uv pip install pytest          # the only dev dependency
```

Run the CLI straight from the source tree without installing:

```bash
PYTHONPATH=src python3 -m asdlc --help
```

## Running the tests

The suite is the point. "A gate you have never seen fail is not a gate" — same
goes for a claim you have never tested.

```bash
# Fast, mandatory — must pass on every PR:
bash tests/test_gates.sh                                  # 9 agent mistakes, each blocked by the right gate
bash tests/test_packaging.sh                              # builds a wheel, installs it clean, drives the CLI from outside the tree
PYTHONPATH=src python3 -m pytest tests/test_policy_parser.py tests/test_wizard.py -q

# Opt-in — needs npx/uv + network, not part of the mandatory suite:
bash tests/test_sdd.sh
```

CI runs the mandatory suite on both Linux and macOS. If you touch anything that
shells out (`git`, `sed`, subprocess), test on both — GNU and BSD userlands
diverge, and a Linux-only test is a test the maintainer can't run locally.

## Conventions

- **The context contract is `AGENTS.md`.** Commands and constraints live there;
  read it before changing behaviour.
- **Small files, small functions.** 800 lines per file is the ceiling — the
  wizard's terminal machinery lives in `tui.py` for exactly this reason. If a
  file crosses it, split by cohesion, not by line count.
- **The gates have zero dependencies, on purpose.** Do not add a runtime
  dependency to `asdlc` itself. A dev/test dependency is fine; a runtime one is
  a conversation with every client's security team.
- **Assets ship inside the package.** Anything the CLI reads at runtime must be
  listed in `pyproject.toml`'s `package-data`, or it won't survive `pip
  install`. `tests/test_packaging.sh` enforces this — if it's not in the wheel,
  it does not exist.
- **Adding a new agent tool** is a data change, not a methodology change: an
  entry in `ADAPTER_TARGETS` (cli.py) plus one in the `TOOLS` tables of
  `commands.py` and `agents.py`. Only add tool/model fields where you have
  verified the target's schema against a real example — leave them out rather
  than guess (see the note at the top of `agents.py`, and record what you
  verified in [docs/adapter-verification.md](docs/adapter-verification.md)).
  `tests/test_adapters.py` checks every rendered file parses (TOML/YAML) and
  pins the exact bytes with golden snapshots — regenerate them deliberately
  with `ASDLC_UPDATE_GOLDEN=1` and review the diff.

## Versioning

[Semantic Versioning](https://semver.org/). Because clients pin a tag:

- **PATCH** — bug fix in a gate or renderer; no change to what passes or fails.
- **MINOR** — a new gate defaulting to off, a new tool/SDD adapter, new
  templates. A client who upgrades and re-runs sees no *new* failures.
- **MAJOR** — anything that can turn a previously-green PR red: a gate now on by
  default, a stricter default threshold, a renamed policy key, a changed
  artifact contract. These are the changes that move under a client's feet;
  call them out loudly in the changelog.

Record every change in [CHANGELOG.md](CHANGELOG.md) under `[Unreleased]` as you
go; the release step just adds the version and date.

## Pull requests

This repo follows its own workflow. Where practical, dogfood it: a behavioural
change gets a change folder and a spec, and `asdlc verify` should be green
before you ask for review. State the problem, the outcome, and — most
importantly — whether the change is PATCH/MINOR/MAJOR by the rule above.
