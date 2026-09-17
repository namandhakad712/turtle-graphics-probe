"""Self-critique: is the spiral a degenerate test shape?

SUPERSEDED. This was the first, single-sided version of the test. Its closing
recommendation names "irregular staircases" as a valid family -- the two-sided
test in degeneracy_sweep.py shows an irregular staircase is drawn by 2 absolute
hops, so it is bypassable. Use degeneracy_sweep.py instead. This file is kept
as the record of how the finding was reached.

If the canonical program is close to a fixed repeating loop, then a model can draw
it without tracking state at all -- it just repeats the same turn. That would make
the shape useless for measuring state tracking.

Measure it rather than assert it.
"""
import math
import random

N = 90
THETA_MAX = 2.0 * 2 * math.pi
R0, R1 = 14.0, 104.0


def canonical_points():
    pts = []
    for i in range(N + 1):
        t = THETA_MAX * i / N
        r = R0 + (R1 - R0) * t / THETA_MAX
        pts.append((r * math.cos(t), r * math.sin(t)))
    return pts


def wrap(d):
    while d > 180.0:
        d -= 360.0
    while d < -180.0:
        d += 360.0
    return d


pts = canonical_points()

turns = []
for i in range(1, N):
    a0 = math.atan2(pts[i][1] - pts[i - 1][1], pts[i][0] - pts[i - 1][0])
    a1 = math.atan2(pts[i + 1][1] - pts[i][1], pts[i + 1][0] - pts[i][0])
    turns.append(wrap(math.degrees(a1 - a0)))

segs = [math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
        for i in range(N)]


def stats(xs):
    m = sum(xs) / len(xs)
    sd = math.sqrt(sum((x - m) ** 2 for x in xs) / len(xs))
    return m, sd, min(xs), max(xs)


tm, tsd, tlo, thi = stats(turns)
sm, ssd, slo, shi = stats(segs)

print("=" * 68)
print("CANONICAL SPIRAL -- is the turn angle constant?")
print("=" * 68)
print(f"  turn per step : mean {tm:6.2f} deg   sd {tsd:5.3f}   range {tlo:.2f}..{thi:.2f}")
print(f"  segment length: mean {sm:6.2f}      sd {ssd:5.2f}   range {slo:.2f}..{shi:.2f}")
print(f"  coefficient of variation of turn angle: {tsd / abs(tm) * 100:.2f}%")
print()

# The lazy program: same command repeated, no state tracking whatsoever.
lx = ly = 0.0
heading = 0.0
lazy = [(0.0, 0.0)]
for _ in range(N):
    heading -= math.radians(tm)
    lx += sm * math.cos(heading)
    ly += sm * math.sin(heading)
    lazy.append((lx, ly))


def resample(path, n=400):
    """Resample a polyline to n points at equal arc length."""
    d = [0.0]
    for i in range(1, len(path)):
        d.append(d[-1] + math.hypot(path[i][0] - path[i - 1][0],
                                    path[i][1] - path[i - 1][1]))
    total = d[-1]
    out = []
    j = 0
    for k in range(n):
        target = total * k / (n - 1)
        while j < len(d) - 2 and d[j + 1] < target:
            j += 1
        span = d[j + 1] - d[j]
        f = 0.0 if span == 0 else (target - d[j]) / span
        out.append((path[j][0] + f * (path[j + 1][0] - path[j][0]),
                    path[j][1] + f * (path[j + 1][1] - path[j][1])))
    return out


def mean_distance(a, b):
    """Symmetric mean nearest-point distance between two paths."""
    ra, rb = resample(a), resample(b)
    d1 = sum(min(math.hypot(p[0] - q[0], p[1] - q[1]) for q in rb) for p in ra) / len(ra)
    d2 = sum(min(math.hypot(p[0] - q[0], p[1] - q[1]) for q in ra) for p in rb) / len(rb)
    return (d1 + d2) / 2


# But the lazy turtle starts at the origin; the canonical spiral starts at (R0, 0).
# Align them on their start points before comparing, which is the fairest test.
canon = [(p[0] - pts[0][0], p[1] - pts[0][1]) for p in pts]
lazy_shifted = [(p[0], p[1]) for p in lazy]

diag = math.hypot(max(p[0] for p in canon) - min(p[0] for p in canon),
                  max(p[1] for p in canon) - min(p[1] for p in canon))

dist = mean_distance(canon, lazy_shifted)

print("=" * 68)
print("THE LAZY PROGRAM -- one command, repeated N times, zero state tracking")
print("=" * 68)
print(f"  forward({sm:.2f}); right({tm:.2f})   x {N}")
print()
print(f"  mean path distance from the true spiral: {dist:.2f} units")
print(f"  spiral diameter: {diag:.1f} units")
print(f"  error as fraction of diameter: {dist / diag * 100:.2f}%")
print()

if dist / diag < 0.05:
    print("  VERDICT: DEGENERATE. A blind repeating loop reproduces this shape")
    print("  to within 5% of its diameter. The spiral cannot distinguish a model")
    print("  that tracks state from one that does not, because tracking is not")
    print("  required to draw it.")
else:
    print("  VERDICT: the shape does require genuine tracking.")
print()

# ---------------------------------------------------------------------------
# Lazy v2: parametric. Constant turn, linearly growing step. Three numbers,
# still zero state tracking. If this lands close, the shape is still degenerate
# -- it just needed a slightly less lazy model, not a state-tracking one.
# ---------------------------------------------------------------------------

n = len(segs)
mi = (n - 1) / 2.0
ms = sm
num = sum((i - mi) * (segs[i] - ms) for i in range(n))
den = sum((i - mi) ** 2 for i in range(n))
b = num / den
a = ms - b * mi

px = py = 0.0
heading = 0.0
para = [(0.0, 0.0)]
for i in range(N):
    heading -= math.radians(tm)
    step = a + b * i
    px += step * math.cos(heading)
    py += step * math.sin(heading)
    para.append((px, py))

dist2 = mean_distance(canon, para)

print("=" * 68)
print("THE PARAMETRIC PROGRAM -- three numbers, still no state tracking")
print("=" * 68)
print(f"  forward({a:.2f} + {b:.3f} * i); right({tm:.2f})   x {N}")
print()
print(f"  mean path distance from the true spiral: {dist2:.2f} units")
print(f"  error as fraction of diameter: {dist2 / diag * 100:.2f}%")
print()

if dist2 / diag < 0.05:
    print("  VERDICT: STILL DEGENERATE. A closed-form parametric program -- three")
    print("  constants and a loop counter -- reproduces the shape. No state tracking")
    print("  is required, so the item cannot measure state tracking.")
else:
    print(f"  VERDICT: the shape resists a closed-form parametric program")
    print(f"  ({dist2 / diag * 100:.1f}% error). It requires something more.")
print()
print("=" * 68)
print("WHAT THIS MEANS FOR SHAPE SELECTION")
print("=" * 68)
print()
print("  A shape is only a valid item if NO closed-form program reproduces it.")
print("  Smooth analytic curves -- spirals, waves, arcs, circles -- all have one.")
print("  They are the worst possible test shapes, and they look the best in a demo.")
print()
print("  Valid families need a program that cannot be written without knowing")
print("  where the pen currently is: random waypoints, irregular staircases,")
print("  paths with varying curvature, and multi-stroke shapes where the pen must")
print("  travel to a specific absolute location between strokes.")
print()

