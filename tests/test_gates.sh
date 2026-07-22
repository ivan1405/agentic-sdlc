#!/usr/bin/env bash
# Proves the gates bite. A gate you have not seen fail is a gate you do not have.
#
#   bash tests/test_gates.sh
#
# Each case builds a throwaway repo, plays an agent's realistic mistake, and
# asserts the right gate blocks it.
set -uo pipefail

STD="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="$STD/src"
ASDLC="python3 -m asdlc"
PASS=0; FAIL=0

setup() {
  WORK=$(mktemp -d); cd "$WORK"
  git init -q; git config user.email t@t.io; git config user.name t
  mkdir -p src tests; echo "#" > README.md
  git add -A; git commit -qm init; git branch -M main
  NO_COLOR=1 $ASDLC init --project demo --tools generic --ci none >/dev/null
  python3 - <<'PY'
from pathlib import Path
p = Path(".asdlc/policy.yaml"); s = p.read_text()
s = s.replace("capabilities:\n", 'capabilities:\n  checkout:\n    - "src/checkout*"\n', 1)
s = s.replace("    missing_report: fail", "    missing_report: skip")
p.write_text(s)
PY
  git add -A; git commit -qm standard
  git checkout -qb feat
}

good_change() {   # a fully compliant change folder
  NO_COLOR=1 $ASDLC new fix-cart >/dev/null
  cat > openspec/changes/fix-cart/spec.md <<'EOF'
# Spec — fix cart
**Change ID:** fix-cart
**Capability:** checkout
## ADDED Requirements
### REQ-001: Reject empty cart
The system SHALL reject a checkout whose cart has no items.
#### Scenario: Empty cart
- **Given** an empty cart
- **When** checkout runs
- **Then** CartEmptyError is raised
EOF
  cat > openspec/changes/fix-cart/tasks.md <<'EOF'
# Tasks
- [x] (REQ-001) raise CartEmptyError
EOF
  sed -i 's/^Approved-by: .*/Approved-by: Ana Ruiz <ana@x.com>/' openspec/changes/fix-cart/design.md
  cat > tests/test_checkout.py <<'EOF'
def test_REQ_001_empty(): """REQ-001"""
EOF
  cat > src/checkout.py <<'EOF'
def checkout(cart):
    if not cart:
        raise ValueError("empty")
    return sum(cart)
EOF
}

assert_gate() { # name expected_status gate_name
  local name="$1" expect="$2" gate="$3"
  git add -A >/dev/null 2>&1
  local out; out=$(NO_COLOR=1 ASDLC_PR_APPROVALS=1 $ASDLC verify --base main 2>&1)
  local line; line=$(echo "$out" | grep -E "  (PASS|FAIL|WARN|SKIP)  ${gate} " | awk '{print $1}')
  if [ "$line" = "$expect" ]; then
    echo "  ok   $name"; PASS=$((PASS+1))
  else
    echo "  FAIL $name — expected $gate=$expect, got '${line:-<gate not run>}'"
    echo "$out" | sed 's/^/       | /'
    FAIL=$((FAIL+1))
  fi
  cd /; rm -rf "$WORK"
}

echo "gate self-test"

setup; good_change
assert_gate "compliant change passes spec-present" PASS spec-present

setup
echo 'def checkout(c): return sum(c)' > src/checkout.py
assert_gate "code without a change folder is blocked" FAIL spec-present

setup; good_change
# agent writes a requirement with no acceptance scenario
python3 - <<'PY'
from pathlib import Path
p = Path("openspec/changes/fix-cart/spec.md")
p.write_text(p.read_text().split("#### Scenario")[0])
PY
assert_gate "requirement with no scenario is blocked" FAIL spec-lint

setup; good_change
# agent leaves the template placeholder in
python3 - <<'PY'
from pathlib import Path
p = Path("openspec/changes/fix-cart/spec.md")
p.write_text(p.read_text() + "\n### REQ-002: TODO\nThe system SHALL TBD.\n#### Scenario: x\n- **Given** a\n- **When** b\n- **Then** c\n")
PY
assert_gate "unfilled placeholder is blocked" FAIL spec-lint

setup; good_change
rm tests/test_checkout.py
assert_gate "requirement with no test is blocked" FAIL traceability

setup; good_change
# agent edits mapped code but never touches the spec
python3 - <<'PY'
from pathlib import Path
p = Path("openspec/changes/fix-cart/spec.md")
p.write_text(p.read_text().replace("**Capability:** checkout", "**Capability:** other"))
PY
assert_gate "code moves, spec does not => drift blocked" FAIL spec-drift

setup; good_change
echo 'AWS_KEY = "AKIAIOSFODNN7EXAMPLE"' >> src/checkout.py
assert_gate "hardcoded credential is blocked" FAIL security-scan

setup; good_change
echo 'AWS_KEY = "AKIAIOSFODNN7EXAMPLE"  # asdlc:allow-secret (docs example)' >> src/checkout.py
assert_gate "justified false positive passes" PASS security-scan

setup; good_change
# agent implements a migration and signs its own homework by deleting the trailer
mkdir -p src/migrations && echo "ALTER TABLE carts;" > src/migrations/001.sql
sed -i '/^Approved-by:/d' openspec/changes/fix-cart/design.md
assert_gate "sensitive change without a human signature is blocked" FAIL human-approval

echo
echo "passed=$PASS failed=$FAIL"
[ "$FAIL" -eq 0 ]
