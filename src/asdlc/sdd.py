"""Install an SDD methodology (OpenSpec, Spec Kit, BMAD, Kiro) into a client repo.

These are not asdlc's to own — each is a separately-maintained project with its
own release cadence ("rented, swappable", per the README). For the three that
ship a real CLI, asdlc shells out to the vendor's own installer instead of
vendoring a copy that would drift immediately. Kiro has no CLI, just steering
files, so those are rendered directly from assets/templates/kiro/.

Flag names on the vendor side have already drifted across doc versions we
found while building this (Spec Kit: --ai vs --integration; BMAD: --ide vs
--tools) — expect this to need occasional correction against whatever version
is actually installed. Failures here are never swallowed: the child's own
stdout/stderr reaches the terminal, and a non-zero exit re-raises naming the
exact command that failed.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

SDD_TOOLS = {
    "openspec": {
        "check_binary": "npx",
        "install_hint": "requires Node.js (npx) on PATH",
        "docs": "https://github.com/Fission-AI/OpenSpec",
        "tool_map": {
            "claude-code": "claude",
            "codex": "codex",
            "copilot": "github-copilot",
            "cursor": "cursor",
        },
    },
    "speckit": {
        "check_binary": "uv",
        "install_hint": "requires uv (https://astral.sh/uv) on PATH",
        "docs": "https://github.com/github/spec-kit",
        "tool_map": {
            "claude-code": "claude",
            "codex": "codex",
            "copilot": "copilot",
            "cursor": "cursor",
        },
    },
    "bmad": {
        "check_binary": "npx",
        "install_hint": "requires Node.js (npx) on PATH",
        "docs": "https://github.com/bmad-code-org/BMAD-METHOD",
        # confirmed against `npx bmad-method install --list-tools`.
        "tool_map": {
            "claude-code": "claude-code",
            "codex": "codex",
            "copilot": "github-copilot",
            "cursor": "cursor",
        },
    },
}


def _mapped_tools(tool_map: dict[str, str], tools: list[str]) -> list[str]:
    return [tool_map[t] for t in tools if t in tool_map]


def _run(cmd: list[str], root: Path) -> None:
    try:
        subprocess.run(cmd, cwd=root, check=True)
    except subprocess.CalledProcessError as e:
        raise SystemExit(f"command failed ({e.returncode}): {' '.join(cmd)}") from e
    except FileNotFoundError as e:
        raise SystemExit(f"command not found: {' '.join(cmd)}") from e


def _require(binary: str, hint: str, docs: str) -> None:
    if shutil.which(binary) is None:
        raise SystemExit(f"'{binary}' not found on PATH — {hint}. See {docs}")


def _install_openspec(root: Path, tools: list[str]) -> None:
    cfg = SDD_TOOLS["openspec"]
    _require(cfg["check_binary"], cfg["install_hint"], cfg["docs"])
    mapped = _mapped_tools(cfg["tool_map"], tools)
    _run(["npx", "-y", "@fission-ai/openspec@latest", "init", ".",
          "--tools", ",".join(mapped) if mapped else "none"], root)


def _install_speckit(root: Path, tools: list[str]) -> None:
    cfg = SDD_TOOLS["speckit"]
    _require(cfg["check_binary"], cfg["install_hint"], cfg["docs"])
    _run(["uv", "tool", "install", "specify-cli",
          "--from", "git+https://github.com/github/spec-kit.git"], root)
    mapped = _mapped_tools(cfg["tool_map"], tools)
    cmd = ["specify", "init", "--here", "--force"]
    if mapped:
        cmd += ["--integration", mapped[0]]
    _run(cmd, root)


def _install_bmad(root: Path, tools: list[str]) -> None:
    # NOTE: BMAD's own docs say --yes + --tools is enough for a fully
    # non-interactive install, but it has been observed to still show one
    # "installation directory" confirmation prompt regardless. Harmless for a
    # real user at a real terminal (this subprocess call doesn't capture
    # stdin/stdout, so the prompt reaches them normally) — but it means this
    # path can't be driven from a script with no TTY attached (see
    # tests/test_sdd.sh).
    cfg = SDD_TOOLS["bmad"]
    _require(cfg["check_binary"], cfg["install_hint"], cfg["docs"])
    mapped = _mapped_tools(cfg["tool_map"], tools)
    if not mapped:
        raise SystemExit(
            f"none of --tools {tools} map to a BMAD tool ID (known: {sorted(cfg['tool_map'])}). "
            f"Run `npx bmad-method install --list-tools` to see all supported IDs."
        )
    # --tools is required for a non-interactive (--yes) fresh install.
    _run(["npx", "bmad-method", "install", "--yes", "--tools", ",".join(mapped)], root)


def _install_kiro(root: Path, kiro_templates: Path, project: str, stack: str,
                   changes_dir: str, specs_dir: str, force: bool) -> None:
    dst = root / ".kiro" / "steering"
    dst.mkdir(parents=True, exist_ok=True)
    for tpl in sorted(kiro_templates.glob("*.md.tpl")):
        target = dst / tpl.name.removesuffix(".tpl")
        if target.exists() and not force:
            continue
        text = (tpl.read_text()
                 .replace("{{PROJECT}}", project)
                 .replace("{{STACK}}", stack)
                 .replace("{{CHANGES_DIR}}", changes_dir)
                 .replace("{{SPECS_DIR}}", specs_dir))
        target.write_text(text)


def install(root: Path, choice: str, tools: list[str], assets: Path,
            project: str = "", stack: str = "",
            changes_dir: str = "openspec/changes", specs_dir: str = "openspec/specs",
            force: bool = False) -> None:
    if choice == "none":
        return
    if choice == "kiro":
        _install_kiro(root, assets / "templates" / "kiro",
                      project or root.name,
                      stack or "TODO: languages, frameworks, versions",
                      changes_dir, specs_dir, force)
        return
    if choice == "openspec":
        _install_openspec(root, tools)
    elif choice == "speckit":
        _install_speckit(root, tools)
    elif choice == "bmad":
        _install_bmad(root, tools)
    else:
        raise SystemExit(f"unknown --sdd '{choice}'. known: none, {', '.join(sorted(SDD_TOOLS))}, kiro")
