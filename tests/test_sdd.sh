#!/usr/bin/env bash
# Opt-in. Exercises `asdlc init --sdd {openspec,speckit,bmad}` against the real
# vendor installers (npx / uv, real network access). NOT part of test_gates.sh
# or test_packaging.sh — asdlc itself has zero runtime dependencies, and these
# three do, so requiring them here would break that on any machine without
# Node/uv installed. Skips each case gracefully instead of failing when its
# binary isn't on PATH.
#
# This is also the check that validates (or corrects) sdd.py's exact CLI
# flags against whatever version of each installer is actually out there —
# their docs disagreed with each other during the research for this feature.
# If a case here fails on an obviously-wrong flag, fix src/asdlc/sdd.py, not
# this test.
#
#   bash tests/test_sdd.sh
set -uo pipefail

STD="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="$STD/src"
ASDLC="python3 -m asdlc"
PASS=0; FAIL=0; SKIP=0

check() { # description  test-expression...
  local d="$1"; shift
  if "$@" >/dev/null 2>&1; then echo "  ok   $d"; PASS=$((PASS+1))
  else echo "  FAIL $d"; FAIL=$((FAIL+1)); fi
}

skip_unless() { # binary description
  command -v "$1" >/dev/null 2>&1 && return 0
  echo "  skip $2 (no '$1' on PATH)"
  SKIP=$((SKIP+1))
  return 1
}

setup() {
  WORK=$(mktemp -d); cd "$WORK"
  git init -q; git config user.email t@t.io; git config user.name t
  echo "#" > README.md; git add -A; git commit -qm init >/dev/null
  NO_COLOR=1 $ASDLC init --tools claude-code --ci none >/dev/null
}

echo "sdd installer self-test (opt-in, needs network)"

if skip_unless npx "openspec"; then
  setup
  check "asdlc init --sdd openspec" env NO_COLOR=1 $ASDLC init --tools claude-code --ci none --sdd openspec --force
  check "openspec produced config.yaml" test -f openspec/config.yaml
  check "--sdd openspec keeps openspec/changes (not .asdlc/)" \
    grep -q "changes: \"openspec/changes\"" .asdlc/policy.yaml
fi

if skip_unless uv "speckit"; then
  setup
  check "asdlc init --sdd speckit" env NO_COLOR=1 $ASDLC init --tools claude-code --ci none --sdd speckit --force
  check "speckit produced .specify/" test -d .specify
  check "--sdd speckit switches to .asdlc/changes (not openspec/)" \
    grep -q "changes: \"\.asdlc/changes\"" .asdlc/policy.yaml
fi

# BMAD's installer has been observed to show one confirmation prompt even
# with --yes --tools set (upstream quirk, not an asdlc flag bug) — it needs a
# real TTY to answer that prompt, so this case is skipped outside one instead
# of hard-failing on every headless CI run. Runs fine for a human at a real
# terminal: `asdlc init --sdd bmad` doesn't capture stdin/stdout.
if [ ! -t 0 ]; then
  echo "  skip bmad (no TTY attached)"
  SKIP=$((SKIP+1))
elif skip_unless npx "bmad"; then
  setup
  check "asdlc init --sdd bmad" env NO_COLOR=1 $ASDLC init --tools claude-code --ci none --sdd bmad --force
  check "bmad produced its tree" bash -c "[ -d _bmad ] || [ -d bmad-agents ]"
fi

echo
echo "passed=$PASS failed=$FAIL skipped=$SKIP"
[ "$FAIL" -eq 0 ]
