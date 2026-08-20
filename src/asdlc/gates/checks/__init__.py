"""Gate framework.

Design rules:
  1. Zero hard dependencies. These run in whatever CI the client already has.
  2. Every check is tool-blind. It inspects git + files, never an agent.
  3. A crashing check fails the build. Gates that fail open are theatre.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Literal

from asdlc import yamlish

Status = Literal["pass", "fail", "warn", "skip"]


@dataclass
class CheckResult:
    name: str
    status: Status
    detail: str = ""
    details: list[str] = field(default_factory=list)


@dataclass
class Context:
    root: Path
    policy: dict[str, Any]
    changed_files: list[str]
    base: str
    stage: str
    changes_dir: str
    specs_dir: str

    def cfg(self, check: str, key: str, default: Any = None) -> Any:
        return self.policy.get("checks", {}).get(check, {}).get(key, default)

    def matches(self, patterns: list[str], files: list[str] | None = None) -> list[str]:
        import fnmatch

        files = self.changed_files if files is None else files
        out = []
        for f in files:
            if any(fnmatch.fnmatch(f, p) for p in patterns):
                out.append(f)
        return out

    @property
    def touched_changes(self) -> list[Path]:
        """Change folders referenced by this diff."""
        ids = set()
        for f in self.changed_files:
            m = re.match(rf"{re.escape(self.changes_dir)}/([^/]+)/", f)
            if m:
                ids.add(m.group(1))
        return [self.root / self.changes_dir / i for i in sorted(ids)]

    @property
    def production_files(self) -> list[str]:
        return self.matches(self.policy.get("source_globs", ["src/**"]))


@dataclass
class Check:
    name: str
    stage: Literal["spec", "code", "any"]
    run: Callable[[Context], CheckResult]


# --------------------------------------------------------------------------- #
# policy loading
# --------------------------------------------------------------------------- #
def load_policy(root: Path, pkg: Path) -> dict:
    path = root / ".asdlc" / "policy.yaml"
    if not path.exists():
        path = pkg / "gates" / "policy.yaml"
    return yamlish.load(path.read_text())


# --------------------------------------------------------------------------- #
# registry
# --------------------------------------------------------------------------- #
from asdlc.gates.checks import (  # noqa: E402
    coverage,
    drift,
    human_approval,
    security,
    spec_lint,
    spec_present,
    traceability,
)

ALL_CHECKS: list[Check] = [
    Check("spec-present", "code", spec_present.run),
    Check("spec-lint", "spec", spec_lint.run),
    Check("traceability", "code", traceability.run),
    Check("spec-drift", "code", drift.run),
    Check("coverage-delta", "code", coverage.run),
    Check("security-scan", "code", security.run),
    Check("human-approval", "code", human_approval.run),
]
