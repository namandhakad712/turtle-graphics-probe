"""Drape — giving a language model a pen, and asking what that can measure.

A small, zero-dependency harness that hands a language model an image and a
turtle, and asks it to redraw the image under a set of controlled conditions.

The original premise was that turtle graphics would expose visual reasoning:
that a model reproducing an image through imperative relative commands would
have to hold spatial state, and that measuring its drift would reveal how well
it does so. That premise did not survive analysis.

What the analysis established:

  - Smooth analytic shapes are degenerate items. A 199-command spiral is
    reproduced to 0.27% of its diameter by eight numbers.
  - Degeneracy has two doors, not one. A shape must be expensive both to
    express as a small program AND to express as a few absolute moves.
  - Degeneracy is not a property of a shape. It is a property of the shape,
    the grading tolerance, and the search class together. A regular zigzag
    needs 199 absolute moves at 1% tolerance and 1 move at 2%.
  - Escape-hatch usage cannot be read as self-monitoring. A model can reach
    any landmark by reading it off the image, with no accumulated state at
    all, so using `goto` is not evidence that anything was tracked.
  - Drift accumulates in the turtle, not in the model, so the drift metric
    measures per-step angular precision rather than state tracking.

The conclusion is that this route cannot answer whether a model reasons
visually, because every quantity the task requires is either readable locally
from the image or recomputable by summing the model's own emitted tokens. What
remains measurable is narrower: whether a perceptual shortcut beats a
text-strategy baseline.

This package is the interpreter, and it is the part of the work that is sound.
Model output is never executed.
"""

__version__ = "0.2.0"
