#!/usr/bin/env bash
# The test that should have existed. Builds a wheel, installs it into a clean
# venv with the source tree OUT of reach, and drives the CLI from there.
#
# Running from a source checkout hides missing package-data completely: every
# asset read resolves against the repo instead of site-packages. The only way to
# catch it is to install and cd somewhere else. That is exactly how 0.1.0 shipped
# broken.
set -uo pipefail

STD="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD=$(mktemp -d); VENV="$BUILD/venv"; REPO="$BUILD/repo"
trap 'rm -rf "$BUILD"' EXIT
PASS=0; FAIL=0

check() { # description  test-expression...
  local d="$1"; shift
  if "$@" >/dev/null 2>&1; then echo "  ok   $d"; PASS=$((PASS+1))
  else echo "  FAIL $d"; FAIL=$((FAIL+1)); fi
}

echo "packaging self-test"

python3 -m venv "$VENV"
"$VENV/bin/pip" install -q --upgrade pip build >/dev/null 2>&1
( cd "$STD" && "$VENV/bin/python" -m build --wheel --outdir "$BUILD/dist" ) >/dev/null 2>&1 \
  || { echo "  FAIL wheel build"; exit 1; }
echo "  ok   wheel builds"

"$VENV/bin/pip" install -q "$BUILD"/dist/*.whl >/dev/null 2>&1 \
  || { echo "  FAIL wheel installs"; exit 1; }
echo "  ok   wheel installs"

# Every asset the CLI reads at runtime must exist inside site-packages.
SITE=$("$VENV/bin/python" -c "import asdlc,os;print(os.path.dirname(asdlc.__file__))")
for f in \
  "gates/policy.yaml" \
  "gates/presets/strict.yaml" \
  "assets/templates/AGENTS.md.tpl" \
  "assets/templates/adr.md" \
  "assets/templates/change/spec.md" \
  "assets/skills/spec-authoring/SKILL.md" \
  "assets/commands/propose.md" \
  "assets/commands/onboard.md" \
  "assets/templates/kiro/product.md.tpl" \
  "assets/ci/github/agentic-sdlc.yml" \
  "assets/ci/gitlab/agentic-sdlc.yml" ; do
  check "packaged: $f" test -f "$SITE/$f"
done

# Drive the installed console script from a repo far away from the source tree.
mkdir -p "$REPO"; cd "$REPO"
git init -q; git config user.email t@t.io; git config user.name t
mkdir -p src; echo "#" > README.md; git add -A; git commit -qm init; git branch -M main

check "asdlc init (claude-code, github)" env NO_COLOR=1 "$VENV/bin/asdlc" init --tools claude-code --ci github
for f in .asdlc/policy.yaml CLAUDE.md \
         .claude/commands/propose.md .claude/commands/onboard.md \
         .claude/skills/spec-authoring/SKILL.md \
         .github/workflows/agentic-sdlc.yml ; do
  check "init produced: $f" test -e "$REPO/$f"
done
check "next-step message recommends /onboard" \
  bash -c "'$VENV/bin/asdlc' init --tools claude-code 2>&1 | grep -q '/onboard'"
check "claude-code alone: no AGENTS.md hub (nothing else reads it)" test ! -e "$REPO/AGENTS.md"
check "claude-code alone: CLAUDE.md has real content, not an import" \
  grep -q "workflow you must follow" "$REPO/CLAUDE.md"
check "default --sdd: workflow note doesn't namedrop unused front-ends" \
  bash -c "! grep -qE 'OpenSpec|Spec Kit|BMAD|Kiro' '$REPO/CLAUDE.md'"
check "doctor checks CLAUDE.md, not a false-negative AGENTS.md, when claude-code is alone" \
  bash -c "cd '$REPO' && NO_COLOR=1 '$VENV/bin/asdlc' doctor 2>&1 | grep -q 'yes  CLAUDE.md'"
check ".asdlc/skills is not created" test ! -e "$REPO/.asdlc/skills"
check "default --sdd keeps openspec/changes in policy.yaml" \
  grep -q "changes: \"openspec/changes\"" "$REPO/.asdlc/policy.yaml"
check "default --sdd: propose.md references openspec/, not .asdlc/changes" \
  grep -q "openspec/changes" "$REPO/.claude/commands/propose.md"
check "default --sdd keeps spec-present enabled" \
  bash -c "grep -A1 'spec-present:' '$REPO/.asdlc/policy.yaml' | grep -q 'enabled: true'"

check "asdlc init --tools claude-code codex copilot cursor generic --sdd kiro" env NO_COLOR=1 "$VENV/bin/asdlc" init --tools claude-code codex copilot cursor generic --ci gitlab --sdd kiro --force
for f in .codex/prompts/verify.md .github/prompts/verify.prompt.md \
         .cursor/commands/verify.md docs/agent-workflow.md .agentic-sdlc.gitlab-ci.yml ; do
  check "init produced: $f" test -e "$REPO/$f"
done
check "claude-code + codex: AGENTS.md hub created (codex reads it natively)" test -f "$REPO/AGENTS.md"
check "claude-code + codex: CLAUDE.md is a pointer, not inlined" \
  grep -q "@AGENTS.md" "$REPO/CLAUDE.md"
check "--sdd kiro: workflow note names Kiro specifically" \
  grep -q "independent of Kiro" "$REPO/AGENTS.md"
check "init produced codex skills" test -f "$REPO/.codex/skills/spec-authoring/SKILL.md"
check "init produced copilot skills" test -f "$REPO/.github/skills/spec-authoring/SKILL.md"
check "init produced cursor skills" test -f "$REPO/.cursor/skills/spec-authoring/SKILL.md"
check "init produced kiro steering" test -f "$REPO/.kiro/steering/product.md"
check "kiro steering has no unsubstituted tokens" \
  bash -c "! grep -q '{{PROJECT}}' '$REPO/.kiro/steering/product.md'"
check "--sdd kiro switches policy.yaml to .asdlc/changes" \
  grep -q "changes: \"\.asdlc/changes\"" "$REPO/.asdlc/policy.yaml"
check "--sdd kiro: propose.md references .asdlc/, not openspec/" \
  grep -q "\.asdlc/changes" "$REPO/.codex/prompts/propose.md"
check "--sdd kiro: kiro steering references .asdlc/changes" \
  grep -q "\.asdlc/changes" "$REPO/.kiro/steering/structure.md"
for chk in spec-present spec-lint traceability spec-drift; do
  check "--sdd kiro disables $chk" \
    bash -c "grep -A1 '$chk:' '$REPO/.asdlc/policy.yaml' | grep -q 'enabled: false'"
done
for chk in coverage-delta security-scan human-approval; do
  check "--sdd kiro keeps $chk enabled" \
    bash -c "grep -A1 '$chk:' '$REPO/.asdlc/policy.yaml' | grep -q 'enabled: true'"
done

# .asdlc/policy.yaml now points at .asdlc/changes (the --sdd kiro call above
# switched it with --force) — asdlc new must follow the CURRENT policy, not
# wherever the very first init call happened to put things.
check "asdlc new" env NO_COLOR=1 "$VENV/bin/asdlc" new demo-change
check "new produced spec.md" test -f "$REPO/.asdlc/changes/demo-change/spec.md"
check "asdlc doctor" env NO_COLOR=1 "$VENV/bin/asdlc" doctor
check "asdlc verify runs on a clean repo" env NO_COLOR=1 "$VENV/bin/asdlc" verify --base main --stage code
check "python -m asdlc works" env NO_COLOR=1 "$VENV/bin/python" -m asdlc doctor

echo
echo "passed=$PASS failed=$FAIL"
[ "$FAIL" -eq 0 ]
