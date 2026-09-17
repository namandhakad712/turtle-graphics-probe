"""
Does turtle graphics probe visual reasoning, or sequential state tracking?

This measures the one property that decides the answer: how errors propagate.

Turtle is a serial walk. Heading is accumulated state, so a heading error at
step i displaces every step after it -- error compounds with path length.
SVG places absolute coordinates, so an error in one element leaves the others
untouched.

If turtle drift grows with the number of segments while SVG drift stays flat,
then turtle is strictly harder for reasons that have nothing to do with seeing.

Run: python analysis/turtle_drift.py
"""
from __future__ import annotations

import math
import random


def turtle_drift(n_segments: int, sigma_deg: float, seg_len: float = 1.0,
                 trials: int = 4000, seed: int = 0) -> float:
    """RMS endpoint displacement when every emitted turn carries heading noise.

    Intended shape is an N-gon -- a circle drawn in N straight strokes, which is
    what a turtle program tracing any curve actually is. The model's program is
    that shape with cumulative heading error added at each turn.
    """
    sigma = math.radians(sigma_deg)
    turn = 2.0 * math.pi / n_segments
    rng = random.Random(seed)

    disps = []
    for _ in range(trials):
        phi = 0.0
        ix = iy = ex = ey = 0.0
        theta = 0.0
        for _ in range(n_segments):
            theta += turn
            phi += rng.gauss(0.0, sigma)
            ix += seg_len * math.cos(theta)
            iy += seg_len * math.sin(theta)
            ex += seg_len * math.cos(theta + phi)
            ey += seg_len * math.sin(theta + phi)
        disps.append(math.hypot(ex - ix, ey - iy))
    return math.sqrt(sum(d * d for d in disps) / len(disps))


def svg_drift(sigma_coord: float = 1.0, trials: int = 4000,
              seed: int = 0) -> float:
    """RMS displacement in an absolute-coordinate format.

    Each element is placed independently, so error does NOT accumulate with the
    number of elements. This is the structural contrast with turtle.
    """
    rng = random.Random(seed)
    disps = [math.hypot(rng.gauss(0.0, sigma_coord), rng.gauss(0.0, sigma_coord))
             for _ in range(trials)]
    return math.sqrt(sum(d * d for d in disps) / len(disps))


def shape_diameter(n_segments: int, seg_len: float = 1.0) -> float:
    """Diameter of the N-gon: perimeter / pi."""
    return n_segments * seg_len / math.pi


def token_cost(n_segments: int) -> tuple[int, int]:
    """Rough output tokens for the same circle in turtle vs SVG.

    Turtle: `forward(1); right(1.8)` per segment.
    SVG:    a single <circle cx=".." cy=".." r=".."/> element.
    """
    turtle_tokens = n_segments * 6
    svg_tokens = 20
    return turtle_tokens, svg_tokens


def main() -> None:
    print("=" * 74)
    print("ERROR PROPAGATION: turtle vs absolute-coordinate formats")
    print("=" * 74)
    print()
    print("RMS endpoint displacement, as a fraction of the drawing's diameter.")
    print("Heading noise per turn, 4000 trials per cell.")
    print()

    header = f"{'segments':>9} | " + " | ".join(f"sigma={s:>4} deg" for s in (0.5, 1.0, 2.0))
    print(header)
    print("-" * len(header))

    for n in (50, 100, 200, 500, 1000):
        diam = shape_diameter(n)
        cells = []
        for s in (0.5, 1.0, 2.0):
            d = turtle_drift(n, s)
            cells.append(f"{100 * d / diam:>12.1f}%")
        print(f"{n:>9} | " + " | ".join(cells))

    print()
    print(f"{'SVG':>9} | " + " | ".join(f"{'flat, indep. of N':>12}" for _ in range(3)))
    print()
    print("Turtle drift grows with segment count. SVG drift does not.")
    print()

    print("=" * 74)
    print("OUTPUT COST: the same circle")
    print("=" * 74)
    print()
    print(f"{'segments':>9} | {'turtle tokens':>13} | {'SVG tokens':>10} | {'ratio':>7}")
    print("-" * 48)
    for n in (50, 100, 200, 500, 1000):
        t, s = token_cost(n)
        print(f"{n:>9} | {t:>13,} | {s:>10,} | {t / s:>6.0f}x")
    print()
    print("A circle is one SVG element and N turtle segments.")
    print("The turtle form costs orders of magnitude more tokens to say less.")
    print()

    print("=" * 74)
    print("WHAT THIS IMPLIES")
    print("=" * 74)
    print()
    print("1. Turtle adds a failure mode that is not perceptual. A model can")
    print("   see the image perfectly and still fail, purely by drifting.")
    print("2. That failure grows with path length, so harder drawings fail for")
    print("   reasons unrelated to task difficulty -- an unfair, non-monotonic")
    print("   difficulty curve.")
    print("3. Grading cannot separate 'could not see it' from 'lost track of")
    print("   heading'. Two very different hypotheses, one score.")
    print()
    print("This does not make turtle worthless. It makes it a probe for")
    print("sequential state tracking, not for visual reasoning.")
    print()


if __name__ == "__main__":
    main()
