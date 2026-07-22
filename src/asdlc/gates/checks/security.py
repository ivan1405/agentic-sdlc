"""Gate: security scanning + secrets.

Shells out to whatever the client already owns (semgrep, trivy, snyk, gitleaks,
bandit, npm audit...). We do not ship a scanner; we ship the contract that one
runs and that its exit code is a merge blocker. The regex secrets sweep is a
zero-dependency floor for clients that own nothing yet.
"""
from __future__ import annotations

import re
import subprocess

from asdlc.gates.checks import CheckResult, Context

SECRET_PATTERNS = [
    (r"AKIA[0-9A-Z]{16}", "AWS access key id"),
    (r"(?i)aws_secret_access_key\s*[:=]\s*['\"][0-9a-zA-Z/+]{40}['\"]", "AWS secret key"),
    (r"ghp_[0-9A-Za-z]{36}", "GitHub PAT"),
    (r"sk-[A-Za-z0-9]{32,}", "API key (sk- prefix)"),
    (r"-----BEGIN (RSA|EC|OPENSSH|PGP) PRIVATE KEY-----", "private key"),
    (r"(?i)(password|passwd|secret|token)\s*[:=]\s*['\"][^'\"$\{\s]{8,}['\"]", "hardcoded credential"),
]
ALLOW_RE = re.compile(r"asdlc:allow-secret")


def _sweep(ctx: Context) -> list[str]:
    hits = []
    for f in ctx.changed_files:
        p = ctx.root / f
        if not p.is_file() or p.stat().st_size > 2_000_000:
            continue
        try:
            text = p.read_text(errors="ignore")
        except Exception:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if ALLOW_RE.search(line):
                continue
            for pat, label in SECRET_PATTERNS:
                if re.search(pat, line):
                    hits.append(f"{f}:{i}: possible {label}")
                    break
    return hits


def run(ctx: Context) -> CheckResult:
    problems: list[str] = []

    if ctx.cfg("security-scan", "secrets_sweep", True):
        problems += _sweep(ctx)

    for cmd in ctx.cfg("security-scan", "scanners", []) or []:
        try:
            proc = subprocess.run(cmd, cwd=ctx.root, shell=True, capture_output=True, text=True, timeout=900)
        except subprocess.TimeoutExpired:
            problems.append(f"scanner timed out: {cmd}")
            continue
        except Exception as e:
            problems.append(f"scanner failed to start ({cmd}): {e}")
            continue
        if proc.returncode != 0:
            tail = (proc.stdout + proc.stderr).strip().splitlines()[-4:]
            problems.append(f"scanner failed (exit {proc.returncode}): {cmd}")
            problems += [f"  {l}" for l in tail]

    if problems:
        return CheckResult("security-scan", "fail", f"{len(problems)} finding(s)", problems[:15])
    return CheckResult("security-scan", "pass", "secrets sweep + configured scanners clean")
