"""Gate: coverage on changed lines.

Deliberately scoped to files the PR touched. Repo-wide coverage thresholds are a
ratchet nobody can move; changed-file coverage is enforceable from day one on a
brownfield codebase, which is the situation you are actually in.

Reads Cobertura XML (pytest-cov, coverage.py, jacoco -> cobertura, nyc, gocover
-> cobertura). One format, every language.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from asdlc.gates.checks import CheckResult, Context


def _parse_cobertura(path: Path) -> dict[str, tuple[int, int]]:
    """-> {filename: (covered_lines, total_lines)}"""
    root = ET.parse(path).getroot()
    sources = [s.text or "" for s in root.findall(".//sources/source")]
    out: dict[str, tuple[int, int]] = {}
    for cls in root.findall(".//class"):
        fn = cls.get("filename") or ""
        lines = cls.findall("./lines/line")
        if not lines:
            continue
        total = len(lines)
        covered = sum(1 for l in lines if int(l.get("hits", "0")) > 0)
        for s in sources or [""]:
            key = fn if not s else f"{s.rstrip('/')}/{fn}".lstrip("./")
            prev = out.get(key, (0, 0))
            out[key] = (prev[0] + covered, prev[1] + total)
    return out


def run(ctx: Context) -> CheckResult:
    # No production code in the diff means nothing to cover. Demanding a report
    # here would fail docs-only PRs and teach the team to ignore this gate.
    if not ctx.production_files:
        return CheckResult("coverage-delta", "pass", "no production code touched")

    report = ctx.root / ctx.cfg("coverage-delta", "report", "coverage.xml")
    if not report.exists():
        mode = ctx.cfg("coverage-delta", "missing_report", "fail")
        return CheckResult(
            "coverage-delta",
            "fail" if mode == "fail" else "skip",
            f"no coverage report at {report.relative_to(ctx.root) if report.is_relative_to(ctx.root) else report}",
            ["run your test suite with cobertura output before `asdlc verify`"],
        )

    data = _parse_cobertura(report)
    threshold = float(ctx.cfg("coverage-delta", "min_changed_file_coverage", 80))
    problems, measured = [], 0

    for f in ctx.production_files:
        match = next((k for k in data if k.endswith(f) or f.endswith(k)), None)
        if not match:
            continue
        covered, total = data[match]
        if total == 0:
            continue
        pct = 100.0 * covered / total
        measured += 1
        if pct < threshold:
            problems.append(f"{f}: {pct:.1f}% < {threshold:.0f}%")

    if problems:
        return CheckResult("coverage-delta", "fail", f"{len(problems)} file(s) under threshold", problems[:12])
    return CheckResult("coverage-delta", "pass", f"{measured} changed file(s) >= {threshold:.0f}%")
