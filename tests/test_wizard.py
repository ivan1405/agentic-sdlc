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
from asdlc import cli  # noqa: E402


def _answer(monkeypatch, answers: list[str]):
    it = iter(answers)
    monkeypatch.setattr("builtins.input", lambda prompt="": next(it))


def test_wizard_parses_multiselect_and_choice_by_number(monkeypatch, tmp_path):
    _answer(monkeypatch, ["demo-project", "Python 3.12, FastAPI", "1,3", "2", "1"])
    ns = cli._run_wizard(tmp_path)
    assert ns.project == "demo-project"
    assert ns.stack == "Python 3.12, FastAPI"
    assert ns.tools == ["claude-code", "copilot"]
    assert ns.ci == "gitlab"
    assert ns.sdd == "none"
    assert ns.force is False


def test_wizard_parses_by_name_not_just_number(monkeypatch, tmp_path):
    _answer(monkeypatch, ["", "", "codex,cursor", "none", "kiro"])
    ns = cli._run_wizard(tmp_path)
    assert ns.project == tmp_path.name  # blank -> default (repo dir name)
    assert ns.stack is None
    assert ns.tools == ["codex", "cursor"]
    assert ns.ci == "none"
    assert ns.sdd == "kiro"


def test_wizard_blank_answers_use_defaults(monkeypatch, tmp_path):
    _answer(monkeypatch, ["", "", "", "", ""])
    ns = cli._run_wizard(tmp_path)
    assert ns.tools == ["claude-code"]
    assert ns.ci == "github"
    assert ns.sdd == "none"


def test_decode_key_recognizes_posix_and_windows_arrow_sequences():
    assert cli._decode_key(b"\x1b[A") == "UP"
    assert cli._decode_key(b"\xe0H") == "UP"
    assert cli._decode_key(b"\x00H") == "UP"
    assert cli._decode_key(b"\x1b[B") == "DOWN"
    assert cli._decode_key(b"\xe0P") == "DOWN"
    assert cli._decode_key(b"\r") == "ENTER"
    assert cli._decode_key(b" ") == "SPACE"
    assert cli._decode_key(b"\x1b") == "QUIT"  # bare Escape, no sequence following
    assert cli._decode_key(b"\x03") == "QUIT"  # Ctrl-C
    assert cli._decode_key(b"x") == ""  # unrecognized keys are ignored


def test_apply_key_single_moves_wraps_and_confirms():
    assert cli._apply_key_single(0, "DOWN", 3) == (1, "move")
    assert cli._apply_key_single(2, "DOWN", 3) == (0, "move")  # wraps past the end
    assert cli._apply_key_single(0, "UP", 3) == (2, "move")  # wraps before the start
    assert cli._apply_key_single(1, "ENTER", 3) == (1, "confirm")
    assert cli._apply_key_single(1, "QUIT", 3) == (1, "quit")
    assert cli._apply_key_single(1, "", 3) == (1, "noop")


def test_apply_key_multi_toggles_selection_independent_of_cursor():
    cursor, selected, outcome = cli._apply_key_multi(0, frozenset(), "SPACE", 3)
    assert (cursor, selected, outcome) == (0, frozenset({0}), "toggle")
    cursor, selected, outcome = cli._apply_key_multi(0, selected, "SPACE", 3)
    assert (cursor, selected, outcome) == (0, frozenset(), "toggle")  # toggles back off
    cursor, selected, outcome = cli._apply_key_multi(1, frozenset({0}), "DOWN", 3)
    assert (cursor, selected, outcome) == (2, frozenset({0}), "move")  # move leaves selection alone
    assert cli._apply_key_multi(1, frozenset({0}), "ENTER", 3) == (1, frozenset({0}), "confirm")
    assert cli._apply_key_multi(1, frozenset({0}), "QUIT", 3) == (1, frozenset({0}), "quit")


def test_arrow_menus_fall_back_to_none_when_not_a_tty(monkeypatch):
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: False)
    assert cli._arrow_choice("q?", ["a", "b"], "a") is None
    assert cli._arrow_multi("q?", ["a", "b"], ["a"]) is None


def test_wizard_output_feeds_cmd_init_end_to_end(monkeypatch, tmp_path):
    import subprocess

    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@t.io"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
    (tmp_path / "README.md").write_text("#\n")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=tmp_path, check=True)

    monkeypatch.setattr(cli, "repo_root", lambda start=None: tmp_path)
    _answer(monkeypatch, ["demo", "", "1", "3", "1"])  # claude-code only, ci none, sdd none
    ns = cli._run_wizard(tmp_path)
    assert cli.cmd_init(ns) == 0

    assert (tmp_path / "CLAUDE.md").exists()
    assert not (tmp_path / "AGENTS.md").exists()  # claude-code alone: inlined into CLAUDE.md
    assert (tmp_path / ".claude" / "commands" / "propose.md").exists()
