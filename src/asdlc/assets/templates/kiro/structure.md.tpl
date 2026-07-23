<!--
Kiro foundation steering file: project structure. Helps generated code land
in the right place instead of a plausible-looking wrong one.
-->

# Project structure — {{PROJECT}}

## Layout
<!-- top-level directories and what lives in each -->

## Naming conventions
<!-- files, modules, tests — be specific: "use X, never Y" beats "prefer X" -->

## Import patterns
<!-- absolute vs relative, barrel files or not, path aliases -->

## The workflow you must follow
This repo uses a spec-first, gated workflow (see AGENTS.md and `asdlc verify`
if this repo has adopted the agentic-sdlc standard). Do not improvise around
it: no code without a change folder under `{{CHANGES_DIR}}/<change-id>/`,
and `asdlc verify` must pass before a PR opens.
