"""Engineering-practice packs — the standard's opinionated, tool-agnostic
"how we write code here" layer.

Each pack is a self-contained Markdown doc under assets/practices/, whose header
carries three markers:
  - `<!-- summary: … -->`  one-line description, shown in the pointer list.
  - `<!-- tier: … -->`     `core` (universal, installed by default) or `domain`
                           (opt-in by the nature of the project). Drives which
                           packs are pre-selected / installed.
  - `<!-- category: … -->` display grouping (Foundations, Testing & QA, …),
                           orthogonal to tier — used to box the wizard picker and
                           the rendered `## Practices` section.

At `asdlc init` the selected packs are copied into docs/practices/ and referenced
from a lean, grouped `## Practices` section in the context file. Guidance, not a
gate — the point is that agents read them.
"""
from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path

TITLE_RE = re.compile(r"^#\s+(.+?)\s*$", re.M)
SUMMARY_RE = re.compile(r"^<!--\s*summary:\s*(.+?)\s*-->\s*$", re.M)
TIER_RE = re.compile(r"^<!--\s*tier:\s*(\w+)\s*-->\s*$", re.M)
CATEGORY_RE = re.compile(r"^<!--\s*category:\s*(.+?)\s*-->\s*$", re.M)

GROUP_TOKENS = ("core", "domain", "all")

# Canonical display order of the category boxes. A pack names its category; the
# module owns the ordering so packs don't have to agree on it. Anything not
# listed falls into a trailing "Other" box.
CATEGORY_ORDER = [
    "Foundations",
    "Testing & QA",
    "Security & Data",
    "DevOps & Platform",
    "Product & Interface",
]


@dataclass(frozen=True)
class Pack:
    name: str
    title: str
    summary: str
    tier: str
    category: str


def _parse(path: Path) -> Pack:
    text = path.read_text()
    title_m = TITLE_RE.search(text)
    summary_m = SUMMARY_RE.search(text)
    tier_m = TIER_RE.search(text)
    cat_m = CATEGORY_RE.search(text)
    return Pack(
        name=path.stem,
        title=title_m.group(1) if title_m else path.stem,
        summary=summary_m.group(1) if summary_m else "",
        tier=tier_m.group(1) if tier_m else "core",       # untagged => core (safe)
        category=cat_m.group(1) if cat_m else "Other",
    )


def available(assets: Path) -> list[Pack]:
    """Every shipped pack, sorted by name."""
    return [_parse(p) for p in sorted((assets / "practices").glob("*.md"))]


def names(assets: Path, tier: str | None = None) -> list[str]:
    """Pack names, optionally filtered to one tier (e.g. 'core')."""
    return [p.name for p in available(assets) if tier is None or p.tier == tier]


def resolve(assets: Path, tokens: list[str]) -> list[str]:
    """Expand names and/or group tokens (core/domain/all) into a concrete,
    deduped name list, ordered core-first then domain. Unknown tokens dropped."""
    packs = available(assets)
    by_name = {p.name: p for p in packs}
    core = [p.name for p in packs if p.tier == "core"]
    domain = [p.name for p in packs if p.tier == "domain"]
    wanted: set[str] = set()
    for tok in tokens:
        if tok == "core":
            wanted.update(core)
        elif tok == "domain":
            wanted.update(domain)
        elif tok == "all":
            wanted.update(by_name)
        elif tok in by_name:
            wanted.add(tok)
    return [n for n in core if n in wanted] + [n for n in domain if n in wanted]


def grouped(packs: list[Pack]) -> list[tuple[str, list[Pack]]]:
    """(category label, packs) in canonical category order, packs by name,
    empty categories skipped. Used for both the wizard and the section."""
    order = {c: i for i, c in enumerate(CATEGORY_ORDER)}
    labels = sorted({p.category for p in packs},
                    key=lambda c: (order.get(c, len(CATEGORY_ORDER)), c))
    out = []
    for label in labels:
        members = sorted((p for p in packs if p.category == label), key=lambda p: p.name)
        if members:
            out.append((label, members))
    return out


def _section(chosen: list[Pack], inline_for_claude: bool) -> str:
    """The `## Practices` section for the context file — a lean pointer list,
    grouped into the category boxes so the reader can navigate it."""
    lines = [
        "## Practices",
        "",
        "How code is written in this repo. Read the relevant one before you act — "
        "these are standards, not suggestions.",
    ]
    for label, members in grouped(chosen):
        lines += ["", f"**{label}**"]
        for p in members:
            lines.append(f"- [{p.title}](docs/practices/{p.name}.md)"
                         + (f" — {p.summary}" if p.summary else ""))
    if inline_for_claude:
        # Claude Code follows @-imports; AGENTS.md-native tools read the links
        # above instead, so this block is additive, never the only reference.
        lines += ["", "<!-- Claude Code auto-loads these: -->"]
        lines += [f"@docs/practices/{p.name}.md" for p in chosen]
    return "\n".join(lines) + "\n"


def install(root: Path, assets: Path, selected: list[str], *,
            inline_for_claude: bool = False, force: bool = False) -> str:
    """Copy the selected packs into root/docs/practices/ and return the
    `## Practices` section text to inject into the context file. An empty
    selection copies nothing and returns "" so the section collapses cleanly."""
    catalog = {p.name: p for p in available(assets)}
    chosen = [catalog[n] for n in selected if n in catalog]
    if not chosen:
        return ""
    dst = root / "docs" / "practices"
    dst.mkdir(parents=True, exist_ok=True)
    for p in chosen:
        target = dst / f"{p.name}.md"
        if target.exists() and not force:
            continue
        shutil.copy(assets / "practices" / f"{p.name}.md", target)
    return _section(chosen, inline_for_claude)
