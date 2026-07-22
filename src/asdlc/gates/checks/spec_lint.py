"""Gate: a spec is only a spec if it is testable.

Enforces the artifact contract:
  - every requirement has a stable ID (REQ-xxx) and a SHALL/SHALL NOT statement
  - every requirement has at least one Given/When/Then acceptance scenario
  - no unresolved placeholders left by the agent or the human
This is the gate that stops "the system should be fast" reaching an agent.
"""
from __future__ import annotations

import re

from asdlc.gates.checks import CheckResult, Context

REQ_RE = re.compile(r"^###\s+(REQ-[A-Z0-9-]+):\s*(.+)$", re.M)
COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
# Template scaffolding the author never filled in: TODO, {{VAR}}, and <angle
# placeholders>. Comments are stripped first so guidance text is not flagged.
PLACEHOLDER_RE = re.compile(r"(TODO|TBD|FIXME|\{\{[A-Z_]+\}\}|<[a-z][a-z0-9 /_.-]{3,}>)")


def _lint(text: str, label: str, ctx: Context) -> list[str]:
    problems: list[str] = []
    text = COMMENT_RE.sub("", text)

    for m in sorted({m.group(1) for m in PLACEHOLDER_RE.finditer(text)}):
        problems.append(f"{label}: unresolved placeholder '{m}'")

    reqs = list(REQ_RE.finditer(text))
    if not reqs:
        problems.append(f"{label}: no requirements found (expected '### REQ-xxx: ...')")
        return problems

    min_scen = ctx.cfg("spec-lint", "min_scenarios_per_requirement", 1)
    for i, m in enumerate(reqs):
        rid = m.group(1)
        body = text[m.end(): reqs[i + 1].start() if i + 1 < len(reqs) else len(text)]
        if not re.search(r"\bSHALL(\s+NOT)?\b", body):
            problems.append(f"{label}/{rid}: no normative SHALL statement")
        scenarios = len(re.findall(r"^\s*#### Scenario:", body, re.M))
        if scenarios < min_scen:
            problems.append(
                f"{label}/{rid}: {scenarios} acceptance scenario(s), need >= {min_scen}"
            )
        for kw in ("Given", "When", "Then"):
            if scenarios and not re.search(rf"^\s*-?\s*\*?\*?{kw}\b", body, re.M):
                problems.append(f"{label}/{rid}: scenario missing '{kw}'")
    return problems


def run(ctx: Context) -> CheckResult:
    changes = ctx.touched_changes
    if not changes:
        return CheckResult("spec-lint", "pass", "no change folders in diff")

    problems: list[str] = []
    checked = 0
    for c in changes:
        spec = c / "spec.md"
        if not spec.exists():
            problems.append(f"{c.name}: spec.md missing")
            continue
        checked += 1
        problems += _lint(spec.read_text(), c.name, ctx)

    if problems:
        return CheckResult("spec-lint", "fail", f"{len(problems)} problem(s)", problems[:15])
    return CheckResult("spec-lint", "pass", f"{checked} spec(s) well-formed")
