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
  asdlc report               Adoption metrics from git — lead time, throughput, spec coverage
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

# The asset payload ships inside the package. Anything read at runtime must be
# under ASSETS or gates/ — if it is not, it will not survive `pip install`.
PKG = Path(__file__).resolve().parent
ASSETS = PKG / "assets"

from asdlc import adapters, mcp, practices, report, sdd, tui
from asdlc.gates.checks import ALL_CHECKS, CheckResult, Context, load_policy
# ANSI colour constants live with the wizard's other terminal machinery in tui.
from asdlc.tui import DIM, GREEN, RED, RESET, YELLOW

MCP_CATALOG = mcp.load_catalog(ASSETS)
PRACTICE_NAMES = practices.names(ASSETS)                 # all packs (for --practices choices)
CORE_PRACTICES = practices.names(ASSETS, "core")         # the default install set

ARTIFACTS = ["proposal.md", "spec.md", "design.md", "tasks.md"]


def _default_artifact_dirs(sdd_choice: str) -> tuple[str, str]:
    """Where asdlc's own artifact contract lives, chosen once at `init` time.

    openspec/ for openspec (or no) front-end — it was never confusing and the
    README already explains the "OpenSpec-compatible on purpose" reasoning.
    .asdlc/ for anything else — calling it "openspec" when a different front-
    end is actually installed is the thing this function exists to avoid.
    """
    if sdd_choice in ("none", "openspec"):
        return "openspec/changes", "openspec/specs"
    return ".asdlc/changes", ".asdlc/specs"


# What actually creates your first change, per --sdd choice. Telling someone
# who picked a real front-end to run `asdlc new` would contradict the whole
# point of relaxing the spec-shape gates for that choice — they're not
# supposed to need asdlc's own commands anymore.
NEXT_STEP_HINT = {
    "none": "run `asdlc new my-first-change`",
    "openspec": "run `openspec new change my-first-change` (or `/opsx:propose` in your agent)",
    "speckit": "run `/speckit-specify` in your agent to create your first feature spec",
    "bmad": "start your first PRD/story with BMAD's own installed workflow",
    "kiro": "open Kiro's Spec mode for your first feature",
}

SDD_DISPLAY_NAME = {"openspec": "OpenSpec", "speckit": "Spec Kit", "bmad": "BMAD", "kiro": "Kiro"}

# Display/choice order for --sdd and the wizard prompt — lightest-weight
# front-end first, heaviest (BMAD's full agile simulation) last, Kiro at the
# end since it's templates-only rather than an installed tool. Not sorted()
# because alphabetical order doesn't track that gradient.
SDD_CHOICES = ["none", "openspec", "speckit", "bmad", "kiro"]

# Shown next to each option in the init wizard's SDD prompt — what the tool
# actually is and the kind of repo it fits, so the choice isn't a guess from
# a bare name. Kept short on purpose; full detail lives in each tool's docs.
SDD_CHOICE_BLURB = {
    "none": "no extra tool — keeps asdlc's own lightweight change/spec gates. "
            "Good default for small repos or if you're not sold on a heavier method yet.",
    "openspec": "lightweight change-folder workflow (proposal/specs/tasks), no phase gates, "
                "30+ agent integrations. Fits fast-moving repos that want spec alignment "
                "without process overhead.",
    "speckit": "GitHub's structured spec -> plan -> tasks -> implement pipeline with checklists. "
               "Fits feature work in existing systems and teams that want more rigor/review gates.",
    "bmad": "full agile simulation — PM/architect/dev/QA agent personas, PRD/story workflow. "
            "Fits larger or greenfield projects where you want role-based planning; heavier setup.",
    "kiro": "templates only (no CLI) — steering files (product/tech/structure.md) for AWS Kiro IDE. "
            "Fits teams already using Kiro; skip if you don't use that IDE.",
}

# Whether a repo's real context file is AGENTS.md or CLAUDE.md depends on
# which tools are present (claude-code doesn't read AGENTS.md — it only reads
# CLAUDE.md); see Adapter.reads_agents_md for the per-tool fact, set in
# adapters/registry.py. Used by cmd_init (decides which to write) and
# cmd_doctor (decides which to check for).


