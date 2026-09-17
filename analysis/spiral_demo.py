"""Generate spiral paths for the explainer diagram: exact vs drifted."""
import math
import random

N = 90
THETA_MAX = 2.0 * 2 * math.pi
R0, R1 = 14.0, 104.0


def spiral(drift_deg_per_step=0.0, noise_deg=0.0, seed=1):
    rng = random.Random(seed)
    x = y = 0.0
    pts = [(0.0, 0.0)]
    for i in range(N):
        t0 = THETA_MAX * i / N
        t1 = THETA_MAX * (i + 1) / N
        ra = R0 + (R1 - R0) * t0 / THETA_MAX
        rb = R0 + (R1 - R0) * t1 / THETA_MAX
        ix = rb * math.cos(t1) - ra * math.cos(t0)
        iy = rb * math.sin(t1) - ra * math.sin(t0)
        seg = math.hypot(ix, iy)
        seg_ang = math.atan2(iy, ix)
        heading = (seg_ang
                   + math.radians(drift_deg_per_step * (i + 1))
                   + math.radians(rng.gauss(0, noise_deg)))
        x += seg * math.cos(heading)
        y += seg * math.sin(heading)
        pts.append((x, y))
    return pts


def to_svg_path(pts, cx, cy):
    out = []
    for i, (x, y) in enumerate(pts):
        out.append(("M" if i == 0 else "L") + f"{cx + x:.1f} {cy - y:.1f}")
    return " ".join(out)


correct = spiral(0.0, 0.0)
drifted = spiral(0.28, 0.35, seed=7)

gap = math.hypot(correct[-1][0] - drifted[-1][0], correct[-1][1] - drifted[-1][1])
print(f"correct end: ({correct[-1][0]:.1f}, {correct[-1][1]:.1f})")
print(f"drifted end: ({drifted[-1][0]:.1f}, {drifted[-1][1]:.1f})")
print(f"endpoint gap: {gap:.1f} units (spiral outer radius = {R1})")
print()
print("CORRECT:")
print(to_svg_path(correct, 175, 172))
print()
print("DRIFTED:")
print(to_svg_path(drifted, 175, 172))
