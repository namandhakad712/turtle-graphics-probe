"""Run every analysis script and write its output to results/.

Stdlib only. No dependencies, no network, no API keys -- every number in the
paper is produced by this script, from fixed seeds, in about thirty seconds.

    python analysis/run_all.py
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "results")

SCRIPTS = [
    ("turtle_drift", "drift and token cost versus program length"),
    ("shape_degeneracy", "first, single-sided degeneracy test (superseded)"),
    ("degeneracy_sweep", "two-sided item validity, scaling test, floor check"),
    ("degeneracy_svg", "raw path data for the overlay figure"),
    ("degeneracy_widget", "figure data: item versus an eight-number program"),
    ("spiral_demo", "correct versus drifted spiral, for the plain-terms explainer"),
]


def main():
    os.makedirs(OUT, exist_ok=True)
    failed = []
    for name, desc in SCRIPTS:
        print(f"  {name:<20} {desc}")
        proc = subprocess.run(
            [sys.executable, os.path.join(HERE, name + ".py")],
            cwd=HERE, capture_output=True, text=True,
        )
        dest = os.path.join(OUT, name + ".txt")
        # newline="\n" is not cosmetic: without it Python translates to CRLF on
        # Windows, and a re-run in a fresh clone shows up as a modified file
        # even when the content is identical.
        with open(dest, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(proc.stdout)
            if proc.stderr:
                fh.write("\n--- stderr ---\n")
                fh.write(proc.stderr)
        if proc.returncode != 0:
            failed.append(name)
            print(f"    FAILED (exit {proc.returncode}) -- see results/{name}.txt")
        else:
            print(f"    ok -> results/{name}.txt  ({len(proc.stdout.splitlines())} lines)")

    print()
    if failed:
        print(f"  {len(failed)} script(s) failed: {', '.join(failed)}")
        return 1

    # The floor check is the assertion the rest of the work depends on. If the
    # exact program does not score zero, every other number is suspect.
    sweep = os.path.join(OUT, "degeneracy_sweep.txt")
    with open(sweep, encoding="utf-8") as fh:
        text = fh.read()
    if "worst floor: 0.0000%" not in text:
        print("  FLOOR CHECK DID NOT PASS -- do not trust the results above.")
        return 1
    print("  floor check passed: the exact program scores 0.0000%.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
