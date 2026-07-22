"""Gate: a human signs the things agents must not decide alone.

Not all diffs are equal. Architecture, data migrations, authn/authz, payments,
and public API contracts get a named human approver recorded in the change
folder. Everything else can flow. This is the gate that makes the whole thing
sellable to a client's risk function.
"""
from __future__ import annotations

import os
import re

from asdlc.gates.checks import CheckResult, Context

APPROVED_RE = re.compile(r"^Approved-by:\s*(.+?)\s*<(.+?)>\s*$", re.M)


def run(ctx: Context) -> CheckResult:
    sensitive_map: dict[str, list[str]] = ctx.cfg("human-approval", "sensitive", {}) or {}
    triggered: dict[str, list[str]] = {}
    for label, globs in sensitive_map.items():
        hits = ctx.matches(globs)
        if hits:
            triggered[label] = hits

    if not triggered:
        return CheckResult("human-approval", "pass", "no sensitive surfaces touched")

    changes = ctx.touched_changes
    if not changes:
        return CheckResult("human-approval", "fail", "sensitive change with no change folder",
                           [f"{k}: {v[0]}" for k, v in triggered.items()])

    problems = []
    approvers = []
    for c in changes:
        design = c / "design.md"
        text = design.read_text() if design.exists() else ""
        found = APPROVED_RE.findall(text)
        if not found:
            problems.append(
                f"{c.name}/design.md: missing 'Approved-by: Name <email>' trailer"
            )
            continue
        for name, email in found:
            domain = email.split("@")[-1].lower()
            allowed = [d.lower() for d in ctx.cfg("human-approval", "approver_domains", []) or []]
            if allowed and domain not in allowed:
                problems.append(f"{c.name}: approver {email} not in an allowed domain")
            approvers.append(email)

    # CI-side reinforcement: the PR itself must carry reviews.
    min_reviews = int(ctx.cfg("human-approval", "min_pr_reviews", 0) or 0)
    if min_reviews:
        got = os.environ.get("ASDLC_PR_APPROVALS")
        if got is None:
            problems.append("ASDLC_PR_APPROVALS not set — CI cannot confirm PR reviews")
        elif int(got) < min_reviews:
            problems.append(f"PR has {got} approval(s), policy requires {min_reviews}")

    reasons = ", ".join(triggered)
    if problems:
        return CheckResult("human-approval", "fail", f"sensitive: {reasons}", problems)
    return CheckResult("human-approval", "pass", f"sensitive: {reasons} — signed by {', '.join(approvers)}")
