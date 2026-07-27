"""Terminal UI primitives for the `asdlc init` setup wizard.

Extracted from cli.py so the CLI's command logic stays under the project's own
file-size rule. Nothing here knows about asdlc's catalogs or commands — it is
pure terminal/menu machinery plus the ANSI colour constants the CLI renders
with. `_run_wizard` (which *does* know about those catalogs) stays in cli.py and
calls into this module.

The key-decoding and cursor/selection transitions are pure functions so they're
unit-testable without a real terminal; only the render/raw-mode loop around them
is not.
"""
from __future__ import annotations

import contextlib
import os
import re
import select
import shutil
import sys

# Arrow-key wizard input needs raw terminal access, which is platform-specific
# and has no stdlib equivalent on the other OS — hence the try/except pair
# instead of one import. _menu_supported() checks whichever of these landed.
try:
    import termios
    import tty
except ImportError:  # Windows
    termios = None  # type: ignore[assignment]
    tty = None  # type: ignore[assignment]

try:
    import msvcrt
except ImportError:  # POSIX
    msvcrt = None  # type: ignore[assignment]


GREEN, RED, YELLOW, DIM, RESET = "\033[32m", "\033[31m", "\033[33m", "\033[2m", "\033[0m"
if not sys.stdout.isatty() or os.environ.get("NO_COLOR"):
    GREEN = RED = YELLOW = DIM = RESET = ""


# Built from centered pieces, not hand-counted spaces — a hardcoded ASCII-art
# string is one string-length change away from misaligned borders.
_ASDLC_LETTERS = {
    "A": [" █████╗ ", "██╔══██╗", "███████║", "██╔══██║", "██║  ██║", "╚═╝  ╚═╝"],
    "S": ["███████╗", "██╔════╝", "███████╗", "╚════██║", "███████║", "╚══════╝"],
    "D": ["██████╗ ", "██╔══██╗", "██║  ██║", "██║  ██║", "██████╔╝", "╚═════╝ "],
    "L": ["██╗     ", "██║     ", "██║     ", "██║     ", "███████╗", "╚══════╝"],
    "C": [" ██████╗", "██╔════╝", "██║     ", "██║     ", "╚██████╗", " ╚═════╝"],
}


def _banner() -> str:
    art_rows = ["".join(_ASDLC_LETTERS[ch][r] for ch in "ASDLC") for r in range(6)]
    tagline = "Agentic SDLC — setup wizard"
    width = max(len(r) for r in art_rows) + 4
    top, bottom = "╔" + "═" * width + "╗", "╚" + "═" * width + "╝"
    blank = f"║{' ' * width}║"
    lines = [top, blank, *(f"║{r.center(width)}║" for r in art_rows),
              blank, f"║{tagline.center(width)}║", blank, bottom]
    return "\n".join(lines)


