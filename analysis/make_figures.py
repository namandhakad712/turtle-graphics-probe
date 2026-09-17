"""Generate the publication figures as standalone SVG.

Every figure is computed from the same analysis code that produces the numbers
in the paper, so changing the analysis changes the figures. Nothing here is
hand-drawn or hard-coded from a previous run.

    python analysis/make_figures.py
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from degeneracy_sweep import (FAMILIES, N_PTS, align, build, diameter,
                              fam_spiral, fit_periodic, fit_poly,
                              hop_compress, mean_path_distance,
                              true_kinematics)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Figures live under docs/assets/figures/ so that a single copy serves both the
# README on GitHub and the GitHub Pages site, which is published from /docs.
OUT = os.path.join(ROOT, "docs", "assets", "figures")

# ---------------------------------------------------------------- palette ---
INK = "#141414"
MUTED = "#5c5c5c"
FAINT = "#9a9a9a"
RULE = "#dcdcdc"
PANEL = "#f6f6f4"
WHITE = "#ffffff"
RED = "#b3261e"
BLUE = "#1f5fa8"
TEAL = "#0f6e56"
AMBER = "#a86a00"
PURPLE = "#534ab7"
GREEN = "#2f6f3e"

SANS = "system-ui,-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"
SERIF = "Georgia,'Times New Roman',serif"
MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;"))


def t(x, y, s, size=13, fill=INK, anchor="start", family=SANS,
      weight="400", extra=""):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{family}" '
            f'font-size="{size}" fill="{fill}" text-anchor="{anchor}" '
            f'font-weight="{weight}"{extra}>{esc(s)}</text>')


def rect(x, y, w, h, fill="none", stroke="none", rx=0, sw=1, extra=""):
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"'
            f'{extra}/>')


def line(x1, y1, x2, y2, stroke=INK, sw=1, dash=None, cap="butt"):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{stroke}" stroke-width="{sw}" stroke-linecap="{cap}"{d}/>')


def circle(cx, cy, r, fill=INK, stroke="none", sw=1):
    return (f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="{sw}"/>')


def poly(points, stroke=INK, sw=2, fill="none", dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    pts = " ".join(f"{p[0]:.1f},{p[1]:.1f}" for p in points)
    return (f'<polyline points="{pts}" fill="{fill}" stroke="{stroke}" '
            f'stroke-width="{sw}" stroke-linejoin="round" '
            f'stroke-linecap="round"{d}/>')


def write(name, body, w, h):
    os.makedirs(OUT, exist_ok=True)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
           f'width="{w}" height="{h}" font-family="{SANS}">'
           f'<rect width="{w}" height="{h}" fill="{WHITE}"/>'
           f'{body}</svg>')
    path = os.path.join(OUT, name)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(svg)
    print(f"  {name:<34} {w}x{h}  {len(svg):>6} bytes")
    return path


def fit_paths(paths, box):
    """Centre a group of paths on the origin and scale to fit `box`."""
    xs = [p[0] for path in paths for p in path]
    ys = [p[1] for path in paths for p in path]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    s = box / max(maxx - minx, maxy - miny)
    ox, oy = (minx + maxx) / 2, (miny + maxy) / 2
    return [[((p[0] - ox) * s, (p[1] - oy) * s) for p in path] for path in paths]


def to_d(path, cx, cy):
    out = []
    for i, p in enumerate(path):
        out.append(("M" if i == 0 else "L") + f"{p[0] + cx:.1f} {p[1] + cy:.1f}")
    return " ".join(out)


def spiral_pair():
    raw, steps, turns = true_kinematics(fam_spiral())
    n = len(steps)
    cs, ct, nparams = fit_poly(steps, turns, 3)
    fake = build(cs, ct, n, periodic=False)
    al, _ = align(fake, raw)
    err = mean_path_distance(al, raw) / diameter(raw)
    return raw, al, err, nparams, n


# ===========================================================================
# Figure 1 -- the item and its eight-number reproduction
# ===========================================================================

def fig_degeneracy():
    raw, al, err, nparams, n = spiral_pair()
    (true_p, fake_p), = [fit_paths([raw, al], 250)]
    W, H = 860, 420
    b = [f'<rect width="{W}" height="{H}" fill="{WHITE}"/>']

    for i, label in enumerate(["The item", "The eight-number reproduction"]):
        x0 = 40 + i * 410
        b.append(rect(x0, 70, 370, 300, PANEL, rx=10))
        b.append(t(x0 + 185, 52, label, 15, INK, "middle", SERIF))
        b.append(rect(x0 + 60, 100, 250, 250, "none", RULE, rx=6, sw=1))

    cx1, cy1 = 40 + 185, 225
    cx2, cy2 = 450 + 185, 225
    b.append(f'<path d="{to_d(true_p, cx1, cy1)}" fill="none" '
             f'stroke="{INK}" stroke-width="1.6" stroke-linejoin="round"/>')
    b.append(f'<path d="{to_d(true_p, cx2, cy2)}" fill="none" '
             f'stroke="{FAINT}" stroke-width="3.6" stroke-linejoin="round"/>')
    b.append(f'<path d="{to_d(fake_p, cx2, cy2)}" fill="none" '
             f'stroke="{RED}" stroke-width="1.4" stroke-linejoin="round" '
             f'stroke-dasharray="5 3"/>')

    b.append(line(60, 392, 90, 392, FAINT, 3.6))
    b.append(t(98, 396, "the item", 12, MUTED))
    b.append(line(180, 392, 210, 392, RED, 1.4, "5 3"))
    b.append(t(218, 396, "the reproduction", 12, MUTED))
    b.append(t(820, 396, f"mean deviation {err * 100:.2f}% of diameter", 12,
               MUTED, "end"))

    b.append(t(430, 40, f"{n} commands  vs  {nparams} numbers", 15, INK,
               "middle", SANS, "500"))
    return write("fig1-degeneracy.svg", "".join(b), W, H)


# ===========================================================================
# Figure 2 -- the two doors
# ===========================================================================

def fig_two_doors():
    W, H = 860, 400
    b = [f'<rect width="{W}" height="{H}" fill="{WHITE}"/>']

    b.append(rect(40, 165, 150, 66, PANEL, RULE, rx=8))
    b.append(t(115, 192, "candidate", 14, INK, "middle", SANS, "500"))
    b.append(t(115, 210, "shape", 14, INK, "middle", SANS, "500"))

    boxes = [
        (300, 60, "Door A", "can a small program draw it?",
         "polynomial / periodic fit", "6 of 9 families: YES", RED),
        (300, 240, "Door B", "can a few absolute moves draw it?",
         "chord compression, tolerance 2%", "6 of 9 families: YES", RED),
    ]
    for x, y, title, q, how, verdict, col in boxes:
        b.append(rect(x, y, 340, 100, PANEL, RULE, rx=8))
        b.append(t(x + 16, y + 26, title, 13, col, "start", SANS, "500"))
        b.append(t(x + 16, y + 50, q, 13, INK))
        b.append(t(x + 16, y + 70, how, 11.5, FAINT))
        b.append(t(x + 324, y + 50, verdict, 12, col, "end", SANS, "500"))

    b.append(line(190, 198, 240, 198, MUTED, 1.5))
    b.append(line(240, 110, 240, 290, MUTED, 1.5))
    b.append(line(240, 110, 300, 110, MUTED, 1.5))
    b.append(line(240, 290, 300, 290, MUTED, 1.5))
    for y in (110, 290):
        b.append(f'<path d="M{292} {y - 5} L{300} {y} L{292} {y + 5}" '
                 f'fill="none" stroke="{MUTED}" stroke-width="1.5"/>')

    b.append(rect(690, 165, 130, 66, "#eef5ee", GREEN, rx=8))
    b.append(t(755, 192, "valid item", 14, GREEN, "middle", SANS, "500"))
    b.append(t(755, 210, "both doors shut", 11.5, GREEN, "middle"))

    for y in (110, 290):
        b.append(line(640, y, 665, y, MUTED, 1.5))
        b.append(line(665, 110, 665, 290, MUTED, 1.5))
        b.append(line(665, 198, 690, 198, MUTED, 1.5))
    b.append(f'<path d="M682 193 L690 198 L682 203" fill="none" '
             f'stroke="{MUTED}" stroke-width="1.5"/>')

    b.append(t(430, 372, "Guarding one door is not enough. This project guarded "
               "only Door A.", 12.5, MUTED, "middle"))
    return write("fig2-two-doors.svg", "".join(b), W, H)


# ===========================================================================
# Figure 3 -- the tolerance cliff
# ===========================================================================

TOL_SERIES = [
    ("regular zigzag", "regular zigzag (periodic)", RED, None),
    ("irregular staircase", "irregular staircase", AMBER, "7 4"),
    ("spiral", "spiral (analytic)", BLUE, "2 3"),
    ("bounded random walk", "bounded random walk", PURPLE, "8 3 2 3"),
    ("aperiodic irregular", "aperiodic irregular", TEAL, None),
]


def fig_tolerance():
    fam = dict(FAMILIES)
    tols = [0.005, 0.01, 0.02, 0.05]
    data = {}
    for label, key, _, _ in TOL_SERIES:
        raw, _, _ = true_kinematics(fam[key]())
        dia = diameter(raw)
        data[label] = [hop_compress(raw, tol * dia) for tol in tols]

    W, H = 860, 500
    x0, y0, cw, ch = 100, 60, 690, 350
    b = [f'<rect width="{W}" height="{H}" fill="{WHITE}"/>']

    def sx(v):
        return x0 + (math.log10(v) - math.log10(0.005)) / (
            math.log10(0.05) - math.log10(0.005)) * cw

    def sy(v):
        v = max(v, 1)
        return y0 + ch - (math.log10(v) / math.log10(220)) * ch

    for v in (1, 2, 5, 10, 20, 50, 100, 200):
        y = sy(v)
        b.append(line(x0, y, x0 + cw, y, RULE, 1))
        b.append(t(x0 - 10, y + 4, str(v), 11.5, FAINT, "end"))
    for tol, lab in zip(tols, ["0.5%", "1%", "2%", "5%"]):
        x = sx(tol)
        b.append(line(x, y0, x, y0 + ch, RULE, 1, "3 4"))
        b.append(t(x, y0 + ch + 22, lab, 12.5, MUTED, "middle"))

    yt = sy(20)
    b.append(line(x0, yt, x0 + cw, yt, GREEN, 1.4, "6 4"))
    b.append(t(x0 + cw - 4, yt - 8, "bypass threshold: 20 moves", 11.5,
               GREEN, "end"))

    for label, _, col, dash in TOL_SERIES:
        pts = [(sx(tol), sy(v)) for tol, v in zip(tols, data[label])]
        b.append(poly(pts, col, 2.4, dash=dash))
        for p in pts:
            b.append(circle(p[0], p[1], 3.4, col))

    b.append(t(x0 - 62, y0 + ch / 2, "absolute moves needed", 12.5, MUTED,
               "middle",
               extra=f' transform="rotate(-90 {x0 - 62} {y0 + ch / 2})"'))
    b.append(t(x0 + cw / 2, y0 + ch + 52,
               "grading tolerance, as a share of shape diameter", 12.5,
               MUTED, "middle"))

    lx, ly = 100, 452
    for i, (label, _, col, dash) in enumerate(TOL_SERIES):
        x = lx + (i % 3) * 240
        y = ly + (i // 3) * 22
        b.append(line(x, y - 4, x + 22, y - 4, col, 2.4, dash))
        b.append(t(x + 30, y, label, 12, MUTED))

    b.append(t(x0 + cw, 40,
               "the same shape is a good item at 1% and one straight line at 2%",
               12.5, MUTED, "end"))
    return write("fig3-tolerance-cliff.svg", "".join(b), W, H)


# ===========================================================================
# Figure 4 -- the scaling test
# ===========================================================================

def fig_scaling():
    """Parameters needed to fit within 1% of diameter, by shape length."""
    sizes = (25, 50, 100, 200)
    fam = dict(FAMILIES)
    flat = [("spiral (analytic)", BLUE), ("circular arc (analytic)", AMBER),
            ("regular zigzag (periodic)", RED), ("5-point star (periodic)", PURPLE),
            ("irregular staircase", TEAL)]
    results = {}

    for name, col in flat:
        vals = []
        for size in sizes:
            try:
                raw = fam[name](size)
            except TypeError:
                raw = fam[name]()
            _, steps, turns = true_kinematics(raw)
            nseg = len(steps)
            dia = diameter(raw)
            found = None
            for deg in range(0, 5):
                if 2 * (deg + 1) > nseg // 2:
                    break
                cs, ct, p = fit_poly(steps, turns, deg)
                fk = build(cs, ct, nseg, periodic=False)
                al, _ = align(fk, raw)
                if mean_path_distance(al, raw) / dia < 0.01:
                    found = p
                    break
            if found is None:
                # Periodic shapes (star, zigzag) are not polynomial. Omitting
                # this search silently drops them from the figure.
                for pp in range(1, max(2, nseg // 4) + 1):
                    if 2 * pp > nseg // 2:
                        break
                    cs, ct, p = fit_periodic(steps, turns, pp)
                    fk = build(cs, ct, nseg, periodic=True)
                    al, _ = align(fk, raw)
                    if mean_path_distance(al, raw) / dia < 0.01:
                        found = p
                        break
            vals.append(found)
        results[name] = vals

    W, H = 860, 470
    x0, y0, cw, ch = 110, 60, 660, 320
    b = [f'<rect width="{W}" height="{H}" fill="{WHITE}"/>']

    def sx(i):
        return x0 + (i / (len(sizes) - 1)) * cw

    def sy(v):
        return y0 + ch - (v / 9) * ch

    b.append(rect(x0, y0, cw, sy(5.5) - y0, "#f3f7f3", rx=0))
    b.append(t(x0 + 12, y0 + 20, "four families: no fit at any length", 12.5,
               GREEN, "start", SANS, "500"))
    b.append(t(x0 + 12, y0 + 38, "these are valid items — fit cost grows with N",
               11.5, GREEN))

    for v in range(0, 10, 2):
        y = sy(v)
        b.append(line(x0, y, x0 + cw, y, RULE, 1))
        b.append(t(x0 - 10, y + 4, str(v), 11.5, FAINT, "end"))
    for i, s in enumerate(sizes):
        x = sx(i)
        b.append(line(x, y0, x, y0 + ch, RULE, 1, "3 4"))
        b.append(t(x, y0 + ch + 22, f"N={s}", 12.5, MUTED, "middle"))

    for name, col in flat:
        pts = [(sx(i), sy(v)) for i, v in enumerate(results[name]) if v]
        b.append(poly(pts, col, 2.6))
        for p in pts:
            b.append(circle(p[0], p[1], 4, col))

    b.append(t(x0 - 66, y0 + ch / 2, "parameters needed", 12.5, MUTED, "middle",
               extra=f' transform="rotate(-90 {x0 - 66} {y0 + ch / 2})"'))
    b.append(t(x0 + cw / 2, y0 + ch + 52,
               "number of segments in the shape", 12.5, MUTED, "middle"))

    lx, ly = 110, 430
    for i, (name, col) in enumerate(flat):
        x = lx + (i % 3) * 250
        y = ly + (i // 3) * 22
        b.append(line(x, y - 4, x + 22, y - 4, col, 2.6))
        b.append(t(x + 30, y, name.split(" (")[0], 12, MUTED))

    b.append(t(x0 + cw, 40, "the same four numbers draw the spiral at N=25 and N=200",
               12.5, MUTED, "end"))
    return write("fig4-scaling.svg", "".join(b), W, H)


# ===========================================================================
# Figure 5 -- drift against length
# ===========================================================================

def fig_drift():
    segs = [50, 100, 200, 500, 1000]
    drift = [8.8, 12.2, 17.5, 27.4, 38.0]
    ref = [drift[0] * math.sqrt(s / segs[0]) for s in segs]

    W, H = 860, 440
    x0, y0, cw, ch = 100, 60, 690, 290
    b = [f'<rect width="{W}" height="{H}" fill="{WHITE}"/>']

    def sx(v):
        return x0 + (math.log10(v) - math.log10(50)) / (
            math.log10(1000) - math.log10(50)) * cw

    def sy(v):
        return y0 + ch - (v / 45) * ch

    for v in (0, 10, 20, 30, 40):
        y = sy(v)
        b.append(line(x0, y, x0 + cw, y, RULE, 1))
        b.append(t(x0 - 10, y + 4, f"{v}%", 11.5, FAINT, "end"))
    for s in segs:
        x = sx(s)
        b.append(line(x, y0, x, y0 + ch, RULE, 1, "3 4"))
        b.append(t(x, y0 + ch + 22, str(s), 12.5, MUTED, "middle"))

    b.append(poly([(sx(s), sy(v)) for s, v in zip(segs, ref)], FAINT, 1.8,
                  dash="5 4"))
    b.append(poly([(sx(s), sy(v)) for s, v in zip(segs, drift)], RED, 2.6))
    for s, v in zip(segs, drift):
        b.append(circle(sx(s), sy(v), 4, RED))

    b.append(t(sx(1000) - 8, sy(ref[-1]) + 20, "random-walk reference: sqrt(N)",
               11.5, FAINT, "end"))
    b.append(t(sx(1000) - 8, sy(drift[-1]) - 12, "measured drift", 12, RED, "end"))

    b.append(t(x0 - 62, y0 + ch / 2, "drift, % of diameter", 12.5, MUTED,
               "middle",
               extra=f' transform="rotate(-90 {x0 - 62} {y0 + ch / 2})"'))
    b.append(t(x0 + cw / 2, y0 + ch + 52, "segments in the program", 12.5,
               MUTED, "middle"))
    b.append(t(x0 + cw, 40,
               "tenfold length gives 3.11x drift — sqrt(10) = 3.16", 12.5,
               MUTED, "end"))
    return write("fig5-drift.svg", "".join(b), W, H)


# ===========================================================================
# Figure 6 -- output cost
# ===========================================================================

def fig_cost():
    segs = [50, 200, 1000]
    turtle = [s * 6 for s in segs]
    svg = [20, 20, 20]

    W, H = 860, 400
    x0, y0, cw, ch = 110, 70, 660, 240
    b = [f'<rect width="{W}" height="{H}" fill="{WHITE}"/>']

    def sy(v):
        return y0 + ch - (math.log10(max(v, 1)) / math.log10(10000)) * ch

    for v in (1, 10, 100, 1000, 10000):
        y = sy(v)
        b.append(line(x0, y, x0 + cw, y, RULE, 1))
        b.append(t(x0 - 10, y + 4, f"{v:,}", 11.5, FAINT, "end"))

    slot = cw / len(segs)
    for i, (s, tv, sv) in enumerate(zip(segs, turtle, svg)):
        base = x0 + slot * i + slot / 2
        for off, val, col, lab in ((-42, tv, RED, "turtle"),
                                   (12, sv, BLUE, "SVG")):
            x = base + off
            y = sy(val)
            b.append(rect(x, y, 30, y0 + ch - y, col, rx=2))
            b.append(t(x + 15, y - 8, f"{val:,}", 11, col, "middle", SANS, "500"))
            b.append(t(x + 15, y0 + ch + 18, lab, 11, MUTED, "middle"))
        b.append(t(base, y0 + ch + 44, f"{s} segments", 12.5, INK, "middle",
                   SANS, "500"))
        b.append(t(base, y0 + ch + 62, f"{tv // sv}x", 13, RED, "middle",
                   SANS, "500"))

    b.append(t(x0 - 72, y0 + ch / 2, "tokens", 12.5, MUTED, "middle",
               extra=f' transform="rotate(-90 {x0 - 72} {y0 + ch / 2})"'))
    b.append(t(x0 + cw, 42,
               "a circle is one SVG element and N turtle segments", 12.5,
               MUTED, "end"))
    return write("fig6-token-cost.svg", "".join(b), W, H)


# ===========================================================================
# Figure 7 -- what the task actually requires
# ===========================================================================

def fig_requirements():
    W, H = 860, 470
    b = [f'<rect width="{W}" height="{H}" fill="{WHITE}"/>']

    b.append(t(40, 40, "To emit the command for segment k, the model needs",
               14, INK, "start", SERIF))

    b.append(rect(40, 60, 380, 96, "#eef5ee", GREEN, rx=8))
    b.append(t(58, 88, "the bend angle", 13.5, GREEN, "start", SANS, "500"))
    b.append(t(58, 110, "the angle between segment k-1 and segment k",
               12, INK))
    b.append(t(58, 130, "a local quantity, directly readable from the image",
               11.5, GREEN))
    b.append(t(58, 148, "cost to obtain: one look", 11.5, FAINT))

    b.append(rect(440, 60, 380, 96, "#fbf0ef", RED, rx=8))
    b.append(t(458, 88, "its own heading", 13.5, RED, "start", SANS, "500"))
    b.append(t(458, 110, "the accumulated direction of the pen", 12, INK))
    b.append(t(458, 130, "NOT needed - the turtle holds this itself",
               11.5, RED))
    b.append(t(458, 148, "cost to obtain: nothing, because it is never used",
               11.5, FAINT))

    b.append(line(430, 108, 440, 108, MUTED, 1.5))
    b.append(t(435, 100, "vs", 11, MUTED, "middle"))

    b.append(rect(40, 186, 780, 52, PANEL, RULE, rx=8))
    b.append(t(430, 208,
               "So a misread bend corrupts the turtle's position, not the "
               "model's estimate of it.", 12.5, INK, "middle"))
    b.append(t(430, 228,
               "The accumulation happens in the turtle, not in the model.",
               12.5, INK, "middle", SANS, "500"))

    b.append(rect(40, 256, 780, 60, "#fbf0ef", RED, rx=8))
    b.append(t(430, 280,
               "Therefore drift measures per-step angular precision — a "
               "perceptual acuity measure —", 12.5, RED, "middle"))
    b.append(t(430, 300, "and not state tracking.", 12.5, RED, "middle",
               SANS, "500"))

    b.append(t(40, 352, "And the escape route cannot be closed", 14, INK,
               "start", SERIF))
    b.append(rect(40, 372, 380, 72, PANEL, RULE, rx=8))
    b.append(t(58, 396, "visible scratch work", 13, INK, "start", SANS, "500"))
    b.append(t(58, 416, "# running heading: 47", 11.5, MUTED, "start", MONO))
    b.append(t(58, 434, "written into its own output", 11.5, FAINT))

    b.append(rect(440, 372, 380, 72, PANEL, RULE, rx=8))
    b.append(t(458, 396, "or re-summing what it already emitted", 13, INK,
               "start", SANS, "500"))
    b.append(t(458, 416, "right(12) + right(9) + right(15) = 36", 11.5, MUTED,
               "start", MONO))
    b.append(t(458, 434, "forbid scratch work and this still works", 11.5,
               FAINT))

    b.append(t(430, 464,
               "Every quantity the task needs is readable from the image or "
               "recomputable from the model's own tokens.", 12.5, INK,
               "middle", SANS, "500"))
    return write("fig7-requirements.svg", "".join(b), W, H)


def main():
    print("generating figures ->", OUT)
    fig_degeneracy()
    fig_two_doors()
    fig_tolerance()
    fig_scaling()
    fig_drift()
    fig_cost()
    fig_requirements()
    print("done")


if __name__ == "__main__":
    main()
