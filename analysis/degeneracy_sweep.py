"""Two-sided validity test for turtle benchmark items.

An item is only valid if BOTH hold:

  (a) NO low-parameter state-free program reproduces it
      -- otherwise a blind loop draws it and the item cannot measure anything.
  (b) NO small set of absolute hops reproduces it
      -- otherwise the model reads landmarks off the image and emits `goto`
         calls, accumulating zero state, and again the item measures nothing.

(b) is the test the original design never ran. It is the more dangerous one,
because it bypasses the task without any loss of fidelity.

Every fake program is given maximum advantage: it is rigidly aligned
(translation + optimal rotation) to the true shape before scoring, and
scored with a nearest-point metric that forgives topological error.

Usage:  python analysis/degeneracy_sweep.py
"""
import math
import random

N_PTS = 200
TAU_FRAC = 0.02          # hop tolerance, as a fraction of shape diameter
ERROR_THRESHOLD = 0.05   # 5% of diameter
HOP_THRESHOLD = 20       # few absolute anchors => bypassable
COVERAGE_THRESHOLD = 0.90  # 90% of each path accounted for by the other


# ---------------------------------------------------------------- geometry ---

def resample(path, n):
    d = [0.0]
    for i in range(1, len(path)):
        d.append(d[-1] + math.hypot(path[i][0] - path[i - 1][0],
                                    path[i][1] - path[i - 1][1]))
    total = d[-1]
    if total == 0:
        return [path[0]] * n
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


def diameter(path):
    xs = [p[0] for p in path]
    ys = [p[1] for p in path]
    return math.hypot(max(xs) - min(xs), max(ys) - min(ys))


def mean_path_distance(a, b):
    ra, rb = resample(a, N_PTS), resample(b, N_PTS)
    d1 = sum(min(math.hypot(p[0] - q[0], p[1] - q[1]) for q in rb) for p in ra) / len(ra)
    d2 = sum(min(math.hypot(p[0] - q[0], p[1] - q[1]) for q in ra) for p in rb) / len(rb)
    return (d1 + d2) / 2


def coverage(a, b, tau):
    """Fraction of a's points lying within tau of b."""
    ra, rb = resample(a, N_PTS), resample(b, N_PTS)
    return sum(1 for p in ra
               if min(math.hypot(p[0] - q[0], p[1] - q[1]) for q in rb) <= tau) / len(ra)


def symmetric_coverage(a, b, tau):
    """Mean path distance forgives a fake that stops short or overshoots.

    Coverage does not: it asks what fraction of each path the other actually
    accounts for. Reported alongside the distance so a lenient metric cannot
    manufacture a degeneracy verdict on its own.
    """
    return min(coverage(a, b, tau), coverage(b, a, tau))


def centroid(pts):
    n = len(pts)
    return (sum(p[0] for p in pts) / n, sum(p[1] for p in pts) / n)


