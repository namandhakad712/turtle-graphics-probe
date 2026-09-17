"""Emit SVG path data showing the true spiral against the closed-form fake."""
import math

N = 90
THETA_MAX = 2.0 * 2 * math.pi
R0, R1 = 14.0, 104.0

pts = []
for i in range(N + 1):
    t = THETA_MAX * i / N
    r = R0 + (R1 - R0) * t / THETA_MAX
    pts.append((r * math.cos(t), r * math.sin(t)))

segs = [math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
        for i in range(N)]
turns = []
for i in range(1, N):
    a0 = math.atan2(pts[i][1] - pts[i - 1][1], pts[i][0] - pts[i - 1][0])
    a1 = math.atan2(pts[i + 1][1] - pts[i][1], pts[i + 1][0] - pts[i][0])
    d = math.degrees(a1 - a0)
    while d > 180.0:
        d -= 360.0
    while d < -180.0:
        d += 360.0
    turns.append(d)

tm = sum(turns) / len(turns)
sm = sum(segs) / len(segs)
n = len(segs)
mi = (n - 1) / 2.0
b = sum((i - mi) * (segs[i] - sm) for i in range(n)) / sum((i - mi) ** 2 for i in range(n))
a = sm - b * mi

# true path, shifted so its start sits at the origin
canon = [(p[0] - pts[0][0], p[1] - pts[0][1]) for p in pts]

# the three-constant fake, same start
px = py = 0.0
heading = 0.0
fake = [(0.0, 0.0)]
for i in range(N):
    heading -= math.radians(tm)
    px += (a + b * i) * math.cos(heading)
    py += (a + b * i) * math.sin(heading)
    fake.append((px, py))

xs = [p[0] for p in canon]
ys = [p[1] for p in canon]
cx0 = (max(xs) + min(xs)) / 2.0
cy0 = (max(ys) + min(ys)) / 2.0
span = max(max(xs) - min(xs), max(ys) - min(ys))
scale = 270.0 / span

CX, CY = 340.0, 190.0


def emit(path):
    out = []
    for i, (x, y) in enumerate(path):
        sx = CX + (x - cx0) * scale
        sy = CY - (y - cy0) * scale
        out.append(("M" if i == 0 else "L") + f"{sx:.1f} {sy:.1f}")
    return " ".join(out)


print(f"scale={scale:.3f}  span={span:.1f}")
print("TRUE:")
print(emit(canon))
print("FAKE:")
print(emit(fake))
