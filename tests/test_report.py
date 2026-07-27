"""`asdlc report` — pure aggregation is unit-tested with synthetic data; the
git walk is exercised end-to-end on a throwaway repo with two real merges.

    PYTHONPATH=src python3 -m pytest tests/test_report.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from asdlc import report  # noqa: E402
from asdlc.report import Merge  # noqa: E402


# --------------------------------------------------------------------------- #
# pure: spec_backed
# --------------------------------------------------------------------------- #
def test_spec_backed_rule():
    globs = ["src/**", "lib/**"]
    cd = "openspec/changes"
    # production code + a change folder in the same merge -> backed
    assert report.spec_backed(["src/a.py", "openspec/changes/x/spec.md"], globs, cd) is True
    # production code, no change folder -> not backed
    assert report.spec_backed(["src/a.py"], globs, cd) is False
    # no production code touched -> excluded from the percentage
    assert report.spec_backed(["README.md", "docs/x.md"], globs, cd) is None


# --------------------------------------------------------------------------- #
# pure: aggregate
# --------------------------------------------------------------------------- #
def test_aggregate_basic():
    merges = [Merge("a", 3600, []), Merge("b", 7200, []), Merge("c", None, [])]
    backed = [True, False, None]
    m = report.aggregate(merges, backed)
    assert m["merges"] == 3
    assert m["lead_time"]["measured"] == 2
    assert m["lead_time"]["median"] == "1.0h"
    assert m["lead_time"]["p90"] == "2.0h"
    assert m["spec_coverage"] == {"production_merges": 2, "with_spec": 1, "pct": 50.0}


def test_aggregate_empty_is_safe():
    m = report.aggregate([], [])
    assert m["merges"] == 0
    assert m["lead_time"] == {"measured": 0, "median": "n/a", "p90": "n/a"}
    assert m["spec_coverage"]["pct"] is None  # no divide-by-zero


def test_human_duration_switches_to_days():
    assert report._human_duration(3600) == "1.0h"
    assert report._human_duration(None) == "n/a"
    assert report._human_duration(3600 * 72) == "3.0d"  # >48h -> days


# --------------------------------------------------------------------------- #
# verify --json history
# --------------------------------------------------------------------------- #
def test_verify_history_aggregates(tmp_path):
    (tmp_path / "a.json").write_text('[{"name": "spec-lint", "status": "pass"}]')
    (tmp_path / "b.json").write_text(
        '[{"name": "spec-lint", "status": "pass"}, {"name": "coverage-delta", "status": "fail"}]'
    )
    vh = report.verify_history(tmp_path)
    assert vh["runs"] == 2
    assert vh["green_pct"] == 50.0
    assert vh["gate_fails"] == {"coverage-delta": 1}


def test_verify_history_absent_or_empty(tmp_path):
    assert report.verify_history(None) is None
    assert report.verify_history(tmp_path / "nope") is None
    assert report.verify_history(tmp_path) is None  # dir exists but has no *.json


# --------------------------------------------------------------------------- #
# integration: a real repo with two merges (one spec-backed, one not)
# --------------------------------------------------------------------------- #
def _git(cwd, *args, **env):
    e = {"GIT_AUTHOR_DATE": "2026-01-01T00:00:00", "GIT_COMMITTER_DATE": "2026-01-01T00:00:00",
         **{k: v for k, v in env.items()}}
    import os
    subprocess.run(["git", *args], cwd=cwd, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                   env={**os.environ, **e})


def _merge_pr(repo, branch, files: dict[str, str]):
    _git(repo, "checkout", "-q", "-b", branch)
    for rel, content in files.items():
        p = repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", f"{branch} work")
    _git(repo, "checkout", "-q", "main")
    _git(repo, "merge", "--no-ff", "-m", f"Merge {branch}", branch)


def test_report_build_on_two_merges(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@t.io")
    _git(repo, "config", "user.name", "t")
    (repo / "README.md").write_text("#\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "init")
    _git(repo, "branch", "-M", "main")

    # PR1: production code WITH a change folder -> spec-backed
    _merge_pr(repo, "pr1", {"src/a.py": "x=1\n", "openspec/changes/add-a/spec.md": "# spec\n"})
    # PR2: production code, NO change folder -> not backed
    _merge_pr(repo, "pr2", {"src/b.py": "y=2\n"})

    m = report.build(repo, since="10 years ago", results_dir=None,
                     source_globs=["src/**"], changes_dir="openspec/changes")
    assert m["merges"] == 2
    assert m["spec_coverage"] == {"production_merges": 2, "with_spec": 1, "pct": 50.0}
    assert m["lead_time"]["measured"] == 2
    assert m["verify_history"] is None
    assert set(m["unavailable"]) == {"review_rework_rate", "escaped_defects"}
