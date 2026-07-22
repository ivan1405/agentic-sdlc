#!/usr/bin/env python3
"""asdlc — Agentic SDLC standard CLI.

Tool-agnostic. Knows nothing about Claude Code, Codex, Copilot or Cursor beyond
rendering their adapter files. All enforcement lives in `asdlc verify`, which is
the same command a developer runs locally and CI runs on every PR.

Commands
--------
  asdlc init                 Scaffold the standard into a repo (AGENTS.md, skills, adapters, CI)
  asdlc new <change-id>      Create a change folder from the artifact contract
  asdlc verify               Run the gate suite (the actual standard)
  asdlc doctor               Report which agent tools are wired up in this repo
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

# The asset payload ships inside the package. Anything read at runtime must be
# under ASSETS or gates/ — if it is not, it will not survive `pip install`.
PKG = Path(__file__).resolve().parent
ASSETS = PKG / "assets"

from asdlc import commands, sdd
from asdlc.gates.checks import ALL_CHECKS, CheckResult, Context, load_policy

CHANGES_DIR = "openspec/changes"
SPECS_DIR = "openspec/specs"
ARTIFACTS = ["proposal.md", "spec.md", "design.md", "tasks.md"]

GREEN, RED, YELLOW, DIM, RESET = "\033[32m", "\033[31m", "\033[33m", "\033[2m", "\033[0m"
if not sys.stdout.isatty() or os.environ.get("NO_COLOR"):
    GREEN = RED = YELLOW = DIM = RESET = ""


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def repo_root(start: Path | None = None) -> Path:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=start or Path.cwd(),
            text=True,
            stderr=subprocess.DEVNULL,
        )
        return Path(out.strip())
    except Exception:
        return Path.cwd()


def changed_files(root: Path, base: str) -> list[str]:
    """Files changed vs the merge-base with `base`. Falls back to working tree."""
    try:
        mb = subprocess.check_output(
            ["git", "merge-base", "HEAD", base], cwd=root, text=True, stderr=subprocess.DEVNULL
        ).strip()
        out = subprocess.check_output(
            ["git", "diff", "--name-only", f"{mb}...HEAD"], cwd=root, text=True
        )
        files = [f for f in out.splitlines() if f.strip()]
        if files:
            return files
    except Exception:
        pass
    try:
        out = subprocess.check_output(["git", "diff", "--name-only", "HEAD"], cwd=root, text=True)
        return [f for f in out.splitlines() if f.strip()]
    except Exception:
        return []


def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9-]+", "-", s.lower()).strip("-")


# --------------------------------------------------------------------------- #
# init
# --------------------------------------------------------------------------- #
def cmd_init(args: argparse.Namespace) -> int:
    root = repo_root()
    print(f"Installing the agentic SDLC standard into {root}")

    (root / CHANGES_DIR).mkdir(parents=True, exist_ok=True)
    (root / SPECS_DIR).mkdir(parents=True, exist_ok=True)
    (root / ".asdlc").mkdir(exist_ok=True)

    # policy
    dst_policy = root / ".asdlc" / "policy.yaml"
    if not dst_policy.exists() or args.force:
        shutil.copy(PKG / "gates" / "policy.yaml", dst_policy)
        print(f"  {GREEN}+{RESET} .asdlc/policy.yaml            (edit this per client)")

    # AGENTS.md
    agents = root / "AGENTS.md"
    if not agents.exists() or args.force:
        tpl = (ASSETS / "templates" / "AGENTS.md.tpl").read_text()
        tpl = tpl.replace("{{PROJECT}}", args.project or root.name)
        tpl = tpl.replace("{{STACK}}", args.stack or "TODO: languages, frameworks, versions")
        agents.write_text(tpl)
        print(f"  {GREEN}+{RESET} AGENTS.md                     (fill in the TODOs — this is the context contract)")

    # adapters
    for tool in args.tools:
        n = render_adapter(root, tool, force=args.force)
        print(f"  {GREEN}+{RESET} adapter: {tool:<20} ({n} files)")

    # SDD methodology
    if args.sdd != "none":
        sdd.install(root, args.sdd, args.tools, ASSETS,
                    project=args.project, stack=args.stack, force=args.force)
        print(f"  {GREEN}+{RESET} sdd: {args.sdd}")

    # CI
    if args.ci == "github":
        d = root / ".github" / "workflows"
        d.mkdir(parents=True, exist_ok=True)
        shutil.copy(ASSETS / "ci" / "github" / "agentic-sdlc.yml", d / "agentic-sdlc.yml")
        print(f"  {GREEN}+{RESET} .github/workflows/agentic-sdlc.yml")
    elif args.ci == "gitlab":
        shutil.copy(ASSETS / "ci" / "gitlab" / "agentic-sdlc.yml", root / ".agentic-sdlc.gitlab-ci.yml")
        print(f"  {GREEN}+{RESET} .agentic-sdlc.gitlab-ci.yml   (include: it from .gitlab-ci.yml)")

    print(
        f"\nNext: fill in AGENTS.md, tune .asdlc/policy.yaml, then run "
        f"`asdlc new my-first-change`."
    )
    return 0


# --------------------------------------------------------------------------- #
# adapters — the ONLY tool-specific code in the whole standard
# --------------------------------------------------------------------------- #
ADAPTER_TARGETS = {
    "claude-code": [(".claude/commands", "commands"), (".claude/skills", "__skills__")],
    "codex": [(".codex/prompts", "commands"), (".codex/skills", "__skills__")],
    "copilot": [(".github/prompts", "commands"), (".github/skills", "__skills__")],
    "cursor": [(".cursor/commands", "commands"), (".cursor/skills", "__skills__")],
    "generic": [("docs/agent-workflow.md", "__single__")],
}


def render_adapter(root: Path, tool: str, force: bool = False) -> int:
    if tool not in ADAPTER_TARGETS:
        raise SystemExit(f"unknown tool '{tool}'. known: {', '.join(sorted(ADAPTER_TARGETS))}")
    shared = ASSETS / "commands"
    count = 0
    for rel, kind in ADAPTER_TARGETS[tool]:
        dst = root / rel
        if kind == "__skills__":
            dst.mkdir(parents=True, exist_ok=True)
            for skill in (ASSETS / "skills").glob("*/"):
                target = dst / skill.name
                if target.exists():
                    if not force:
                        continue
                    shutil.rmtree(target)
                shutil.copytree(skill, target)
                count += 1
        elif kind == "__single__":
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(commands.render_generic(shared))
            count += 1
        else:
            dst.mkdir(parents=True, exist_ok=True)
            for name, content in sorted(commands.render_tool_files(tool, shared).items()):
                target = dst / name
                if target.exists() and not force:
                    continue
                target.write_text(content)
                count += 1
    return count


# --------------------------------------------------------------------------- #
# new
# --------------------------------------------------------------------------- #
def cmd_new(args: argparse.Namespace) -> int:
    root = repo_root()
    cid = slugify(args.change_id)
    folder = root / CHANGES_DIR / cid
    if folder.exists():
        print(f"{RED}change '{cid}' already exists{RESET}")
        return 1
    folder.mkdir(parents=True)
    for a in ARTIFACTS:
        text = (ASSETS / "templates" / "change" / a).read_text()
        text = text.replace("{{CHANGE_ID}}", cid)
        text = text.replace("{{TITLE}}", args.change_id)
        (folder / a).write_text(text)
    print(f"{GREEN}created{RESET} {CHANGES_DIR}/{cid}/  ({', '.join(ARTIFACTS)})")
    print(
        "\nHand this to whatever agent the client uses:\n"
        f"  \"Read AGENTS.md and {CHANGES_DIR}/{cid}/. Fill in proposal.md and spec.md.\n"
        "   Do not write code until spec.md passes `asdlc verify --stage spec`.\""
    )
    return 0


# --------------------------------------------------------------------------- #
# verify — the standard
# --------------------------------------------------------------------------- #
def cmd_verify(args: argparse.Namespace) -> int:
    root = repo_root()
    policy = load_policy(root, PKG)
    files = changed_files(root, args.base)
    ctx = Context(
        root=root,
        policy=policy,
        changed_files=files,
        base=args.base,
        stage=args.stage,
        changes_dir=CHANGES_DIR,
        specs_dir=SPECS_DIR,
    )

    selected = [c for c in ALL_CHECKS if c.stage in (args.stage, "any") or args.stage == "all"]
    if args.only:
        selected = [c for c in selected if c.name in args.only]

    results: list[CheckResult] = []
    print(f"{DIM}base={args.base}  changed_files={len(files)}  stage={args.stage}{RESET}\n")
    for check in selected:
        enabled = policy.get("checks", {}).get(check.name, {}).get("enabled", True)
        if not enabled:
            results.append(CheckResult(check.name, "skip", "disabled in policy"))
            continue
        try:
            res = check.run(ctx)
        except Exception as e:  # a broken check must never silently pass
            res = CheckResult(check.name, "fail", f"check crashed: {e}")
        results.append(res)

    width = max(len(r.name) for r in results) + 2
    for r in results:
        icon = {"pass": f"{GREEN}PASS{RESET}", "fail": f"{RED}FAIL{RESET}",
                "warn": f"{YELLOW}WARN{RESET}", "skip": f"{DIM}SKIP{RESET}"}[r.status]
        print(f"  {icon}  {r.name:<{width}} {r.detail}")
        for d in r.details:
            print(f"        {DIM}- {d}{RESET}")

    if args.json:
        Path(args.json).write_text(json.dumps([r.__dict__ for r in results], indent=2))

    failed = [r for r in results if r.status == "fail"]
    print()
    if failed:
        print(f"{RED}{len(failed)} gate(s) failed.{RESET} This PR is not mergeable.")
        return 1
    print(f"{GREEN}All gates passed.{RESET}")
    return 0


# --------------------------------------------------------------------------- #
# doctor
# --------------------------------------------------------------------------- #
def cmd_doctor(args: argparse.Namespace) -> int:
    root = repo_root()
    print(f"repo: {root}\n")
    checks = [
        ("AGENTS.md", (root / "AGENTS.md").exists()),
        ("policy (.asdlc/policy.yaml)", (root / ".asdlc" / "policy.yaml").exists()),
        ("skills (per-tool)", any(
            next((root / p).glob("*/SKILL.md"), None) is not None
            for p in (".claude/skills", ".codex/skills", ".github/skills", ".cursor/skills")
        )),
        ("changes dir", (root / CHANGES_DIR).exists()),
        ("specs dir", (root / SPECS_DIR).exists()),
    ]
    for name, ok in checks:
        print(f"  {GREEN + 'yes' + RESET if ok else RED + 'no ' + RESET}  {name}")

    print("\nagent tooling detected in this repo:")
    detect = {
        "claude-code": ".claude/commands",
        "codex": ".codex/prompts",
        "copilot": ".github/prompts",
        "cursor": ".cursor/commands",
    }
    any_found = False
    for tool, path in detect.items():
        if (root / path).exists():
            any_found = True
            print(f"  {GREEN}yes{RESET}  {tool:<12} ({path})")
    if not any_found:
        print(f"  {YELLOW}none{RESET} — run `asdlc init --tools claude-code codex ...`")

    print("\nSDD methodology detected in this repo:")
    detect_sdd = {
        "openspec": ["openspec/config.yaml"],
        "speckit": [".specify"],
        "bmad": ["_bmad", "bmad-agents"],
        "kiro": [".kiro/steering"],
    }
    found_sdd = {name: next((p for p in paths if (root / p).exists()), None)
                 for name, paths in detect_sdd.items()}
    if not any(found_sdd.values()):
        print(f"  {YELLOW}none{RESET} — run `asdlc init --sdd openspec` (or speckit, bmad, kiro)")
    for name, path in found_sdd.items():
        if path:
            print(f"  {GREEN}yes{RESET}  {name:<12} ({path})")

    stale = []
    for cf in sorted((root / CHANGES_DIR).glob("*/")) if (root / CHANGES_DIR).exists() else []:
        tasks = cf / "tasks.md"
        if tasks.exists():
            body = tasks.read_text()
            done = body.count("- [x]") + body.count("- [X]")
            todo = body.count("- [ ]")
            if todo:
                stale.append(f"{cf.name}: {done}/{done + todo} tasks done")
    if stale:
        print("\nopen changes:")
        for s in stale:
            print(f"  - {s}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="asdlc", description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    pi = sub.add_parser("init", help="scaffold the standard into a repo")
    pi.add_argument("--project")
    pi.add_argument("--stack")
    pi.add_argument("--tools", nargs="+", default=["claude-code", "codex", "generic"],
                    choices=sorted(ADAPTER_TARGETS))
    pi.add_argument("--ci", default="github", choices=["github", "gitlab", "none"])
    pi.add_argument("--sdd", default="none", choices=["none", *sorted(sdd.SDD_TOOLS), "kiro"],
                    help="SDD methodology to install (shells out to its own installer; kiro is templates-only)")
    pi.add_argument("--force", action="store_true")
    pi.set_defaults(func=cmd_init)

    pn = sub.add_parser("new", help="create a change folder")
    pn.add_argument("change_id")
    pn.set_defaults(func=cmd_new)

    pv = sub.add_parser("verify", help="run the gate suite")
    pv.add_argument("--base", default=os.environ.get("ASDLC_BASE", "origin/main"))
    pv.add_argument("--stage", default="all", choices=["spec", "code", "all"])
    pv.add_argument("--only", nargs="+")
    pv.add_argument("--json", help="write machine-readable results here")
    pv.set_defaults(func=cmd_verify)

    pd = sub.add_parser("doctor", help="report repo wiring")
    pd.set_defaults(func=cmd_doctor)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