def _workflow_note(sdd_choice: str) -> str:
    """AGENTS.md's workflow section shouldn't namedrop OpenSpec/Spec Kit/BMAD/
    Kiro when none of them are actually installed — that's just noise for the
    common --sdd none case. Name the specific tool only when one is real."""
    if sdd_choice == "none":
        return ("The paths below are asdlc's own artifact contract (see "
                 "`.asdlc/policy.yaml`'s `artifact_dirs`) — `asdlc verify` "
                 "checks exactly these paths.")
    name = SDD_DISPLAY_NAME[sdd_choice]
    return (f"The paths below are asdlc's own artifact contract (see "
            f"`.asdlc/policy.yaml`'s `artifact_dirs`) — its own thing, "
            f"independent of {name}, which this repo also has installed. "
            f"{name} runs alongside this workflow, not instead of it; "
            f"`asdlc verify` only ever checks the paths below.")


def _unresolved(value: str | None) -> bool:
    """True for an unsubstituted %%TOKEN%% — i.e. `asdlc init` was never run,
    so we're reading the raw packaged template, not a real .asdlc/policy.yaml."""
    return value is None or (value.startswith("%%") and value.endswith("%%"))


def _read_artifact_dirs(root: Path) -> tuple[str, str]:
    policy = load_policy(root, PKG)
    dirs = policy.get("artifact_dirs") or {}
    changes = dirs.get("changes")
    specs = dirs.get("specs")
    return (
        "openspec/changes" if _unresolved(changes) else changes,
        "openspec/specs" if _unresolved(specs) else specs,
    )


def _read_sdd_choice(root: Path) -> str:
    choice = load_policy(root, PKG).get("sdd")
    return "none" if _unresolved(choice) else choice


def _read_practices(root: Path) -> list[str] | None:
    """The practice packs a prior `asdlc init` persisted, or None if never set
    (unsubstituted %%PRACTICES%% token, or no policy yet)."""
    val = load_policy(root, PKG).get("practices")
    if val is None:
        return None
    if isinstance(val, str):
        val = [x.strip() for x in val.split(",")]
    cleaned = [v for v in val if v and not _unresolved(v)]
    return cleaned or None


# Checks that can only verify asdlc's own proposal/spec/design/tasks.md
# contract — meaningless once a real SDD front-end's own commands (not
# asdlc's /propose) are what's actually producing artifacts.
SPEC_SHAPE_CHECKS = ["spec-present", "spec-lint", "traceability", "spec-drift"]


def _relaxed_checks(sdd_choice: str) -> list[str]:
    return [] if sdd_choice == "none" else SPEC_SHAPE_CHECKS


