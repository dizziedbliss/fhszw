"""One real round trip: HTTP -> create_app() defaults -> live Elexon -> engine.

January 2026 is history, so the answer key from the golden test must hold. If this
fails while the golden test passes, Elexon changed their API or revised the data."""

import pytest
from fastapi.testclient import TestClient

from wind.api import create_app

pytestmark = pytest.mark.live


def test_live_elexon_still_gives_the_january_15_answer_key() -> None:
    response = TestClient(create_app()).get(
        "/api/decision", params={"today": "2026-01-15", "slot": "09:30"}
    )

    assert response.status_code == 200, response.text
    body = response.json()
    week, fortnight = body["windows"]
    assert body["tomorrow"]["total_mwh"] == 191_402
    assert (week["half_hours"], fortnight["half_hours"]) == (336, 672)
    assert (week["mae_mw"], fortnight["mae_mw"]) == pytest.approx(
        (2200.886905, 2123.721726), abs=1e-5
    )
    assert (body["band"]["lower_miss_mw"], body["band"]["upper_miss_mw"]) == pytest.approx(
        (-949.5, 4491.5), abs=1e-6
    )
