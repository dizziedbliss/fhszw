"""Textbook error formulas. Pure functions over misses (forecast - actual, in MW)."""

import math
from collections.abc import Sequence
from dataclasses import dataclass


class NoMissesError(ValueError):
    """Raised when asked to score an empty set: there is no honest number to give."""


def _require(misses: Sequence[float]) -> None:
    if not misses:
        raise NoMissesError("no misses to score")


def mae(misses: Sequence[float]) -> float:
    """Mean absolute error: the average size of a miss, ignoring direction."""
    _require(misses)
    return sum(abs(m) for m in misses) / len(misses)


def rmse(misses: Sequence[float]) -> float:
    """Root mean square error: squares misses first, so big misses weigh more."""
    _require(misses)
    return math.sqrt(sum(m * m for m in misses) / len(misses))


def bias(misses: Sequence[float]) -> float:
    """Mean miss with its sign. Positive means the forecast ran high on balance."""
    _require(misses)
    return sum(misses) / len(misses)


def percentile(values: Sequence[float], pct: float) -> float:
    """Linear-interpolated percentile (numpy's default method), pct in 0..100."""
    _require(values)
    ordered = sorted(values)
    position = (len(ordered) - 1) * pct / 100
    lower = math.floor(position)
    upper = math.ceil(position)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


@dataclass(frozen=True)
class DirectionAgreement:
    """Share of moves where forecast and actual went the same way.

    pct is None when no move had a direction on both sides; the counts say why.
    """

    pct: float | None
    scored: int
    flat_skipped: int


def direction_agreement(moves: Sequence[tuple[float, float]]) -> DirectionAgreement:
    """Shape MDA over (forecast change, actual change) pairs. Flat moves are skipped."""
    judged = [(f, a) for f, a in moves if f != 0 and a != 0]
    agreed = sum(1 for f, a in judged if (f > 0) == (a > 0))
    pct = 100 * agreed / len(judged) if judged else None
    return DirectionAgreement(pct=pct, scored=len(judged), flat_skipped=len(moves) - len(judged))
