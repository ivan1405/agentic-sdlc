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
BOLD, CYAN, REVERSE = "\033[1m", "\033[36m", "\033[7m"
if not sys.stdout.isatty() or os.environ.get("NO_COLOR"):
    GREEN = RED = YELLOW = DIM = RESET = BOLD = CYAN = REVERSE = ""


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


def _prompt(question: str, default: str = "", *, step: tuple[int, int] | None = None) -> str:
    if step is not None:
        _step_header(question, step)
        hint = f" [{default}]" if default else ""
        return input(f"  {DIM}›{RESET}{hint}: ").strip() or default
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
    if raw in (b"a", b"A"):          # select-all shortcut (multi-select only)
        return "ALL"
    if raw in (b"n", b"N"):          # select-none shortcut (multi-select only)
        return "NONE"
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


def _apply_key_multi(cursor: int, selected: frozenset[int], key: str, count: int,
                     exclusive: frozenset[int] = frozenset()) -> tuple[int, frozenset[int], str]:
    """Same idea as _apply_key_single, for the checkbox multi-select — SPACE
    toggles the highlighted row in/out of `selected`.

    `exclusive` holds indices that are mutually exclusive with everything else
    (e.g. a "none" sentinel): checking one clears the rest, and checking any
    normal option clears the exclusive ones."""
    if key == "UP":
        return (cursor - 1) % count, selected, "move"
    if key == "DOWN":
        return (cursor + 1) % count, selected, "move"
    if key == "SPACE":
        if cursor in selected:
            toggled = selected - {cursor}
        elif cursor in exclusive:
            toggled = frozenset({cursor})                 # exclusive on -> only it
        else:
            toggled = (selected | {cursor}) - exclusive   # normal on -> drop exclusives
        return cursor, frozenset(toggled), "toggle"
    if key == "ALL":
        return cursor, frozenset(range(count)) - exclusive, "toggle"
    if key == "NONE":
        return cursor, frozenset(), "toggle"
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


def _vis(s: str) -> int:
    """Visible width — ANSI colour codes take no columns."""
    return len(_ANSI_RE.sub("", s))


def _trunc(text: str, width: int) -> str:
    """Truncate PLAIN text (no ANSI) to `width` visible columns, ellipsizing."""
    return text if len(text) <= width else text[: max(0, width - 1)] + "…"


def _wrap(text: str, width: int) -> list[str]:
    """Greedy word-wrap PLAIN text to `width`; always at least one line."""
    lines: list[str] = []
    cur = ""
    for word in text.split():
        if cur and len(cur) + 1 + len(word) > width:
            lines.append(cur)
            cur = word
        else:
            cur = f"{cur} {word}" if cur else word
    lines.append(cur)
    return lines


# --- Box drawing --------------------------------------------------------
# Content is truncated to the inner width so nothing wraps — that keeps the
# right border aligned and makes the in-place redraw a fixed, stable height.

def _box_width() -> int:
    return max(48, min(shutil.get_terminal_size((80, 24)).columns - 2, 78))


def _row(inner: str, iw: int, highlight: bool = False) -> str:
    body = inner + " " * max(0, iw - _vis(inner))       # pad by visible width
    if highlight:
        body = f"{REVERSE}{body}{RESET}"                 # full-row highlight (inner is plain)
    return f"│ {body} │"


def _topbar(title: str, step: tuple[int, int] | None, w: int) -> str:
    left = f"─ {title} "
    right = f" step {step[0]}/{step[1]} ─" if step else "─"
    fill = "─" * max(0, (w - 2) - len(left) - len(right))
    return "┌" + left + fill + right + "┐"


def _botbar(hint: str, w: int) -> str:
    if not hint:
        return "└" + "─" * (w - 2) + "┘"
    seg = f" {hint} "
    fill = "─" * max(0, (w - 2) - _vis(seg))
    return "└" + fill + seg + "┘"