def _disable_checks(policy_text: str, names: list[str]) -> str:
    for name in names:
        policy_text = re.sub(
            rf"(  {re.escape(name)}:\n    enabled: )true",
            r"\1false",
            policy_text,
            count=1,
        )
    return policy_text


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

    # Not pre-created: no gate needs it to exist ahead of time (they all work
    # off changed_files string matching), and asdlc shouldn't presumptuously
    # scaffold an empty "openspec/" (or any) folder before anyone's actually
    # made a change. `asdlc new` creates it lazily via mkdir(parents=True).
    changes_dir, specs_dir = _default_artifact_dirs(args.sdd)
    (root / ".asdlc").mkdir(exist_ok=True)

    # Which practice packs to install: an explicit --practices (or wizard
    # selection) wins — names and/or group tokens (core/domain/all), resolved
    # to concrete names; else whatever a prior init persisted; else core only
    # (domain packs are opt-in by the nature of the project).
    if getattr(args, "practices", None) is not None:
        selected_practices = practices.resolve(ASSETS, args.practices)
    else:
        selected_practices = _read_practices(root) or CORE_PRACTICES

    # policy
    dst_policy = root / ".asdlc" / "policy.yaml"
    if not dst_policy.exists() or args.force:
        tpl = (PKG / "gates" / "policy.yaml").read_text()
        tpl = tpl.replace("%%CHANGES_DIR%%", changes_dir).replace("%%SPECS_DIR%%", specs_dir)
        tpl = tpl.replace("%%SDD_CHOICE%%", args.sdd)
        tpl = tpl.replace("%%PRACTICES%%", ", ".join(selected_practices))
        relaxed = _relaxed_checks(args.sdd)
        if relaxed:
            tpl = _disable_checks(tpl, relaxed)
        dst_policy.write_text(tpl)
        note = f" ({len(relaxed)} spec-shape check(s) disabled — see comment)" if relaxed else ""
        print(f"  {GREEN}+{RESET} .asdlc/policy.yaml            (edit this per client){note}")

    # AGENTS.md / CLAUDE.md — Claude Code never reads AGENTS.md, only
    # CLAUDE.md. If some OTHER selected tool reads AGENTS.md natively
    # (Codex/Cursor/Copilot), generate it as the shared hub and make
    # CLAUDE.md a one-line import — one source of truth, no drift between
    # two copies. If claude-code is the only tool that needs this content,
    # skip AGENTS.md entirely and write the real content straight into
    # CLAUDE.md — no reason to keep a hub file nothing else reads.
    has_native_reader = any(adapters.ADAPTERS[t].reads_agents_md for t in args.tools)
    inline_into_claude = "claude-code" in args.tools and not has_native_reader
    context_file = "CLAUDE.md" if inline_into_claude else "AGENTS.md"

    context_tpl = (ASSETS / "templates" / "AGENTS.md.tpl").read_text()
    context_tpl = context_tpl.replace("{{PROJECT}}", args.project or root.name)
    context_tpl = context_tpl.replace("{{STACK}}", args.stack or "TODO: languages, frameworks, versions")
    context_tpl = context_tpl.replace("{{CHANGES_DIR}}", changes_dir).replace("{{SPECS_DIR}}", specs_dir)
    context_tpl = context_tpl.replace("{{WORKFLOW_NOTE}}", _workflow_note(args.sdd))

    # Practices — copy the selected packs into docs/practices/ and fold a lean
    # `## Practices` pointer section into the context file (or nothing if none
    # were selected). Claude-only repos get @-imports so Claude auto-loads them.
    practices_section = practices.install(
        root, ASSETS, selected_practices,
        inline_for_claude=inline_into_claude, force=args.force,
    )
    context_tpl = context_tpl.replace("{{PRACTICES}}", practices_section)
    if selected_practices:
        print(f"  {GREEN}+{RESET} docs/practices/               ({len(selected_practices)} pack(s), linked from {context_file})")

    agents_md = root / "AGENTS.md"
    if not inline_into_claude:
        if not agents_md.exists() or args.force:
            note = ("It is read natively by Codex, Cursor, Copilot, Gemini CLI, Aider, "
                     "Zed, Windsurf and others. Claude Code never reads this file directly "
                     "— it only reads CLAUDE.md — so `asdlc init --tools claude-code` "
                     "generates a one-line `@AGENTS.md` import there. One source of truth "
                     "either way.")
            agents_md.write_text(context_tpl.replace("{{FILE_NOTE}}", note))
            print(f"  {GREEN}+{RESET} AGENTS.md                     (fill in the TODOs — this is the context contract)")
    elif agents_md.exists():
        # A previous `--tools` combo needed the AGENTS.md hub; this one
        # doesn't. Leaving it behind means it silently goes stale forever —
        # nothing would ever write to it again.
        if args.force:
            agents_md.unlink()
            print(f"  {RED}-{RESET} AGENTS.md                     (removed — content is now inlined into CLAUDE.md instead)")
        else:
            print(f"  {YELLOW}!{RESET} AGENTS.md still exists but nothing reads it now that claude-code is "
                  f"alone — re-run with --force to remove it")

    if "claude-code" in args.tools:
        claude_md = root / "CLAUDE.md"
        if not claude_md.exists() or args.force:
            if inline_into_claude:
                note = ("Claude Code reads this file directly and never reads AGENTS.md — "
                         "since no other selected tool needs a shared AGENTS.md hub, this "
                         "is the one and only copy of this content.")
                claude_md.write_text(context_tpl.replace("{{FILE_NOTE}}", note))
                print(f"  {GREEN}+{RESET} CLAUDE.md                     (fill in the TODOs — this is the context contract)")
            else:
                claude_md.write_text("See @AGENTS.md — this repo's single source of context and workflow rules.\n")
                print(f"  {GREEN}+{RESET} CLAUDE.md                     (pointer — Claude Code does not read AGENTS.md itself)")

    # MCP servers — tool-agnostic (most MCP hosts read project-scoped
    # .mcp.json), so this doesn't belong in adapters/. Which servers a repo
    # actually needs is out of scope for asdlc; ship the empty shell and let
    # AGENTS.md point at it, rather than opining on specific servers/creds.
    mcp_json = root / ".mcp.json"
    if not mcp_json.exists() or args.force:
        mcp_json.write_text((ASSETS / "templates" / "mcp.json.tpl").read_text())
        print(f"  {GREEN}+{RESET} .mcp.json                     (empty — add servers this repo needs)")
    for name in getattr(args, "mcp", None) or []:
        entry = mcp.add(root, ASSETS, name)
        print(f"  {GREEN}+{RESET} .mcp.json: {name:<10} ({entry['display']})")

    # adapters
    for tool in args.tools:
        n = adapters.render_adapter(root, tool, ASSETS, changes_dir, specs_dir,
                                    context_file, force=args.force)
        print(f"  {GREEN}+{RESET} adapter: {tool:<20} ({n} files)")

    # SDD methodology
    if args.sdd != "none":
        sdd.install(root, args.sdd, args.tools, ASSETS,
                    project=args.project, stack=args.stack,
                    changes_dir=changes_dir, specs_dir=specs_dir,
                    context_file=context_file, force=args.force)
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

    # Read back what's actually persisted, not just this invocation's --sdd —
    # a later `asdlc init` re-run (e.g. adding a tool) without repeating --sdd
    # must still reflect whatever front-end this repo already has configured.
    effective_sdd = _read_sdd_choice(root)
    next_step = NEXT_STEP_HINT[effective_sdd]
    gate_note = "" if effective_sdd == "none" else " (asdlc's own spec gates are disabled for this choice — see .asdlc/policy.yaml)"
    print(
        f"\nNext: run `/onboard` in your agent — a one-time codebase skim that "
        f"fills in {context_file} with real facts instead of TODOs, so later "
        f"commands read that instead of re-scanning the repo every time. "
        f"Then tune .asdlc/policy.yaml, and {next_step}.{gate_note}"
    )
    return 0


