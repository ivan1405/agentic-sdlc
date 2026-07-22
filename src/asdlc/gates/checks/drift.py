"""Gate: spec/code drift.

The failure mode every SDD rollout hits at month six: code moves, specs don't,
and the specs become lies that nobody reads and agents then act on. Frameworks
leave reconciliation manual; this makes it a merge blocker.

Rule: if production code under a capability changes, the capability's spec must
change in the same PR — either the living spec or a delta in a change folder.
"""
from __future__ import annotations

import re

from asdlc.gates.checks import CheckResult, Context


def run(ctx: Context) -> CheckResult:
    caps: dict[str, list[str]] = ctx.policy.get("capabilities", {}) or {}
    if not caps:
        return CheckResult("spec-drift", "skip", "no capabilities mapped in policy")

    touched_specs = {f for f in ctx.changed_files if f.startswith(ctx.specs_dir)}
    delta_text = ""
    for c in ctx.touched_changes:
        spec = c / "spec.md"
        if spec.exists():
            delta_text += spec.read_text()

    problems = []
    for cap, globs in caps.items():
        hits = ctx.matches(globs)
        if not hits:
            continue
        spec_touched = any(f"{ctx.specs_dir}/{cap}" in s for s in touched_specs)
        # tolerate markdown emphasis: "**Capability:** checkout"
        cap_in_delta = re.search(
            rf"(?i)\bcapability:\**\s*{re.escape(cap)}\b", delta_text
        )
        if not (spec_touched or cap_in_delta):
            problems.append(
                f"capability '{cap}': {len(hits)} file(s) changed, spec untouched "
                f"(e.g. {hits[0]})"
            )

    mode = ctx.cfg("spec-drift", "mode", "fail")
    if problems:
        return CheckResult(
            "spec-drift",
            "fail" if mode == "fail" else "warn",
            f"{len(problems)} capability/capabilities drifting",
            problems + ["fix: update openspec/specs/<capability>/spec.md, or declare "
                        "'Capability: <name>' in the change's spec.md"],
        )
    return CheckResult("spec-drift", "pass", "no drift detected")