def _render_menu(prev_lines: int, question: str, options: list[str], cursor: int,
                 selected: frozenset[int] | None, blurbs: dict[str, str] | None,
                 headers: dict[int, str] | None = None, *,
                 title: str = "Agentic SDLC setup", step: tuple[int, int] | None = None) -> int:
    """Redraw the framed menu in place and return its physical-row count.

    `headers` maps an option index to a category label printed above it; the
    cursor row is highlighted; ✓/○ mark checkbox state. Cursor/selection indices
    are unaffected by headers — navigation never has to skip them."""
    if prev_lines:
        sys.stdout.write(f"\033[{prev_lines}A\r\033[J")
    w = _box_width()
    iw = w - 4
    multi = selected is not None
    rows = [_topbar(title, step, w)]

    # subtitle (wrapped), then a right-aligned selected-count on its own line
    for line in _wrap(question, iw):
        rows.append(_row(f"{DIM}{line}{RESET}", iw))
    if multi:
        tag = f"{len(selected)}/{len(options)} selected"
        rows.append(_row(f"{DIM}{' ' * max(0, iw - len(tag))}{tag}{RESET}", iw))
    rows.append(_row("", iw))

    prefix = 2 + (2 if multi else 0)            # "❯ " (+ "✓ ")
    for i, opt in enumerate(options):
        if headers and i in headers:
            if i != 0:
                rows.append(_row("", iw))
            rows.append(_row(f"{BOLD}{CYAN}{headers[i]}{RESET}", iw))
        checked = multi and i in selected
        pointer = "❯" if i == cursor else " "
        name = _trunc(opt, iw - prefix)
        if i == cursor:                          # plain inner; _row reverses the whole row
            mark = ("✓ " if checked else "○ ") if multi else ""
            rows.append(_row(f"{pointer} {mark}{name}", iw, highlight=True))
        else:
            mark = (f"{GREEN}✓{RESET} " if checked else f"{DIM}○{RESET} ") if multi else ""
            rows.append(_row(f"{pointer} {mark}{name}", iw))
        # Full description on its own wrapped, indented line(s) — never trimmed.
        blurb = blurbs.get(opt, "") if blurbs else ""
        if blurb:
            for bl in _wrap(blurb, iw - 4):
                rows.append(_row(f"    {DIM}{bl}{RESET}", iw))

    rows.append(_row("", iw))
    hint = ("↑/↓ move · space toggle · a all · n none · ⏎ confirm" if multi
            else "↑/↓ move · ⏎ confirm")
    rows.append(_botbar(_trunc(hint, w - 4), w))

    sys.stdout.write("\n".join(rows) + "\n")
    sys.stdout.flush()
    cols = shutil.get_terminal_size((80, 24)).columns
    return sum(_display_rows(line, cols) for line in rows)


def _confirm(title: str, pairs: list[tuple[str, str]]) -> bool:
    """Print a boxed review summary and ask to proceed. Default is yes."""
    w = _box_width()
    iw = w - 4
    keyw = max((len(k) for k, _ in pairs), default=0)
    rows = [_topbar(title, None, w), _row("", iw)]
    for k, v in pairs:
        rows.append(_row(f"{DIM}{k.ljust(keyw)}{RESET}  {_trunc(v, iw - keyw - 2)}", iw))
    rows.append(_row("", iw))
    rows.append(_botbar("", w))
    print("\n".join(rows))
    return not input("Proceed? [Y/n]: ").strip().lower().startswith("n")


def _arrow_choice(question: str, options: list[str], default: str,
                  blurbs: dict[str, str] | None = None, *,
                  step: tuple[int, int] | None = None) -> str | None:
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
                prev_lines = _render_menu(prev_lines, question, options, cursor, None, blurbs, step=step)
                cursor, outcome = _apply_key_single(cursor, _read_key(), len(options))
                if outcome == "confirm":
                    return options[cursor]
                if outcome == "quit":
                    return None
    except Exception:
        return None


def _arrow_multi(question: str, options: list[str], default: list[str],
                 blurbs: dict[str, str] | None = None,
                 headers: dict[int, str] | None = None, *,
                 step: tuple[int, int] | None = None,
                 exclusive: frozenset[int] = frozenset()) -> list[str] | None:
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
                prev_lines = _render_menu(prev_lines, question, options, cursor, selected,
                                          blurbs, headers, step=step)
                cursor, selected, outcome = _apply_key_multi(cursor, selected, _read_key(),
                                                             len(options), exclusive)
                if outcome == "confirm":
                    return [opt for i, opt in enumerate(options) if i in selected] or default
                if outcome == "quit":
                    return None
    except Exception:
        return None


def _step_header(question: str, step: tuple[int, int] | None) -> None:
    tag = f"{DIM}step {step[0]}/{step[1]}{RESET}" if step else ""
    print(f"\n{BOLD}{CYAN}{question}{RESET}  {tag}")


def _prompt_choice(question: str, options: list[str], default: str,
                   blurbs: dict[str, str] | None = None, *,
                   step: tuple[int, int] | None = None) -> str:
    picked = _arrow_choice(question, options, default, blurbs, step=step)
    if picked is not None:
        return picked
    _step_header(question, step)
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
                  headers: dict[int, str] | None = None, *,
                  step: tuple[int, int] | None = None,
                  exclusive: tuple[str, ...] = ()) -> list[str]:
    excl_idx = frozenset(i for i, opt in enumerate(options) if opt in exclusive)
    picked = _arrow_multi(question, options, default, blurbs, headers, step=step, exclusive=excl_idx)
    if picked is not None:
        return picked
    _step_header(question, step)
    for i, opt in enumerate(options, 1):
        if headers and (i - 1) in headers:
            print(f"\n  {BOLD}{CYAN}{headers[i - 1]}{RESET}")
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
    # A real choice cancels an exclusive sentinel ("none"), same as the menu.
    if any(p not in exclusive for p in picked):
        picked = [p for p in picked if p not in exclusive]
    return picked or default
