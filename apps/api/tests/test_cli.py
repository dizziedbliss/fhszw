import json

import pytest

from tests.recorded import recorded_elexon
from wind import cli


def test_cli_prints_the_decision_for_a_day_and_slot_as_json(
    capsys: pytest.CaptureFixture[str],
) -> None:
    cli.main(["2026-01-15", "09:30"], transport=recorded_elexon())

    view = json.loads(capsys.readouterr().out)
    assert (view["tomorrow"]["delivery_day"], view["tomorrow"]["total_mwh"]) == (
        "2026-01-16",
        191_402,
    )
