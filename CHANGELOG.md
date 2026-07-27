# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/). Because
clients pin a tag of this repo in CI, the PATCH / MINOR / MAJOR distinction is
load-bearing — see [CONTRIBUTING.md](CONTRIBUTING.md#versioning). In short: a
release is MAJOR if it can turn a previously-green PR red.

## [Unreleased]

### Added
- `LICENSE` (Apache-2.0) and packaging metadata in `pyproject.toml` (authors,
  readme, keywords, trove classifiers including the license, and project URLs),
  so the project is installable and redistributable as a public open-source
  package.
- `CONTRIBUTING.md` and this `CHANGELOG.md`, including an explicit versioning
  policy tied to the "can this turn a green PR red?" rule.

### Changed
- Extracted the interactive wizard's terminal/menu machinery and ANSI colour
  constants from `cli.py` into a new `asdlc.tui` module, keeping `cli.py` under
  the project's own 800-line file-size rule. Behaviour is unchanged; the
  catalog-aware `_run_wizard` orchestration stays in `cli.py`.

## [0.2.0]

### Added
- MCP catalog and `asdlc mcp {list,add,remove}` for managing a repo's
  `.mcp.json` against a curated set of common servers (Atlassian, GitHub,
  Slack), with remote/OAuth entries committed without secrets and self-hosted
  entries wired through `${VAR}` references.
- Six portable role definitions (technical-leader, solutions-architect,
  frontend-dev, backend-dev, qa-engineer, security-engineer), rendered per tool
  — Codex as native TOML, the others as Markdown-with-frontmatter.
- SDD front-end installers (`--sdd openspec|speckit|bmad|kiro`) that shell out
  to each vendor's own installer, and disable asdlc's spec-shape gates that a
  front-end's native artifacts wouldn't satisfy.
- Interactive `asdlc init` setup wizard (arrow-key menus with a type-a-number
  fallback) when run with no flags at a terminal.

### Fixed
- Asset payload (`templates/`, `skills/`, `commands/`, `agents/`, `ci/`) is now
  declared in `package-data` and ships inside the wheel; `tests/test_packaging.sh`
  builds, installs, and drives the CLI from outside the source tree to prove it.

## [0.1.0]

### Added
- Initial release: `asdlc` CLI (`init`, `new`, `verify`, `doctor`), the
  seven-gate suite (`spec-present`, `spec-lint`, `traceability`, `spec-drift`,
  `coverage-delta`, `security-scan`, `human-approval`), the four-file artifact
  contract, per-tool command adapters, GitHub/GitLab CI templates, and a
  zero-dependency YAML fallback parser for the policy file.

[Unreleased]: https://github.com/ivan1405/agentic-sdlc/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/ivan1405/agentic-sdlc/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/ivan1405/agentic-sdlc/releases/tag/v0.1.0
