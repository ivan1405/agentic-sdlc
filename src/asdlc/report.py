"""`asdlc report` — adoption metrics from git and archived verify results.

Deliberately API-free: no HTTP, no `gh`/`glab`, no runtime dependency — the same
constraint the gates hold to. So it computes what git alone can compute (PR lead
time, merge throughput, % of merged PRs that carried a spec) and, if given a
directory of archived `asdlc verify --json` outputs, the gate pass-rate. Review
rework rate and escaped defects genuinely need the PR/issue API, so they are
reported as unavailable rather than half-measured.

Git extraction and pure aggregation are separated so the arithmetic is testable
without fabricating dated commits.
"""
from __future__ import annotations

import fnmatch
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Merge:
    sha: str
    lead_seconds: int | None      # branch age at merge; None if not computable
    files: list[str]              # the PR's net change (M^1 -> M)


# --------------------------------------------------------------------------- #
# git extraction
# --------------------------------------------------------------------------- #
def _git(root: Path, *args: str) -> str:
    """Same idiom as cli.changed_files — returns stdout, or "" on any failure."""
    try:
        return subprocess.check_output(
            ["git", *args], cwd=root, text=True, stderr=subprocess.DEVNULL
        )
    except Exception:
        return ""


def merge_records(root: Path, since: str) -> list[Merge]:
    """First-parent merge commits on HEAD's history within the window."""
    out = _git(root, "log", "--merges", "--first-parent",
               f"--since={since}", "--format=%H|%ct")
    merges: list[Merge] = []
    for line in out.splitlines():
        if "|" not in line:
            continue
        sha, _, ct = line.partition("|")
        merge_ct = int(ct) if ct.strip().isdigit() else None
        # Second parent = the merged-in branch tip. No second parent => not a
        # real branch merge (e.g. an octopus edge case) — skip.
        parents = _git(root, "rev-parse", f"{sha}^@").split()
        if len(parents) < 2 or merge_ct is None:
            continue
        base, tip = parents[0], parents[1]
        branch_cts = [int(x) for x in _git(root, "log", "--format=%ct", f"{base}..{tip}").split()
                      if x.strip().isdigit()]
        lead = merge_ct - min(branch_cts) if branch_cts else None
        files = [f for f in _git(root, "diff", "--name-only", base, sha).splitlines() if f.strip()]
        merges.append(Merge(sha=sha[:12], lead_seconds=lead, files=files))
    return merges


# --------------------------------------------------------------------------- #
# pure helpers (no git, no I/O)
# --------------------------------------------------------------------------- #
def spec_backed(files: list[str], source_globs: list[str], changes_dir: str) -> bool | None:
    """Historical analog of the spec-present rule for one merge's file list.

    None  -> the merge touched no production code (excluded from the %).
    False -> touched production code but carried no change folder.
    True  -> touched production code and carried a change folder.
    """
    touched_prod = any(fnmatch.fnmatch(f, g) for f in files for g in source_globs)
    if not touched_prod:
        return None
    prefix = changes_dir.rstrip("/") + "/"
    return any(f.startswith(prefix) for f in files)


def _percentile(values: list[float], pct: float) -> float:
    """Nearest-rank percentile on a sorted copy; 0.0 for empty input."""
    if not values:
        return 0.0
    ordered = sorted(values)
    k = max(0, min(len(ordered) - 1, round((pct / 100) * (len(ordered) - 1))))
    return ordered[k]


def _human_duration(seconds: float | None) -> str:
    if seconds is None:
        return "n/a"
    hours = seconds / 3600
    if hours < 48:
        return f"{hours:.1f}h"
    return f"{hours / 24:.1f}d"


def aggregate(merges: list[Merge], backed_flags: list[bool | None]) -> dict:
    """Throughput, lead-time median/p90, and spec-coverage % — pure arithmetic."""
    leads = [float(m.lead_seconds) for m in merges if m.lead_seconds is not None]
    prod_merges = [b for b in backed_flags if b is not None]
    backed = sum(1 for b in prod_merges if b)
    return {
        "merges": len(merges),
        "lead_time": {
            "measured": len(leads),
            "median": _human_duration(_percentile(leads, 50) if leads else None),
            "p90": _human_duration(_percentile(leads, 90) if leads else None),
        },
        "spec_coverage": {
            "production_merges": len(prod_merges),
            "with_spec": backed,
            "pct": round(100 * backed / len(prod_merges), 1) if prod_merges else None,
        },
    }


# --------------------------------------------------------------------------- #
# verify --json history
# --------------------------------------------------------------------------- #
def verify_history(results_dir: Path | None) -> dict | None:
    """Aggregate a directory of archived `asdlc verify --json` outputs (each a
    list of CheckResult dicts). None if the dir is absent or has no readable
    result files."""
    if not results_dir or not results_dir.is_dir():
        return None
    runs = 0
    green = 0
    gate_fails: dict[str, int] = {}
    for path in sorted(results_dir.glob("*.json")):
        try:
            results = json.loads(path.read_text())
        except Exception:
            continue
        if not isinstance(results, list):
            continue
        runs += 1
        fails = [r for r in results if isinstance(r, dict) and r.get("status") == "fail"]
        if not fails:
            green += 1
        for r in fails:
            name = r.get("name", "?")
            gate_fails[name] = gate_fails.get(name, 0) + 1
    if runs == 0:
        return None
    return {
        "runs": runs,
        "green_pct": round(100 * green / runs, 1),
        "gate_fails": dict(sorted(gate_fails.items(), key=lambda kv: -kv[1])),
    }


# --------------------------------------------------------------------------- #
# orchestration
# --------------------------------------------------------------------------- #
def build(root: Path, *, since: str, results_dir: Path | None,
          source_globs: list[str], changes_dir: str) -> dict:
    merges = merge_records(root, since)
    backed_flags = [spec_backed(m.files, source_globs, changes_dir) for m in merges]
    metrics = aggregate(merges, backed_flags)
    metrics["since"] = since
    metrics["verify_history"] = verify_history(results_dir)
    # Honest about what git can't see.
    metrics["unavailable"] = {
        "review_rework_rate": "needs the PR review API (gh/glab) — not derivable from git",
        "escaped_defects": "needs the issue tracker — not derivable from git",
    }
    return metrics