def rotate(pts, deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return [(x * c - y * s, x * s + y * c) for x, y in pts]


def align(fake, true):
    """Best rigid alignment of fake onto true, returned in true's own frame.

    The result is translated back by true's centroid. Returning a centred
    shape while scoring it against an uncentred original silently injects a
    constant translation error into every measurement.
    """
    ct = centroid(true)
    cf = centroid(fake)
    t0 = [(x - ct[0], y - ct[1]) for x, y in true]
    f0 = [(x - cf[0], y - cf[1]) for x, y in fake]

    ts = resample(t0, 60)
    fs0 = resample(f0, 60)

    # Seed the rotation from the first segment. `build` always emits its first
    # segment along +x, so the rotation that maps the fake onto the true shape
    # is just the true first segment's direction. Seeding matters for symmetric
    # shapes: a 5-fold star coincides with itself under 72-degree rotations,
    # and an unseeded index-correspondence search happily locks onto the wrong
    # one and reports a large error for an exact reproduction.
    seed = math.degrees(math.atan2(true[1][1] - true[0][1], true[1][0] - true[0][0]))

    def err(deg):
        f = rotate(fs0, deg)
        return sum(math.hypot(f[i][0] - ts[i][0], f[i][1] - ts[i][1])
                   for i in range(60)) / 60

    best_e, best_d = 1e18, seed
    for step in (1.0, 0.25):
        lo, hi = best_d - 6 * step, best_d + 6 * step
        k = -6
        while k <= 6:
            deg = best_d + k * step
            if lo <= deg <= hi:
                e = err(deg)
                if e < best_e:
                    best_e, best_d = e, deg
            k += 1

    r = rotate(f0, best_d)
    return [(x + ct[0], y + ct[1]) for x, y in r], best_d


# ------------------------------------------------------- program families ---

def polyfit(u, y, deg):
    m = deg + 1
    A = [[sum(x ** (i + j) for x in u) for j in range(m)] for i in range(m)]
    b = [sum(yy * x ** i for x, yy in zip(u, y)) for i in range(m)]
    for col in range(m):
        piv = max(range(col, m), key=lambda r: abs(A[r][col]))
        A[col], A[piv] = A[piv], A[col]
        b[col], b[piv] = b[piv], b[col]
        for r in range(col + 1, m):
            f = A[r][col] / A[col][col]
            for c in range(col, m):
                A[r][c] -= f * A[col][c]
            b[r] -= f * b[col]
    co = [0.0] * m
    for r in range(m - 1, -1, -1):
        s = b[r] - sum(A[r][c] * co[c] for c in range(r + 1, m))
        co[r] = s / A[r][r]
    return co


def polyval(co, x):
    return sum(c * x ** i for i, c in enumerate(co))


def build(cs, ct, nseg, periodic=False, heading0=0.0):
    """Integrate a program into a path.

    Index convention: turn[0] is always 0, because the initial heading is set
    to the first segment's direction. Fitted turn models therefore start at
    index 1 -- including turn[0] in the fit would break the period of an
    otherwise perfectly periodic shape.
    """
    x = y = 0.0
    h = math.radians(heading0)
    pts = [(0.0, 0.0)]
    for i in range(nseg):
        u = 2 * i / (nseg - 1) - 1 if nseg > 1 else 0.0
        if periodic:
            step = cs[i % len(cs)]
            turn = 0.0 if i == 0 else ct[(i - 1) % len(ct)]
        else:
            step = polyval(cs, u)
            turn = 0.0 if i == 0 else polyval(ct, u)
        h += math.radians(turn)
        x += step * math.cos(h)
        y += step * math.sin(h)
        pts.append((x, y))
    return pts


def fit_poly(steps, turns, deg):
    n = len(steps)
    u = [2 * i / (n - 1) - 1 for i in range(n)]
    cs = polyfit(u, steps, deg)
    ct = polyfit(u[1:], turns[1:], deg) if len(turns) > 1 else [0.0] * (deg + 1)
    return cs, ct, 2 * (deg + 1)


def fit_periodic(steps, turns, p):
    cs = [0.0] * p
    cnts = [0] * p
    for i in range(len(steps)):
        k = i % p
        cs[k] += steps[i]
        cnts[k] += 1
    cs = [cs[i] / cnts[i] if cnts[i] else 0.0 for i in range(p)]

    ct = [0.0] * p
    cntt = [0] * p
    for i in range(1, len(turns)):
        k = (i - 1) % p
        ct[k] += turns[i]
        cntt[k] += 1
    ct = [ct[i] / cntt[i] if cntt[i] else 0.0 for i in range(p)]
    return cs, ct, 2 * p


# --------------------------------------------------------- hop compression ---

def max_chord_dev(pts, i, j):
    ax, ay = pts[i]
    bx, by = pts[j]
    dx, dy = bx - ax, by - ay
    L = math.hypot(dx, dy)
    if L == 0:
        return max(math.hypot(pts[k][0] - ax, pts[k][1] - ay) for k in range(i, j + 1))
    return max(abs(dy * (pts[k][0] - ax) - dx * (pts[k][1] - ay)) / L
               for k in range(i, j + 1))


def hop_compress(path, tau):
    """Fewest straight-line hops (each = one absolute `goto`) within tolerance."""
    pts = resample(path, N_PTS)
    i, hops = 0, 0
    while i < len(pts) - 1:
        j = i + 1
        while j < len(pts) - 1 and max_chord_dev(pts, i, j + 1) <= tau:
            j += 1
        hops += 1
        i = j
    return hops


# ----------------------------------------------------------------- shapes ---

def fam_spiral(n=N_PTS):
    return [(lambda t: ((14 + 90 * t / (4 * math.pi)) * math.cos(t),
                        (14 + 90 * t / (4 * math.pi)) * math.sin(t)))(4 * math.pi * i / (n - 1))
            for i in range(n)]


def fam_sine(n=N_PTS):
    return [(300 * i / (n - 1), 60 * math.sin(2.5 * 2 * math.pi * i / (n - 1)))
            for i in range(n)]


def fam_arc(n=N_PTS):
    return [(100 * math.cos(math.radians(300 * i / (n - 1))),
             100 * math.sin(math.radians(300 * i / (n - 1)))) for i in range(n)]


def fam_star(n=N_PTS):
    verts = []
    for k in range(10):
        a = math.pi / 2 + k * math.pi / 5
        r = 100 if k % 2 == 0 else 40
        verts.append((r * math.cos(a), r * math.sin(a)))
    verts.append(verts[0])
    return verts


def fam_zigzag(n=N_PTS):
    pts = [(0.0, 0.0)]
    x = y = 0.0
    h = 0.0
    for i in range(n - 1):
        h += 40.0 if i % 2 == 0 else -40.0
        x += 12 * math.cos(h)
        y += 12 * math.sin(h)
        pts.append((x, y))
    return pts


def fam_staircase(n=N_PTS):
    rng = random.Random(7)
    pts = [(0.0, 0.0)]
    x = y = 0.0
    while len(pts) < n:
        x += rng.uniform(8, 30)
        pts.append((x, y))
        y += rng.uniform(8, 30)
        pts.append((x, y))
    return pts


def fam_random_walk(n=N_PTS):
    rng = random.Random(11)
    pts = [(0.0, 0.0)]
    x = y = 0.0
    h = 0.0
    for _ in range(n - 1):
        h += rng.uniform(-25, 25)
        x += 10 * math.cos(h)
        y += 10 * math.sin(h)
        pts.append((x, y))
    return pts


def fam_varying_curvature(n=N_PTS):
    """Smoothly varying curvature -- looks organic, may still be closed-form."""
    pts = [(0.0, 0.0)]
    x = y = 0.0
    h = 0.0
    for i in range(n - 1):
        h += 6.0 + 4.0 * math.sin(2 * math.pi * i / 60)
        x += 9 * math.cos(h)
        y += 9 * math.sin(h)
        pts.append((x, y))
    return pts


def fam_irregular_poly(n=N_PTS):
    """Aperiodic irregular turning -- the candidate valid family."""
    rng = random.Random(23)
    pts = [(0.0, 0.0)]
    x = y = 0.0
    h = 0.0
    for _ in range(n - 1):
        h += rng.uniform(-80, 80)
        step = rng.uniform(4, 22)
        x += step * math.cos(h)
        y += step * math.sin(h)
        pts.append((x, y))
    return pts


FAMILIES = [
    ("spiral (analytic)", fam_spiral),
    ("sine wave (analytic)", fam_sine),
    ("circular arc (analytic)", fam_arc),
    ("5-point star (periodic)", fam_star),
    ("regular zigzag (periodic)", fam_zigzag),
    ("varying curvature (smooth)", fam_varying_curvature),
    ("irregular staircase", fam_staircase),
    ("bounded random walk", fam_random_walk),
    ("aperiodic irregular", fam_irregular_poly),
]


def true_kinematics(path):
    """Steps and turns of the program that actually produced `path`.

    Deliberately does NOT resample. Resampling to equal arc length forces every
    segment to the same length, which erases the step sequence and leaves the
    test measuring turn angles only. The kinematics must come from the raw
    output of the generator.

    turns[i] is the turn applied before segment i; turns[0] is 0 because the
    initial heading is set to the first segment's direction.
    """
    steps, turns = [], []
    n = len(path)
    for i in range(n - 1):
        dx = path[i + 1][0] - path[i][0]
        dy = path[i + 1][1] - path[i][1]
        steps.append(math.hypot(dx, dy))
        if i == 0:
            turns.append(0.0)
        else:
            a0 = math.atan2(path[i][1] - path[i - 1][1], path[i][0] - path[i - 1][0])
            a1 = math.atan2(dy, dx)
            d = math.degrees(a1 - a0)
            while d > 180:
                d -= 360
            while d < -180:
                d += 360
            turns.append(d)
    return path, steps, turns


def scaling_test(tol=0.01, sizes=(25, 50, 100, 200)):
    """How many parameters does it take to fit the shape at 1% error?

    The robust question is not 'can a cheap program fit it' -- that depends on
    the hypothesis class and the tolerance, both of which we choose. The robust
    question is how the answer SCALES with the length of the shape.

      - params constant as N grows  -> the shape has a name. A model that
        recognises the family writes a fixed loop and matches it at any length.
      - params grow with N          -> the shape carries N-dependent
        information, and no fixed program reproduces it.

    This is the only version of the test that is not an artefact of a threshold
    we picked ourselves.
    """
    print("=" * 78)
    print(f"SCALING TEST -- parameters needed to fit within {tol:.0%} of diameter")
    print("=" * 78)
    print()
    print(f"{'shape family':<28}" + "".join(f"{'N=' + str(s):>12}" for s in sizes))
    print("-" * 78)

    verdicts = {}
    for name, fn in FAMILIES:
        cells = []
        counts = []
        for size in sizes:
            try:
                raw = fn(size)
            except TypeError:
                raw = fn()
            _, steps, turns = true_kinematics(raw)
            nseg = len(steps)
            if nseg < 4:
                cells.append("n/a")
                continue
            dia = diameter(raw)

            found = None
            for deg in range(0, 7):
                if 2 * (deg + 1) > nseg // 2:
                    break
                cs, ct, p = fit_poly(steps, turns, deg)
                fake = build(cs, ct, nseg, periodic=False)
                al, _ = align(fake, raw)
                if mean_path_distance(al, raw) / dia < tol:
                    found = p
                    break
            if found is None:
                for pp in range(1, max(2, nseg // 4) + 1):
                    if 2 * pp > nseg // 2:
                        break
                    cs, ct, p = fit_periodic(steps, turns, pp)
                    fake = build(cs, ct, nseg, periodic=True)
                    al, _ = align(fake, raw)
                    if mean_path_distance(al, raw) / dia < tol:
                        found = p
                        break
            cells.append(str(found) if found else "no fit")
            counts.append(found if found else nseg)

        verdicts[name] = counts
        print(f"{name:<28}" + "".join(f"{c:>12}" for c in cells))

    print("-" * 78)
    print()
    print("params constant  -> the shape has a name; it is degenerate")
    print("params grow ~N   -> no fixed program reproduces it")
    print()
    for name, counts in verdicts.items():
        if len(counts) >= 2 and counts[0] > 0:
            ratio = counts[-1] / counts[0]
            if ratio > 3:
                tag = "GROWS  (valid)"
            elif ratio > 1.5:
                tag = "grows slowly (suspect)"
            else:
                tag = "FLAT   (degenerate)"
            print(f"  {name:<28} {counts[0]:>5} -> {counts[-1]:>5}   x{ratio:<5.1f} {tag}")
    print()


def main():
    print("=" * 78)
    print("TWO-SIDED ITEM VALIDITY TEST")
    print(f"  n = {N_PTS} points | tolerance {ERROR_THRESHOLD:.0%} of diameter "
          f"| hop tolerance {TAU_FRAC:.0%}")
    print("=" * 78)
    print()
    print(f"{'shape family':<28}{'segs':>5}{'best fake':>16}{'par':>5}"
          f"{'err%':>8}{'cov%':>7}{'hops':>6}  verdict")
    print("-" * 78)

    rows = []
    for name, fn in FAMILIES:
        path = fn()
        raw, steps, turns = true_kinematics(path)
        nseg = len(steps)
        dia = diameter(raw)
        tau = TAU_FRAC * dia

        best = (1e18, "?", 0)
        best_cov = 0.0
        for deg in range(4):
            cs, ct, p = fit_poly(steps, turns, deg)
            fake = build(cs, ct, nseg, periodic=False)
            al, _ = align(fake, raw)
            e = mean_path_distance(al, raw) / dia
            if e < best[0]:
                best = (e, f"poly d={deg}", p)
                best_cov = symmetric_coverage(al, raw, tau)

        for p_ in range(1, 13):
            cs, ct, pr = fit_periodic(steps, turns, p_)
            fake = build(cs, ct, nseg, periodic=True)
            al, _ = align(fake, raw)
            e = mean_path_distance(al, raw) / dia
            if e < best[0]:
                best = (e, f"periodic p={p_}", pr)
                best_cov = symmetric_coverage(al, raw, tau)

        hops = hop_compress(raw, tau)

        # An item is dead if a cheap program reproduces it on BOTH metrics.
        # Requiring agreement stops a lenient distance metric from producing a
        # degeneracy verdict on its own.
        fails_a = best[0] > ERROR_THRESHOLD or best_cov < COVERAGE_THRESHOLD
        fails_b = hops > HOP_THRESHOLD
        if fails_a and fails_b:
            verdict = "VALID"
        elif not fails_a and not fails_b:
            verdict = "DEAD (both)"
        elif not fails_a:
            verdict = "DEAD (a: loop)"
        else:
            verdict = "DEAD (b: goto)"
        rows.append((name, best[1], best[2], best[0], best_cov, hops, verdict))

        print(f"{name:<28}{nseg:>5}{best[1]:>16}{best[2]:>5}"
              f"{best[0] * 100:>7.2f}%{best_cov * 100:>6.0f}%{hops:>6}  {verdict}")

    print("-" * 78)
    print()
    print("(a) = no low-parameter state-free program reproduces the shape")
    print("(b) = no small set of absolute hops reproduces the shape")
    print()
    valid = [r[0] for r in rows if r[6] == "VALID"]
    print(f"families surviving BOTH tests: {len(valid)} of {len(rows)}")
    for v in valid:
        print(f"  - {v}")
    print()

    # ------------------------------------------------------------------
    # Test (b) depends on the tolerance, and the tolerance is our choice.
    # If validity moves when we move the tolerance, then validity is not a
    # property of the shape -- it is a property of the grader.
    # ------------------------------------------------------------------
    print("=" * 78)
    print("TOLERANCE SENSITIVITY OF TEST (b)  --  hops needed at each tolerance")
    print("=" * 78)
    print()
    tols = [0.005, 0.01, 0.02, 0.05]
    print(f"{'shape family':<28}" + "".join(f"{t:>9.1%}" for t in tols))
    print("-" * 78)
    for name, fn in FAMILIES:
        rs, _, _ = true_kinematics(fn())
        dia = diameter(rs)
        cells = "".join(f"{hop_compress(rs, t * dia):>9}" for t in tols)
        print(f"{name:<28}{cells}")
    print("-" * 78)
    print()
    print("A shape is only 'un-bypassable' relative to a stated tolerance.")
    print("Tighten the tolerance and every shape becomes expensive to hop.")
    print("Loosen it and a zigzag is one straight line.")
    print()

    # ------------------------------------------------------------------
    # What this test can and cannot establish.
    # ------------------------------------------------------------------
    print("=" * 78)
    print("THE LIMIT OF THIS TEST")
    print("=" * 78)
    print()
    print("  The fitter searches a hypothesis class: polynomial turn/step")
    print("  sequences up to degree 3, and periodic sequences up to period 12.")
    print()
    print("  'varying curvature (smooth)' scores VALID above -- but it was")
    print("  generated by  right(6 + 4*sin(2*pi*i/60)); forward(9), which is a")
    print("  closed form with three constants. The fitter missed it because a")
    print("  sinusoid is not in the hypothesis class.")
    print()
    print("  So the verdict is 'no cheap program FOUND', never 'no cheap program")
    print("  EXISTS'. Widen the hypothesis class and more items die. This test")
    print("  can only ever return a lower bound on degeneracy.")
    print()
    print("  Consequence for the benchmark: item validity rests on an assumption")
    print("  that cannot be proved, only failed to be disproved.")
    print()
    print()

    scaling_test()

    # ------------------------------------------------------------------
    # Floor check. Feed the exact program back through the full metric and
    # confirm it scores zero. Without this, a bug in the integrator, the
    # alignment, or the resampling produces plausible-looking numbers that
    # happen to flatter the conclusion. Four such bugs were found this way.
    # ------------------------------------------------------------------
    print("=" * 78)
    print("FLOOR CHECK -- the exact program must score 0.00%")
    print("=" * 78)
    print()
    worst = 0.0
    for name, fn in FAMILIES:
        raw = fn()
        _, steps, turns = true_kinematics(raw)
        n = len(steps)
        cs, ct, _ = fit_periodic(steps, turns, n)
        exact = build(cs, ct, n, periodic=True)
        al, _ = align(exact, raw)
        e = mean_path_distance(al, raw) / diameter(raw)
        worst = max(worst, e)
        print(f"  {name:<28} {e * 100:8.4f}%")
    print()
    print(f"  worst floor: {worst * 100:.4f}%  --  "
          f"{'PASS' if worst < 1e-6 else 'FAIL, do not trust the table above'}")


if __name__ == "__main__":
    main()
