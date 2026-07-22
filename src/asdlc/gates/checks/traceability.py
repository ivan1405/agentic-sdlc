"""Gate: requirement -> task -> test.

Cheap, mechanical, and the reason your QA/regression stages stop being vibes:
if REQ-003 exists, some test file must name it. Agents are good at this once you
make it a hard gate; humans quietly skip it forever.
"""
from __future__ import annotations

import re
import subprocess

from asdlc.gates.checks import CheckResult, Context

REQ_RE = re.compile(r"\b(REQ-[A-Z0-9-]+)\b")


def _grep_repo(ctx: Context, needle: str, globs: list[str]) -> bool:
    cmd = ["git", "grep", "-l", "--fixed-strings", needle, "--"] + globs
    try:
        out = subprocess.run(cmd, cwd=ctx.root, capture_output=True, text=True)
        return bool(out.stdout.strip())
    except Exception:
        return False


def run(ctx: Context) -> CheckResult:
    changes = ctx.touched_changes
    if not changes:
        return CheckResult("traceability", "pass", "no change folders in diff")

    test_globs = ctx.cfg("traceability", "test_globs", ["tests/**", "**/*_test.*", "**/*.test.*"])
    problems: list[str] = []
    total = 0

    for c in changes:
        spec = c / "spec.md"
        tasks = c / "tasks.md"
        if not spec.exists():
            continue
        spec_reqs = set(REQ_RE.findall(spec.read_text()))
        total += len(spec_reqs)
        task_reqs = set(REQ_RE.findall(tasks.read_text())) if tasks.exists() else set()

        for rid in sorted(spec_reqs - task_reqs):
            problems.append(f"{c.name}/{rid}: no task references it (tasks.md)")

        if ctx.cfg("traceability", "require_test_reference", True):
            for rid in sorted(spec_reqs):
                if not _grep_repo(ctx, rid, test_globs):
                    problems.append(f"{c.name}/{rid}: no test references it")

        for rid in sorted(task_reqs - spec_reqs):
            problems.append(f"{c.name}/{rid}: task references a requirement not in spec.md")

    if problems:
        return CheckResult("traceability", "fail", f"{len(problems)} broken link(s)", problems[:15])
    return CheckResult("traceability", "pass", f"{total} requirement(s) traced to tasks + tests")
