"""Emit SVG path data for the degeneracy visual.

Two paths in a shared coordinate frame, so the overlay is exact:
  TRUE -- the canonical spiral, 199 segments
  FAKE -- the best state-free program from the sweep (polynomial degree 2),
          rigidly aligned to TRUE

Both are normalised into a 260x260 box centred on the origin, so the widget
can place them with a plain <g transform="translate(...)">.
"""
from degeneracy_sweep import (N_PTS, align, build, centroid, diameter,
                              fam_spiral, fit_poly, mean_path_distance,
                              true_kinematics)

BOX = 260.0

raw, steps, turns = true_kinematics(fam_spiral(N_PTS))
n = len(steps)

cs, ct, nparams = fit_poly(steps, turns, 3)
fake = build(cs, ct, n, periodic=False)
aligned_fake, deg = align(fake, raw)

dia = diameter(raw)
err = mean_path_distance(aligned_fake, raw) / dia

cx, cy = centroid(raw)
true_c = [(p[0] - cx, p[1] - cy) for p in raw]

allpts = true_c + aligned_fake
span = max(max(abs(p[0]) for p in allpts), max(abs(p[1]) for p in allpts)) * 2.0
scale = BOX / span


def to_path(pts):
    out = []
    for i, (px, py) in enumerate(pts):
        cmd = "M" if i == 0 else "L"
        out.append(f"{cmd}{px * scale:.1f} {py * scale:.1f}")
    return " ".join(out)


print(f"segments={n}  params={nparams}  err={err * 100:.2f}%  rot={deg}deg")
print(f"step  coeffs (u in [-1,1]): {[round(c, 3) for c in cs]}")
print(f"turn  coeffs (u in [-1,1]): {[round(c, 3) for c in ct]}")
print()
print("TRUE:")
print(to_path(true_c))
print()
print("FAKE:")
print(to_path(aligned_fake))
