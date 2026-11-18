"""End-to-end Smoke-Test via Streamlits AppTest: lädt app.py, klickt jeden Button, fährt jeden Regler (Schieberegler, Zahlenfeld, Auswahl) an Minimum und Maximum,
prüft Permalink, Presets und den Worst Case am Regler-Maximum (Timeout statt Zeit-Assertion). Fängt `StreamlitDuplicateElementId` (Charts ohne eindeutiges key=)
und Abstürze bei Reglern mit berechneten Grenzen."""

import os

import pytest
from streamlit.testing.v1 import AppTest

import evk_constants as C

APP_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")
TIMEOUT = int(os.environ.get("APPTEST_TIMEOUT", "300"))  # unter Last (parallele Läufe) reichen 180 s nicht immer; Umgebungsvariable zum Anpassen
BIGGEST_BUILDING_SEED = 318      # 4 Etagen mit je 6 Personen (24 Menschen): der größte Fall der Regler


def _fresh_app() -> AppTest:
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=TIMEOUT)
    assert not at.exception, [str(e) for e in at.exception]
    return at


def test_app_loads_without_exception_and_shows_the_main_results():
    at = _fresh_app()
    assert [m.label for m in at.metric][:4] == ["Räumungszeit exakt (T*)", "Reines Flussmodell", "Fluss plus Maschinenschranke", "Alle Gehenden auf der Treppe"]
    assert len(at.get("plotly_chart")) >= 6 and not at.error


def test_every_button_click_does_not_raise():
    labels = [b.label for b in _fresh_app().button]
    assert len(labels) == len(C.PRESETS) + 1                        # sieben Presets und „Neues Gebäude“
    for index in range(len(labels)):
        at = _fresh_app()
        at.button[index].click().run(timeout=TIMEOUT)
        assert not at.exception, (labels[index], [str(e) for e in at.exception])


@pytest.mark.parametrize("key", ["floors_slider", "share_slider", "cabins_slider", "capacity_slider", "halt_slider", "stairs_slider"])
@pytest.mark.parametrize("edge", ["min", "max"])
def test_every_slider_at_its_min_and_max_does_not_raise(key, edge):
    at = _fresh_app()
    slider = at.sidebar.slider(key=key)
    slider.set_value(int(slider.min if edge == "min" else slider.max)).run(timeout=TIMEOUT)
    assert not at.exception, (key, edge, [str(e) for e in at.exception])
    assert at.metric[0].value.endswith("Zeitschritte")


@pytest.mark.parametrize("value", [C.SEED_MIN, C.SEED_MAX, BIGGEST_BUILDING_SEED])
def test_seed_field_at_its_bounds(value):
    at = _fresh_app()
    at.sidebar.number_input(key="seed_input").set_value(value).run(timeout=TIMEOUT)
    assert not at.exception, [str(e) for e in at.exception]


def test_every_option_of_the_waiting_area_selectors_does_not_raise():
    at = _fresh_app()
    for key, options in (("wait_share", C.WAIT_SHARES), ("wait_q", C.WAIT_OVERFLOW), ("wait_places", C.WAIT_PLACES)):
        for option in options:
            at.radio(key=key).set_value(option).run(timeout=TIMEOUT)
            assert not at.exception, (key, option, [str(e) for e in at.exception])
    at.sidebar.slider(key="cabins_slider").set_value(2).run(timeout=TIMEOUT)
    assert not at.exception


def test_permalink_is_clamped_and_snapped_to_the_grid():
    at = AppTest.from_file(APP_PATH)
    at.query_params["share"] = "23"       # nicht auf dem 5-%-Raster der Messreihe
    at.query_params["floors"] = "9"       # über der Reglergrenze
    at.query_params["seed"] = "0"
    at.run(timeout=TIMEOUT)
    assert not at.exception, [str(e) for e in at.exception]
    assert at.sidebar.slider(key="share_slider").value == 25 and at.sidebar.slider(key="floors_slider").value == 4
    assert at.sidebar.number_input(key="seed_input").value == C.SEED_MIN


@pytest.mark.parametrize("share", [C.SHARE_MIN, C.SHARE_MAX])
@pytest.mark.parametrize("cabins,capacity", [(2, 2), (1, 4), (1, 1)])
def test_worst_case_at_the_slider_maximum(share, cabins, capacity):
    """Vier Etagen mit je 6 Personen, längster Halt, langsamste Treppe: der größte Aufzählungsraum (7^4 Aufteilungen); Timeout statt Zeit-Assertion."""
    at = _fresh_app()
    at.sidebar.slider(key="floors_slider").set_value(C.FLOORS_MAX)
    at.sidebar.slider(key="halt_slider").set_value(C.HALT_MAX)
    at.sidebar.slider(key="stairs_slider").set_value(C.STAIRS_MIN)
    at.sidebar.slider(key="cabins_slider").set_value(cabins)
    at.sidebar.slider(key="capacity_slider").set_value(capacity)
    at.sidebar.slider(key="share_slider").set_value(share)
    at.sidebar.number_input(key="seed_input").set_value(BIGGEST_BUILDING_SEED).run(timeout=60)
    assert not at.exception, [str(e) for e in at.exception]
    assert any("24 Menschen" in c.value for c in at.caption)
