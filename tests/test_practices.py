"""Practices layer: every shipped pack parses; install() copies exactly the
selected packs and returns a lean, correctly-linked `## Practices` section.

    PYTHONPATH=src python3 -m pytest tests/test_practices.py
    ASDLC_UPDATE_GOLDEN=1 PYTHONPATH=src python3 -m pytest tests/test_practices.py  # regen goldens
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import asdlc  # noqa: E402
from asdlc import practices  # noqa: E402

ASSETS = Path(asdlc.__file__).resolve().parent / "assets"
GOLDEN = Path(__file__).resolve().parent / "golden"
ALL = practices.names(ASSETS)


def _check_golden(rel: str, actual: str) -> None:
    path = GOLDEN / rel
    if os.environ.get("ASDLC_UPDATE_GOLDEN"):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(actual)
        pytest.skip(f"regenerated golden {rel}")
    assert path.exists(), f"missing golden {rel} — regen with ASDLC_UPDATE_GOLDEN=1"
    assert actual == path.read_text(), f"practices section drifted from golden {rel}"


def test_packs_exist_and_parse():
    for p in practices.available(ASSETS):
        assert p.title and p.title != p.name, f"{p.name}: missing a '# Title' heading"
        assert p.summary, f"{p.name}: missing a '<!-- summary: … -->' line"
        assert p.tier in ("core", "domain"), f"{p.name}: bad tier {p.tier!r}"
        assert p.category in practices.CATEGORY_ORDER, f"{p.name}: unknown category {p.category!r}"
        body = (ASSETS / "practices" / f"{p.name}.md").read_text()
        assert len(body.strip().splitlines()) > 3, f"{p.name}: body too thin"


def test_tier_counts():
    core = practices.names(ASSETS, "core")
    domain = practices.names(ASSETS, "domain")
    assert len(core) == 8, core
    assert len(domain) == 7, domain
    assert set(core).isdisjoint(domain)
    assert sorted(core + domain) == sorted(ALL)


def test_resolve_expands_tokens_dedups_and_orders_core_first():
    core = practices.names(ASSETS, "core")
    domain = practices.names(ASSETS, "domain")
    assert practices.resolve(ASSETS, ["core"]) == core
    assert practices.resolve(ASSETS, ["domain"]) == domain
    assert practices.resolve(ASSETS, ["all"]) == core + domain
    # names + a group token: deduped, core-first regardless of input order
    assert practices.resolve(ASSETS, ["observability", "core", "immutability"]) == core + ["observability"]
    assert practices.resolve(ASSETS, ["nope"]) == []          # unknown dropped
    assert practices.resolve(ASSETS, []) == []                # empty -> none


def test_names_sorted_and_unique():
    assert ALL == sorted(ALL)
    assert len(ALL) == len(set(ALL))


def test_packs_are_vendor_neutral():
    """No Claude/agent/slash-command/personal references leaked from the seed."""
    banned = ["claude", "codex", "cursor", "copilot", "/simplify", "/plan",
              "sub-agent", "subagent", "qjc-office", "mcp__", "playwright"]
    for p in practices.available(ASSETS):
        text = (ASSETS / "practices" / f"{p.name}.md").read_text().lower()
        for token in banned:
            assert token not in text, f"{p.name}: leaked non-neutral token {token!r}"


def test_grouped_orders_categories_and_skips_empty():
    packs = practices.available(ASSETS)
    labels = [label for label, _ in practices.grouped(packs)]
    assert labels == practices.CATEGORY_ORDER  # all 5 present, in canonical order
    # within a group, packs are name-sorted
    for _, members in practices.grouped(packs):
        assert [m.name for m in members] == sorted(m.name for m in members)
    # a core-only selection yields only the categories that contain core packs
    core = [p for p in packs if p.tier == "core"]
    core_labels = [label for label, _ in practices.grouped(core)]
    assert core_labels == ["Foundations", "Testing & QA", "Security & Data"]


def test_install_copies_only_selected(tmp_path):
    section = practices.install(tmp_path, ASSETS, ["immutability", "test-first"])
    copied = sorted(p.name for p in (tmp_path / "docs" / "practices").glob("*.md"))
    assert copied == ["immutability.md", "test-first.md"]
    assert "(docs/practices/immutability.md)" in section
    assert "(docs/practices/test-first.md)" in section
    assert "boundary-validation" not in section
    assert section.startswith("## Practices")


def test_empty_selection_returns_empty_and_writes_nothing(tmp_path):
    assert practices.install(tmp_path, ASSETS, []) == ""
    assert not (tmp_path / "docs" / "practices").exists()


def test_unknown_names_ignored(tmp_path):
    section = practices.install(tmp_path, ASSETS, ["immutability", "nope"])
    copied = [p.name for p in (tmp_path / "docs" / "practices").glob("*.md")]
    assert copied == ["immutability.md"]
    assert "nope" not in section


def test_claude_inline_emits_imports_but_plain_does_not(tmp_path):
    inline = practices.install(tmp_path, ASSETS, ["immutability"], inline_for_claude=True)
    assert "@docs/practices/immutability.md" in inline
    plain = practices.install(tmp_path, ASSETS, ["immutability"], inline_for_claude=False, force=True)
    assert "@docs/practices/" not in plain


def test_section_snapshot_plain(tmp_path):
    _check_golden("practices.section.txt",
                  practices.install(tmp_path, ASSETS, ALL, inline_for_claude=False, force=True))


def test_section_snapshot_claude(tmp_path):
    _check_golden("practices.section.claude.txt",
                  practices.install(tmp_path, ASSETS, ALL, inline_for_claude=True, force=True))
