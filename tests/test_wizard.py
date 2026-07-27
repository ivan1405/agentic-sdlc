"""The interactive setup wizard (`asdlc init` with zero flags, at a real
terminal) is gated behind `sys.stdin.isatty()`, which a bash-driven test can't
reliably simulate across platforms (macOS `script` doesn't forward piped
stdin the way Linux's does). So this exercises `_run_wizard`'s prompt parsing
and its handoff into `cmd_init` directly, with `input()` mocked — the same
approach used to hand-verify this feature originally.

    python3 -m pytest tests/test_wizard.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from asdlc import cli, tui  # noqa: E402


def _answer(monkeypatch, answers: list[str]):
    it = iter(answers)
    monkeypatch.setattr("builtins.input", lambda prompt="": next(it))


# Wizard prompt order: project, stack, tools, mcp, practices, ci, sdd, then a
# final "Proceed? [Y/n]" confirmation ("" => yes). Practices blank => core default.
def test_wizard_parses_multiselect_and_choice_by_number(monkeypatch, tmp_path):
    _answer(monkeypatch, ["demo-project", "Python 3.12, FastAPI", "1,3", "", "", "2", "1", ""])
    ns = cli._run_wizard(tmp_path)
    assert ns.project == "demo-project"
    assert ns.stack == "Python 3.12, FastAPI"
    assert ns.tools == ["claude-code", "copilot"]
    assert ns.mcp == []  # blank -> "none" -> filtered out
    assert ns.practices == cli.CORE_PRACTICES  # blank -> default (core tier)
    assert ns.ci == "gitlab"
    assert ns.sdd == "none"
    assert ns.force is False


def test_wizard_parses_by_name_not_just_number(monkeypatch, tmp_path):
    _answer(monkeypatch, ["", "", "codex,cursor", "atlassian", "", "none", "kiro", ""])
    ns = cli._run_wizard(tmp_path)
    assert ns.project == tmp_path.name  # blank -> default (repo dir name)
    assert ns.stack is None
    assert ns.tools == ["codex", "cursor"]
    assert ns.mcp == ["atlassian"]
    assert ns.practices == cli.CORE_PRACTICES
    assert ns.ci == "none"
    assert ns.sdd == "kiro"


def test_wizard_blank_answers_use_defaults(monkeypatch, tmp_path):
    _answer(monkeypatch, ["", "", "", "", "", "", "", ""])
    ns = cli._run_wizard(tmp_path)
    assert ns.tools == ["claude-code"]
    assert ns.mcp == []
    assert ns.practices == cli.CORE_PRACTICES
    assert ns.ci == "github"
    assert ns.sdd == "none"


def test_decode_key_recognizes_posix_and_windows_arrow_sequences():
    assert tui._decode_key(b"\x1b[A") == "UP"
    assert tui._decode_key(b"\xe0H") == "UP"
    assert tui._decode_key(b"\x00H") == "UP"
    assert tui._decode_key(b"\x1b[B") == "DOWN"
    assert tui._decode_key(b"\xe0P") == "DOWN"
    assert tui._decode_key(b"\r") == "ENTER"
    assert tui._decode_key(b" ") == "SPACE"
    assert tui._decode_key(b"\x1b") == "QUIT"  # bare Escape, no sequence following
    assert tui._decode_key(b"\x03") == "QUIT"  # Ctrl-C
    assert tui._decode_key(b"x") == ""  # unrecognized keys are ignored


def test_apply_key_single_moves_wraps_and_confirms():
    assert tui._apply_key_single(0, "DOWN", 3) == (1, "move")
    assert tui._apply_key_single(2, "DOWN", 3) == (0, "move")  # wraps past the end
    assert tui._apply_key_single(0, "UP", 3) == (2, "move")  # wraps before the start
    assert tui._apply_key_single(1, "ENTER", 3) == (1, "confirm")
    assert tui._apply_key_single(1, "QUIT", 3) == (1, "quit")
    assert tui._apply_key_single(1, "", 3) == (1, "noop")


def test_apply_key_multi_toggles_selection_independent_of_cursor():
    cursor, selected, outcome = tui._apply_key_multi(0, frozenset(), "SPACE", 3)
    assert (cursor, selected, outcome) == (0, frozenset({0}), "toggle")
    cursor, selected, outcome = tui._apply_key_multi(0, selected, "SPACE", 3)
    assert (cursor, selected, outcome) == (0, frozenset(), "toggle")  # toggles back off
    cursor, selected, outcome = tui._apply_key_multi(1, frozenset({0}), "DOWN", 3)
    assert (cursor, selected, outcome) == (2, frozenset({0}), "move")  # move leaves selection alone
    assert tui._apply_key_multi(1, frozenset({0}), "ENTER", 3) == (1, frozenset({0}), "confirm")
    assert tui._apply_key_multi(1, frozenset({0}), "QUIT", 3) == (1, frozenset({0}), "quit")


def test_display_rows_counts_wrapping_not_logical_lines():
    # The redraw bug: a wrapping blurb occupies more physical rows than the one
    # logical line it is, so the cursor-up must use physical rows.
    assert tui._display_rows("", 80) == 1                 # empty line still one row
    assert tui._display_rows("x" * 10, 10) == 1           # exact fit
    assert tui._display_rows("x" * 30, 10) == 3           # wraps to 3
    assert tui._display_rows("x" * 31, 10) == 4           # partial 4th row
    assert tui._display_rows("\x1b[32mhi\x1b[0m", 80) == 1  # ANSI codes take no columns
    assert tui._display_rows("y" * 25, 10) == 3           # visible length drives it


def test_render_menu_adds_rows_for_group_headers(capsys):
    opts = ["a", "b", "c"]
    base = tui._render_menu(0, "q?", opts, 0, frozenset(), None, None)
    withh = tui._render_menu(0, "q?", opts, 0, frozenset(), None, {0: "Box A", 2: "Box B"})
    capsys.readouterr()  # swallow the rendered output
    assert withh > base, "group headers should add printed rows to the menu"


def test_render_box_lines_are_equal_width(capsys):
    """Every rendered row must be the same visible width, or the right border
    stair-steps. Guards the truncate/pad logic against long blurbs and headers."""
    opts = ["short", "a-much-longer-option-name-than-usual"]
    tui._render_menu(0, "A long enough question to wrap across more than one line inside the box.",
                     opts, 1, frozenset({0}),
                     {opts[1]: "a very long blurb " * 8}, {0: "Group One"}, step=(3, 7))
    out = capsys.readouterr().out
    widths = {len(tui._ANSI_RE.sub("", ln)) for ln in out.splitlines() if ln}
    assert len(widths) == 1, f"box rows misaligned: widths={widths}"


def test_apply_key_multi_select_all_and_none():
    assert tui._apply_key_multi(0, frozenset(), "ALL", 3) == (0, frozenset({0, 1, 2}), "toggle")
    assert tui._apply_key_multi(1, frozenset({0, 1, 2}), "NONE", 3) == (1, frozenset(), "toggle")


def test_apply_key_multi_exclusive_sentinel():
    ex = frozenset({0})  # index 0 is a mutually-exclusive "none"
    # checking a normal option clears the exclusive one
    assert tui._apply_key_multi(1, frozenset({0}), "SPACE", 3, ex) == (1, frozenset({1}), "toggle")
    # checking the exclusive option clears everything else
    assert tui._apply_key_multi(0, frozenset({1, 2}), "SPACE", 3, ex) == (0, frozenset({0}), "toggle")
    # select-all skips the exclusive option
    assert tui._apply_key_multi(0, frozenset(), "ALL", 3, ex) == (0, frozenset({1, 2}), "toggle")


def test_prompt_multi_fallback_drops_exclusive_when_real_choice(monkeypatch, capsys):
    monkeypatch.setenv("ASDLC_WIZARD_PLAIN", "1")   # force the numbered fallback
    monkeypatch.setattr("builtins.input", lambda *a, **k: "none, atlassian")
    picked = tui._prompt_multi("q?", ["none", "atlassian", "github"], ["none"],
                               exclusive=("none",))
    capsys.readouterr()
    assert picked == ["atlassian"]   # "none" dropped once a real server is chosen


def test_decode_key_maps_select_all_none():
    assert tui._decode_key(b"a") == "ALL"
    assert tui._decode_key(b"n") == "NONE"


def test_confirm_defaults_to_yes_and_honors_no(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda *a, **k: "")      # blank -> proceed
    assert tui._confirm("Review", [("k", "v")]) is True
    monkeypatch.setattr("builtins.input", lambda *a, **k: "n")     # explicit no
    assert tui._confirm("Review", [("k", "v")]) is False
    capsys.readouterr()


def test_arrow_menus_fall_back_to_none_when_not_a_tty(monkeypatch):
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: False)
    assert tui._arrow_choice("q?", ["a", "b"], "a") is None
    assert tui._arrow_multi("q?", ["a", "b"], ["a"]) is None


def test_wizard_output_feeds_cmd_init_end_to_end(monkeypatch, tmp_path):
    import subprocess

    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@t.io"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
    (tmp_path / "README.md").write_text("#\n")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=tmp_path, check=True)

    monkeypatch.setattr(cli, "repo_root", lambda start=None: tmp_path)
    # claude-code only, mcp: github, practices: core (blank), ci none, sdd none, confirm
    _answer(monkeypatch, ["demo", "", "1", "github", "", "3", "1", ""])
    ns = cli._run_wizard(tmp_path)
    assert cli.cmd_init(ns) == 0

    assert (tmp_path / "CLAUDE.md").exists()
    assert not (tmp_path / "AGENTS.md").exists()  # claude-code alone: inlined into CLAUDE.md
    assert (tmp_path / ".claude" / "commands" / "propose.md").exists()
    assert "github" in cli.mcp.read_mcp_json(tmp_path)["mcpServers"]
    # practices installed and linked from the (claude-inline) context file
    assert (tmp_path / "docs" / "practices" / "immutability.md").exists()
    assert "## Practices" in (tmp_path / "CLAUDE.md").read_text()
