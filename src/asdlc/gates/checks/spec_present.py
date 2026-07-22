"""Gate: production code may not change without a change folder in the same PR.

This is the load-bearing gate. Everything else in the standard is downstream of
"the spec is the artifact". If code can land without one, it won't take three
sprints before nobody writes specs at all.
"""
from __future__ import annotations

from asdlc.gates.checks import CheckResult, Context

ARTIFACTS = ["proposal.md", "spec.md", "design.md", "tasks.md"]


def run(ctx: Context) -> CheckResult:
    prod = ctx.production_files
    if not prod:
        return CheckResult("spec-present", "pass", "no production code touched")

    exempt = ctx.matches(ctx.cfg("spec-present", "exempt_globs", []) or [], prod)
    prod = [f for f in prod if f not in exempt]
    if not prod:
        return CheckResult("spec-present", "pass", "all touched code is exempt")

    changes = ctx.touched_changes
    if not changes:
        return CheckResult(
            "spec-present",
            "fail",
            f"{len(prod)} production file(s) changed with no change folder",
            [f"expected a folder under {ctx.changes_dir}/<change-id>/ in this PR",
             "run: asdlc new <change-id>",
             *[f"unbacked: {f}" for f in prod[:8]]],
        )

    missing = []
    required = ctx.cfg("spec-present", "required_artifacts", ARTIFACTS)
    for c in changes:
        for a in required:
            if not (c / a).exists():
                missing.append(f"{c.name}/{a}")
    if missing:
        return CheckResult("spec-present", "fail", "change folder is incomplete", missing)

    return CheckResult(
        "spec-present", "pass", f"{len(prod)} file(s) backed by {', '.join(c.name for c in changes)}"
    )
