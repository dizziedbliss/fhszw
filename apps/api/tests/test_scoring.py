from collections.abc import Callable, Sequence

import pytest

from wind import scoring


def test_mae_is_the_average_size_of_a_miss_ignoring_direction() -> None:
    # |+100| + |-300| + |+200| = 600 over 3 misses
    assert scoring.mae([100, -300, 200]) == 200


def test_rmse_punishes_big_misses_more_than_mae() -> None:
    # sqrt((10^2 + 70^2) / 2) = sqrt(2500) = 50, while the MAE would be 40
    assert scoring.rmse([10, -70]) == 50


def test_bias_keeps_the_sign_so_highs_and_lows_cancel() -> None:
    # (+100 - 300 + 500) / 3 = +100: on balance the forecast ran high
    assert scoring.bias([100, -300, 500]) == 100


@pytest.mark.parametrize("formula", [scoring.mae, scoring.rmse, scoring.bias])
def test_scoring_nothing_is_refused_rather_than_reported_as_zero(
    formula: Callable[[Sequence[float]], float],
) -> None:
    with pytest.raises(scoring.NoMissesError):
        formula([])


@pytest.mark.parametrize(
    ("pct", "expected"),
    [
        (90, 46),  # sorted position (5-1) * 0.9 = 3.6 -> 40 + 0.6 * (50 - 40)
        (10, 14),  # sorted position (5-1) * 0.1 = 0.4 -> 10 + 0.4 * (20 - 10)
    ],
)
def test_percentile_blends_the_two_neighbours_of_its_sorted_position(
    pct: float, expected: float
) -> None:
    assert scoring.percentile([50, 10, 40, 20, 30], pct) == pytest.approx(expected)


def test_percentile_of_nothing_is_refused() -> None:
    with pytest.raises(scoring.NoMissesError):
        scoring.percentile([], 90)


def test_direction_agreement_scores_moves_and_counts_flat_ones_it_skips() -> None:
    moves = [
        (+100, +50),  # both up: agree
        (-20, -10),  # both down: agree
        (+30, -40),  # forecast up, actual down: disagree
        (0, +10),  # forecast flat: no direction to judge
        (+10, 0),  # actual flat: no direction to judge
    ]

    result = scoring.direction_agreement(moves)

    assert (result.scored, result.flat_skipped) == (3, 2)
    assert result.pct == pytest.approx(66.667, abs=1e-3)  # 2 of 3


def test_direction_agreement_with_only_flat_moves_has_no_percentage() -> None:
    result = scoring.direction_agreement([(0, 5), (5, 0)])

    assert (result.pct, result.scored, result.flat_skipped) == (None, 0, 2)
