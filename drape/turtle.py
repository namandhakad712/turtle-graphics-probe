"""A tiny, safe Turtle interpreter.

We never `exec` model output. The program is parsed against a whitelist of
commands and replayed by our own simulator. Model output is untrusted input,
and `exec` on untrusted input is how you get owned.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

RELATIVE_OPS = {"forward", "back", "right", "left", "penup", "pendown"}
ABSOLUTE_OPS = {"goto", "setheading"}

ARITY = {
    "forward": 1, "back": 1, "right": 1, "left": 1,
    "penup": 0, "pendown": 0, "goto": 2, "setheading": 1,
}

ALIASES = {
    "fd": "forward", "bk": "back", "backward": "back",
    "rt": "right", "lt": "left",
    "pu": "penup", "up": "penup", "pd": "pendown", "down": "pendown",
    "setpos": "goto", "setposition": "goto", "seth": "setheading",
}

_CALL_RE = re.compile(r"^([A-Za-z_][A-Za-z_0-9]*)\s*\(\s*([^)]*)\s*\)\s*;?\s*$")


@dataclass(frozen=True)
class Cmd:
    op: str
    args: tuple[float, ...] = ()


@dataclass
class Trace:
    """The result of replaying a program."""
    segments: list[tuple[float, float, float, float]] = field(default_factory=list)
    x: float = 0.0
    y: float = 0.0
    heading: float = 0.0
    n_commands: int = 0
    n_goto: int = 0
    n_setheading: int = 0

    @property
    def endpoint(self) -> tuple[float, float]:
        return (self.x, self.y)

    @property
    def n_segments(self) -> int:
        return len(self.segments)

    @property
    def escape_hatch_used(self) -> bool:
        return (self.n_goto + self.n_setheading) > 0

    @property
    def path_length(self) -> float:
        return sum(math.hypot(x1 - x0, y1 - y0)
                   for x0, y0, x1, y1 in self.segments)


def parse_program(text: str, allow_absolute: bool) -> tuple[list[Cmd], list[str]]:
    """Parse turtle source into commands.

    Returns (commands, errors). Anything unrecognised becomes an error and is
    skipped -- we never guess at intent.
    """
    allowed = set(RELATIVE_OPS) | (set(ABSOLUTE_OPS) if allow_absolute else set())
    cmds: list[Cmd] = []
    errors: list[str] = []

    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.strip().lstrip("-*").strip()
        if not line or line.startswith("#") or line.startswith("//"):
            continue
        m = _CALL_RE.match(line)
        if not m:
            errors.append(f"line {lineno}: not a command -> {line!r}")
            continue

        name = ALIASES.get(m.group(1).lower(), m.group(1).lower())
        if name not in allowed:
            errors.append(f"line {lineno}: '{name}' not allowed here")
            continue

        argstr = m.group(2).strip()
        if not argstr:
            args: tuple[float, ...] = ()
        else:
            try:
                args = tuple(float(a) for a in argstr.split(",") if a.strip())
            except ValueError:
                errors.append(f"line {lineno}: unparseable arguments -> {argstr!r}")
                continue

        if len(args) != ARITY[name]:
            errors.append(
                f"line {lineno}: {name} takes {ARITY[name]} arg(s), got {len(args)}")
            continue

        cmds.append(Cmd(name, args))

    return cmds, errors


def simulate(cmds: list[Cmd], start_heading: float = 0.0) -> Trace:
    """Replay commands. Heading 0 points along +x; angles are anticlockwise."""
    tr = Trace(heading=start_heading)
    pen_down = True

    for c in cmds:
        tr.n_commands += 1

        if c.op in ("forward", "back"):
            dist = c.args[0] if c.op == "forward" else -c.args[0]
            nx = tr.x + dist * math.cos(tr.heading)
            ny = tr.y + dist * math.sin(tr.heading)
            if pen_down:
                tr.segments.append((tr.x, tr.y, nx, ny))
            tr.x, tr.y = nx, ny

        elif c.op == "right":
            tr.heading -= math.radians(c.args[0])

        elif c.op == "left":
            tr.heading += math.radians(c.args[0])

        elif c.op == "penup":
            pen_down = False

        elif c.op == "pendown":
            pen_down = True

        elif c.op == "goto":
            nx, ny = c.args
            if pen_down:
                tr.segments.append((tr.x, tr.y, nx, ny))
            tr.x, tr.y = nx, ny
            tr.n_goto += 1

        elif c.op == "setheading":
            tr.heading = math.radians(c.args[0])
            tr.n_setheading += 1

    return tr


def to_source(cmds: list[Cmd], precision: int = 3) -> str:
    """Serialise commands back to source. Used to write reference programs."""
    out = []
    for c in cmds:
        args = ", ".join(f"{a:.{precision}f}".rstrip("0").rstrip(".") for a in c.args)
        out.append(f"{c.op}({args})")
    return "\n".join(out)