# --------------------------------------------------------------------------- #
# new
# --------------------------------------------------------------------------- #
def cmd_new(args: argparse.Namespace) -> int:
    root = repo_root()
    changes_dir, _ = _read_artifact_dirs(root)
    cid = slugify(args.change_id)
    folder = root / changes_dir / cid
    if folder.exists():
        print(f"{RED}change '{cid}' already exists{RESET}")
        return 1
    folder.mkdir(parents=True)
    for a in ARTIFACTS:
        text = (ASSETS / "templates" / "change" / a).read_text()
        text = text.replace("{{CHANGE_ID}}", cid)
        text = text.replace("{{TITLE}}", args.change_id)
        (folder / a).write_text(text)
    print(f"{GREEN}created{RESET} {changes_dir}/{cid}/  ({', '.join(ARTIFACTS)})")
    print(
        "\nHand this to whatever agent the client uses:\n"
        f"  \"Read AGENTS.md and {changes_dir}/{cid}/. Fill in proposal.md and spec.md.\n"
        "   Do not write code until spec.md passes `asdlc verify --stage spec`.\""
    )
    return 0


# --------------------------------------------------------------------------- #
# verify — the standard
# --------------------------------------------------------------------------- #
def cmd_verify(args: argparse.Namespace) -> int:
    root = repo_root()
    policy = load_policy(root, PKG)
    changes_dir, specs_dir = _read_artifact_dirs(root)
    files = changed_files(root, args.base)
    ctx = Context(
        root=root,
        policy=policy,
        changed_files=files,
        base=args.base,
        stage=args.stage,
        changes_dir=changes_dir,
        specs_dir=specs_dir,
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
def cmd_doctor(_args: argparse.Namespace) -> int:
    root = repo_root()
    print(f"repo: {root}\n")
    changes_dir, specs_dir = _read_artifact_dirs(root)

    detect = {name: a.commands_dir for name, a in adapters.ADAPTERS.items() if a.commands_dir}
    detected_tools = [tool for tool, path in detect.items() if (root / path).exists()]
    has_native_reader = any(adapters.ADAPTERS[t].reads_agents_md for t in detected_tools)
    inline_into_claude = "claude-code" in detected_tools and not has_native_reader
    context_file = "CLAUDE.md" if inline_into_claude else "AGENTS.md"

    checks = [
        (context_file, (root / context_file).exists()),
        ("policy (.asdlc/policy.yaml)", (root / ".asdlc" / "policy.yaml").exists()),
        ("skills (per-tool)", any(
            next((root / p).glob("*/SKILL.md"), None) is not None
            for p in (".claude/skills", ".codex/skills", ".github/skills", ".cursor/skills")
        )),
        (f"changes dir ({changes_dir})", (root / changes_dir).exists()),
        (f"specs dir ({specs_dir})", (root / specs_dir).exists()),
    ]
    for name, ok in checks:
        print(f"  {GREEN + 'yes' + RESET if ok else RED + 'no ' + RESET}  {name}")

    print("\nagent tooling detected in this repo:")
    if detected_tools:
        for tool in detected_tools:
            print(f"  {GREEN}yes{RESET}  {tool:<12} ({detect[tool]})")
    else:
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

    prac_dir = root / "docs" / "practices"
    installed = sorted(p.stem for p in prac_dir.glob("*.md")) if prac_dir.exists() else []
    print("\npractice packs installed (docs/practices/):")
    if installed:
        print(f"  {GREEN}{len(installed)}{RESET}  {', '.join(installed)}")
    else:
        print(f"  {YELLOW}none{RESET} — run `asdlc init` (installs core) or `--practices all` for domains too")

    stale = []
    for cf in sorted((root / changes_dir).glob("*/")) if (root / changes_dir).exists() else []:
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


# --------------------------------------------------------------------------- #
# report — adoption metrics (git-derived, API-free)
# --------------------------------------------------------------------------- #
def cmd_report(args: argparse.Namespace) -> int:
    root = repo_root()
    policy = load_policy(root, PKG)
    source_globs = policy.get("source_globs") or ["src/**"]
    changes_dir, _ = _read_artifact_dirs(root)
    results_dir = Path(args.results_dir) if args.results_dir else None

    m = report.build(root, since=args.since, results_dir=results_dir,
                     source_globs=source_globs, changes_dir=changes_dir)

    if args.json:
        Path(args.json).write_text(json.dumps(m, indent=2))

    print(f"{DIM}adoption metrics — since {m['since']}  (git history on the current branch){RESET}\n")
    print(f"  merges (PRs to mainline)   {m['merges']}")
    lt = m["lead_time"]
    print(f"  PR lead time median/p90    {lt['median']} / {lt['p90']}   {DIM}[{lt['measured']} measured]{RESET}")
    sc = m["spec_coverage"]
    if sc["pct"] is None:
        print(f"  PRs carrying a spec        {DIM}n/a — no production code changed in window{RESET}")
    else:
        print(f"  PRs carrying a spec        {sc['pct']}%   {DIM}[{sc['with_spec']}/{sc['production_merges']} production PRs]{RESET}")

    vh = m["verify_history"]
    if vh is not None:
        print(f"\n  gate pass-rate             {vh['green_pct']}%   {DIM}[{vh['runs']} verify run(s)]{RESET}")
        for name, n in vh["gate_fails"].items():
            print(f"      {YELLOW}{name}{RESET}: {n} fail(s)")
    else:
        print(f"\n  gate pass-rate             {DIM}n/a — pass --results-dir with archived `asdlc verify --json` files{RESET}")

    print(f"\n  {DIM}not derivable from git alone:{RESET}")
    for k, why in m["unavailable"].items():
        print(f"      {k}: {DIM}{why}{RESET}")

    if m["merges"] == 0:
        print(f"\n{YELLOW}No merges in the window.{RESET} A shallow clone hides history "
              f"(CI needs fetch-depth: 0); or widen it, e.g. --since '1 year ago'.")
    return 0


def cmd_mcp_list(_args: argparse.Namespace) -> int:
    configured = mcp.read_mcp_json(repo_root()).get("mcpServers", {})
    print("MCP catalog (verify against the docs link before rolling out to a client):\n")
    name_w = max(len(n) for n in MCP_CATALOG) + 2
    for name, entry in sorted(MCP_CATALOG.items()):
        mark = f"{GREEN}configured{RESET}" if name in configured else f"{DIM}not configured{RESET}"
        print(f"  {name:<{name_w}} {entry['display']:<32} [{entry['kind']}]  {mark}")
        print(f"  {' ' * name_w} {DIM}{entry['note']}{RESET}")
        print(f"  {' ' * name_w} {DIM}{entry['docs']}{RESET}")
    extra = sorted(set(configured) - set(MCP_CATALOG))
    if extra:
        print(f"\nAlso configured in .mcp.json (not from asdlc's catalog): {', '.join(extra)}")
    return 0


def cmd_mcp_add(args: argparse.Namespace) -> int:
    root = repo_root()
    for name in args.names:
        entry = mcp.add(root, ASSETS, name)
        print(f"  {GREEN}+{RESET} .mcp.json: {name} ({entry['display']}) — {entry['note']}")
        env_vars = sorted(entry["config"].get("env", {}))
        if env_vars:
            print(f"      {YELLOW}set these before it can start:{RESET} {', '.join(env_vars)}")
    return 0


def cmd_mcp_remove(args: argparse.Namespace) -> int:
    root = repo_root()
    ok = True
    for name in args.names:
        if mcp.remove(root, name):
            print(f"  {RED}-{RESET} .mcp.json: {name}")
        else:
            print(f"  {YELLOW}!{RESET} '{name}' wasn't in .mcp.json")
            ok = False
    return 0 if ok else 1


# --------------------------------------------------------------------------- #
# setup wizard — only for `asdlc init` with zero flags, at a real terminal.
# Anything scripted (CI, tests, `--tools ...`) always goes through argparse
# untouched below; this never changes what a flag-driven invocation does. The
# terminal/menu primitives it drives live in tui.py; only the catalog-aware
# orchestration stays here.
# --------------------------------------------------------------------------- #
def _run_wizard(root: Path) -> argparse.Namespace:
    print(f"{GREEN}{tui._banner()}{RESET}")
    print()
    print("No flags? Let's set this repo up interactively.")
    print(f"{DIM}(Scripting it instead? `asdlc init --help`. Menus: ↑/↓ move · space "
          f"toggle · a all · n none · enter confirm; ASDLC_WIZARD_PLAIN=1 to type answers.){RESET}")
    N = 7
    project = tui._prompt("Project name", root.name, step=(1, N))
    stack = tui._prompt("Describe your stack (languages/frameworks) in a few words", step=(2, N))
    tools = tui._prompt_multi("Which agent tool(s) does this repo use?",
                              sorted(adapters.TOOL_NAMES), ["claude-code"], step=(3, N))
    mcp_names = sorted(MCP_CATALOG)
    mcp_choice = tui._prompt_multi(
        "Install any MCP servers? Pointers only — no secrets stored; each person "
        "authenticates in their own agent tool afterwards.",
        ["none", *mcp_names], ["none"],
        blurbs={"none": "skip — run `asdlc mcp add <name>` later if needed",
                **{n: MCP_CATALOG[n]["note"] for n in mcp_names}},
        step=(4, N), exclusive=("none",),
    )
    mcp_choice = [m for m in mcp_choice if m != "none"]
    # Present the packs grouped into category boxes, ordered as grouped() dictates.
    packs = practices.available(ASSETS)
    ordered_practices: list[str] = []
    practice_headers: dict[int, str] = {}
    for label, members in practices.grouped(packs):
        practice_headers[len(ordered_practices)] = label
        ordered_practices += [p.name for p in members]
    practice_choice = tui._prompt_multi(
        "Which engineering practices to install? Core is pre-selected; "
        "add domain packs by the nature of the project.",
        ordered_practices, CORE_PRACTICES,
        blurbs={p.name: p.summary for p in packs},
        headers=practice_headers, step=(5, N),
    )
    ci = tui._prompt_choice("CI provider?", ["github", "gitlab", "none"], "github", step=(6, N))
    sdd_choice = tui._prompt_choice(
        "SDD front-end? Installs the real tool via its own installer and disables "
        "asdlc's own spec gates for it — 'none' keeps asdlc's gates on.",
        SDD_CHOICES, "none", blurbs=SDD_CHOICE_BLURB, step=(7, N),
    )
    # Review before anything is written.
    print()
    summary = [
        ("project", project or root.name),
        ("stack", stack or "(fill in later)"),
        ("tools", ", ".join(tools)),
        ("mcp", ", ".join(mcp_choice) or "none"),
        ("practices", f"{len(practice_choice)} pack(s)" if practice_choice else "none"),
        ("ci", ci),
        ("sdd", sdd_choice),
    ]
    if not tui._confirm("Review setup", summary):
        print(f"{YELLOW}Setup cancelled — nothing was written.{RESET}")
        raise SystemExit(0)
    print()
    return argparse.Namespace(project=project or None, stack=stack or None,
                               tools=tools, ci=ci, sdd=sdd_choice, mcp=mcp_choice,
                               practices=practice_choice, force=False)


def main(argv: list[str] | None = None) -> int:
    raw = sys.argv[1:] if argv is None else argv
    if raw == ["init"] and sys.stdin.isatty():
        return cmd_init(_run_wizard(repo_root()))

    p = argparse.ArgumentParser(prog="asdlc", description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    pi = sub.add_parser("init", help="scaffold the standard into a repo")
    pi.add_argument("--project")
    pi.add_argument("--stack")
    pi.add_argument("--tools", nargs="+", default=["claude-code"],
                    choices=sorted(adapters.TOOL_NAMES))
    pi.add_argument("--ci", default="github", choices=["github", "gitlab", "none"])
    pi.add_argument("--sdd", default="none", choices=SDD_CHOICES,
                    help="SDD methodology to install (shells out to its own installer; kiro is templates-only)")
    pi.add_argument("--practices", nargs="*", choices=PRACTICE_NAMES + list(practices.GROUP_TOKENS),
                    default=None, metavar="NAME",
                    help="practice packs or group tokens core/domain/all "
                         "(default: core; empty list: none)")
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

    prp = sub.add_parser("report", help="adoption metrics from git + archived verify results")
    prp.add_argument("--since", default="90 days ago", help="git date window (default: '90 days ago')")
    prp.add_argument("--results-dir", help="dir of archived `asdlc verify --json` outputs, for gate pass-rate")
    prp.add_argument("--json", help="write machine-readable metrics here")
    prp.set_defaults(func=cmd_report)

    pm = sub.add_parser("mcp", help="manage this repo's .mcp.json against asdlc's MCP catalog")
    mcp_sub = pm.add_subparsers(dest="mcp_cmd", required=True)

    pml = mcp_sub.add_parser("list", help="show the catalog and what's configured here")
    pml.set_defaults(func=cmd_mcp_list)

    pma = mcp_sub.add_parser("add", help="add catalog entries to .mcp.json")
    pma.add_argument("names", nargs="+", choices=sorted(MCP_CATALOG))
    pma.set_defaults(func=cmd_mcp_add)

    pmr = mcp_sub.add_parser("remove", help="remove entries from .mcp.json")
    pmr.add_argument("names", nargs="+")
    pmr.set_defaults(func=cmd_mcp_remove)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