def _prompt(question: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    return input(f"{question}{suffix}: ").strip() or default


# --- Arrow-key menu -----------------------------------------------------
#
# _menu_supported() gates this entirely: piped/redirected stdin (CI, the
# test suite's mocked input()) or ASDLC_WIZARD_PLAIN=1 fall straight through
# to the type-a-number prompts below, unchanged.

def _menu_supported() -> bool:
    if os.environ.get("ASDLC_WIZARD_PLAIN"):
        return False
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        return False
    return msvcrt is not None if os.name == "nt" else termios is not None


@contextlib.contextmanager
def _raw_mode():
    if os.name == "nt":
        yield
        return
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        # cbreak, not setraw: raw mode also disables output post-processing
        # (OPOST), so a bare "\n" stops implying a carriage return and every
        # redrawn line drifts right of the last. cbreak only turns off
        # canonical/echo input handling, which is all we need for one-key-
        # at-a-time reads. (It also leaves ISIG on, so Ctrl-C raises
        # KeyboardInterrupt normally instead of us having to fake it.)
        tty.setcbreak(fd)
        yield
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def _getch_posix() -> bytes:
    fd = sys.stdin.fileno()
    b = os.read(fd, 1)
    # Arrow keys arrive as a 3-byte escape sequence (ESC [ A/B/C/D) sent back
    # to back; a lone Escape keypress is just the one byte with nothing
    # following, which the short select() timeout distinguishes.
    if b == b"\x1b" and select.select([fd], [], [], 0.05)[0]:
        b += os.read(fd, 1)
        if b == b"\x1b[" and select.select([fd], [], [], 0.05)[0]:
            b += os.read(fd, 1)
    return b


def _getch_windows() -> bytes:
    b = msvcrt.getch()
    if b in (b"\xe0", b"\x00"):  # arrow/function key prefix
        b += msvcrt.getch()
    return b


def _decode_key(raw: bytes) -> str:
    """Normalize a raw keypress — a POSIX escape sequence or a Windows
    msvcrt.getch() pair — into UP/DOWN/ENTER/SPACE/QUIT. Anything else
    decodes to "" and is ignored by the menu loop."""
    if raw in (b"\r", b"\n"):
        return "ENTER"
    if raw == b" ":
        return "SPACE"
    if raw in (b"\x03", b"\x1b"):  # Ctrl-C, or Escape with nothing following
        return "QUIT"
    if raw in (b"\x1b[A", b"\xe0H", b"\x00H"):
        return "UP"
    if raw in (b"\x1b[B", b"\xe0P", b"\x00P"):
        return "DOWN"
    return ""


def _read_key() -> str:
    raw = _getch_windows() if os.name == "nt" else _getch_posix()
    return _decode_key(raw)


def _apply_key_single(cursor: int, key: str, count: int) -> tuple[int, str]:
    """One step of the single-select menu: given the highlighted index and a
    decoded key, returns (new_cursor, outcome) — outcome is 'move', 'confirm',
    'quit', or 'noop'."""
    if key == "UP":
        return (cursor - 1) % count, "move"
    if key == "DOWN":
        return (cursor + 1) % count, "move"
    if key == "ENTER":
        return cursor, "confirm"
    if key == "QUIT":
        return cursor, "quit"
    return cursor, "noop"


def _apply_key_multi(cursor: int, selected: frozenset[int], key: str,
                     count: int) -> tuple[int, frozenset[int], str]:
    """Same idea as _apply_key_single, for the checkbox multi-select — SPACE
    toggles the highlighted row in/out of `selected`."""
    if key == "UP":
        return (cursor - 1) % count, selected, "move"
    if key == "DOWN":
        return (cursor + 1) % count, selected, "move"
    if key == "SPACE":
        toggled = (selected - {cursor}) if cursor in selected else (selected | {cursor})
        return cursor, toggled, "toggle"
    if key == "ENTER":
        return cursor, selected, "confirm"
    if key == "QUIT":
        return cursor, selected, "quit"
    return cursor, selected, "noop"


_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _display_rows(line: str, cols: int) -> int:
    """Physical terminal rows a single logical line occupies at width `cols`.

    A long line (e.g. an option blurb) wraps onto multiple rows; the in-place
    redraw must move the cursor up by the *physical* row count, not the logical
    line count, or wrapped overflow is left behind on every keypress. ANSI
    colour codes take no columns; an empty line still occupies one row."""
    visible = _ANSI_RE.sub("", line)
    if not visible:
        return 1
    return -(-len(visible) // max(1, cols))  # ceil division


def _render_menu(prev_lines: int, question: str, options: list[str], cursor: int,
                 selected: frozenset[int] | None, blurbs: dict[str, str] | None,
                 headers: dict[int, str] | None = None) -> int:
    """Redraw the menu in place — clear what the previous call printed, then
    print the current state — and return the physical-row count for next time.

    `headers` maps an option index to a group label printed above it (the
    category boxes). Headers are display-only — cursor/selection indices are
    unaffected, so navigation logic never has to skip them."""
    if prev_lines:
        sys.stdout.write(f"\033[{prev_lines}A\r\033[J")
    rendered = ["", question]
    for i, opt in enumerate(options):
        if headers and i in headers:
            if i != 0:
                rendered.append("")          # blank line separates the boxes
            rendered.append(f"  {YELLOW}{headers[i]}{RESET}")
        pointer = "❯" if i == cursor else " "
        box = "" if selected is None else ("[x] " if i in selected else "[ ] ")
        style, reset = (GREEN, RESET) if i == cursor else ("", "")
        rendered.append(f"  {style}{pointer} {box}{opt}{reset}")
        if blurbs and opt in blurbs:
            rendered.append(f"     {DIM}{blurbs[opt]}{RESET}")
    hint = "space to toggle, enter to confirm" if selected is not None else "enter to confirm"
    rendered.append(f"{DIM}(↑/↓ to move, {hint}){RESET}")
    sys.stdout.write("\n".join(rendered) + "\n")
    sys.stdout.flush()
    # Count physical rows (lines may wrap at the terminal width), so the next
    # call's cursor-up clears exactly what we printed.
    cols = shutil.get_terminal_size((80, 24)).columns
    return sum(_display_rows(line, cols) for line in rendered)


def _arrow_choice(question: str, options: list[str], default: str,
                  blurbs: dict[str, str] | None = None) -> str | None:
    """Interactive arrow-key single-select. Returns the chosen option, or
    None if the terminal can't support it — callers fall back to the
    type-a-number prompt in that case."""
    if not _menu_supported():
        return None
    cursor = options.index(default) if default in options else 0
    prev_lines = 0
    try:
        with _raw_mode():
            while True:
                prev_lines = _render_menu(prev_lines, question, options, cursor, None, blurbs)
                cursor, outcome = _apply_key_single(cursor, _read_key(), len(options))
                if outcome == "confirm":
                    return options[cursor]
                if outcome == "quit":
                    return None
    except Exception:
        return None


def _arrow_multi(question: str, options: list[str], default: list[str],
                 blurbs: dict[str, str] | None = None,
                 headers: dict[int, str] | None = None) -> list[str] | None:
    """Interactive arrow-key checkbox multi-select. Returns the picked
    options, or None if the terminal can't support it."""
    if not _menu_supported():
        return None
    cursor = 0
    selected = frozenset(i for i, opt in enumerate(options) if opt in default)
    prev_lines = 0
    try:
        with _raw_mode():
            while True:
                prev_lines = _render_menu(prev_lines, question, options, cursor, selected, blurbs, headers)
                cursor, selected, outcome = _apply_key_multi(cursor, selected, _read_key(), len(options))
                if outcome == "confirm":
                    return [opt for i, opt in enumerate(options) if i in selected] or default
                if outcome == "quit":
                    return None
    except Exception:
        return None


def _prompt_choice(question: str, options: list[str], default: str,
                   blurbs: dict[str, str] | None = None) -> str:
    picked = _arrow_choice(question, options, default, blurbs)
    if picked is not None:
        return picked
    print(f"\n{question}")
    for i, opt in enumerate(options, 1):
        print(f"  {i}. {opt}{'  (default)' if opt == default else ''}")
        if blurbs and opt in blurbs:
            print(f"     {DIM}{blurbs[opt]}{RESET}")
    ans = input(f"choice [1-{len(options)}, default {default}]: ").strip()
    if not ans:
        return default
    if ans.isdigit() and 1 <= int(ans) <= len(options):
        return options[int(ans) - 1]
    if ans in options:
        return ans
    print(f"  {YELLOW}unrecognized — using default: {default}{RESET}")
    return default


def _prompt_multi(question: str, options: list[str], default: list[str],
                  blurbs: dict[str, str] | None = None,
                  headers: dict[int, str] | None = None) -> list[str]:
    picked = _arrow_multi(question, options, default, blurbs, headers)
    if picked is not None:
        return picked
    print(f"\n{question}")
    for i, opt in enumerate(options, 1):
        if headers and (i - 1) in headers:
            print(f"\n  {YELLOW}{headers[i - 1]}{RESET}")
        print(f"  {i}. {opt}{'  (default)' if opt in default else ''}")
        if blurbs and opt in blurbs:
            print(f"     {DIM}{blurbs[opt]}{RESET}")
    ans = input(f"choices, comma-separated [default: {','.join(default)}]: ").strip()
    if not ans:
        return default
    picked = []
    for tok in (t.strip() for t in ans.split(",")):
        if tok.isdigit() and 1 <= int(tok) <= len(options):
            picked.append(options[int(tok) - 1])
        elif tok in options:
            picked.append(tok)
    return picked or default
