"""Verdikte an von Hand gesetzten Werten (DEMO-PLAYBOOK §12): jede Schwelle und jede Zahl im Text steht hier."""

import pytest

import evk_evaluation as ev


def test_de_and_steps_helpers():
    assert ev.de(2.5) == "2,5" and ev.de(0.4666, 2) == "0,47" and ev.de(21.0, 0) == "21"
    assert ev.steps(1) == "1 Zeitschritt" and ev.steps(0) == "0 Zeitschritte" and ev.steps(5) == "5 Zeitschritte"


def test_flow_error_exact_one_and_large():
    kind, text = ev.verdict_flow_error(9, 9)
    assert kind == "success" and "beide 9 Zeitschritte" in text
    kind, text = ev.verdict_flow_error(6, 5)                                    # Lücke 1
    assert kind == "info" and "nur 1 Zeitschritt unter" in text and "(5 statt 6, 17 % von T*)" in text
    kind, text = ev.verdict_flow_error(21, 9)                                   # Lücke 12 von 21 = 57 %
    assert kind == "warning" and "**12 Zeitschritte**" in text and "9 statt 21" in text and "57 % von T*" in text


def test_flow_error_rejects_a_flow_above_the_exact_time():
    with pytest.raises(ValueError):
        ev.verdict_flow_error(5, 6)


COUNTS = ((12786, 12816), (1134, 10224))


def test_rule_without_mandatory_persons():
    kind, text = ev.verdict_rule(True, 0, 7, 7, *COUNTS)
    assert kind == "success" and "Keine Person mit Aufzugspflicht" in text and "0 Zeitschritte" in text


def test_rule_holds_and_hits():
    kind, text = ev.verdict_rule(True, 6, 7, 7, *COUNTS)
    assert kind == "success" and "allein 6 ≤ Fluss 7" in text and "(0 Zeitschritte)" in text and "in 12786 von 12816 Zellen" in text
    kind, text = ev.verdict_rule(True, 6, 7, 8, *COUNTS)                        # Lücke 1: Fluss höchstens 1 unter T*
    assert kind == "success" and "(1 Zeitschritt)" in text


def test_rule_holds_but_misses():
    kind, text = ev.verdict_rule(True, 6, 7, 10, *COUNTS)                       # Lücke 3
    assert kind == "warning" and "6 ≤ 7" in text and "3 Zeitschritte unter T*" in text and "sind es 30 von 12816 Zellen" in text


def test_rule_fails():
    kind, text = ev.verdict_rule(False, 9, 7, 9, *COUNTS)
    assert kind == "warning" and "9 > Fluss 7" in text and "2 Zeitschritte unter T*" in text and "nur in 1134 von 10224 Zellen" in text


def test_volunteers_help():
    kind, text = ev.verdict_volunteers(7, 8, 2, 3, 13, 0)
    assert kind == "success" and "7 Zeitschritte statt 8" in text and "Mindestens 2 von 13" in text and "höchstens 3" in text


def test_volunteers_do_not_help():
    kind, text = ev.verdict_volunteers(9, 9, 0, 2, 9, 9)
    assert kind == "info" and "T* = 9" in text and "(die Pflichtgruppe allein braucht im Aufzug 9)" in text and "Bis zu 2 von 9 Gehenden" in text
    kind, text = ev.verdict_volunteers(9, 9, 0, 0, 9, 6)                        # Stau auf der Treppe, niemand darf mitfahren
    assert "Pflichtgruppe" not in text and "Keine der 9 Gehenden darf" in text
    assert "keine Gehenden" in ev.verdict_volunteers(6, 6, 0, 0, 0, 6)[1]


def test_volunteers_reject_a_worse_plan_than_all_on_stairs():
    with pytest.raises(ValueError):
        ev.verdict_volunteers(7, 6, 0, 1, 3, 5)


def test_tipping_threshold_and_names():
    kind, text = ev.verdict_tipping(15.0, 30, 30, 1, 37.5, 18)
    assert kind == "warning" and "Mit 1 Kabine kippt die Räumung im Median bei 15 % Aufzugspflicht (30 von 30 Zufalls-Seeds kippen bis 40 %)" in text
    assert "mit 2 Kabinen bei 37,5 % (18 von 30)" in text
    assert ev.verdict_tipping(20.0, 30, 30, 1, 45.0, 4)[0] == "warning"        # genau 20: inklusive Grenze
    kind, text = ev.verdict_tipping(25.0, 28, 30, 2, 15.0, 30)
    assert kind == "info" and "Mit 2 Kabinen kippt" in text and "mit 1 Kabine bei 15 %" in text
    assert "über 40 %" in ev.verdict_tipping(45.0, 1, 30, 2, 15.0, 30)[1]


def test_waiting_verdicts():
    kind, text = ev.verdict_waiting(0.0, 0, 30, 3.5, -1)
    assert kind == "info" and "Unbegrenzter Wartebereich" in text
    kind, text = ev.verdict_waiting(0.47, 11, 30, 2.03, 0)
    assert kind == "success" and "Mit 0 Warteplätzen je Etage" in text and "um 0,47 Zeitschritte (11 von 30" in text and "um 2,03" in text
    assert ev.verdict_waiting(0.5, 15, 30, 1.0, 1)[0] == "success"              # genau 0,5: inklusive Grenze
    kind, text = ev.verdict_waiting(0.97, 17, 30, 2.0, 1)
    assert kind == "info" and "Mit 1 Warteplatz je Etage" in text


def test_evacuation_curve_totals():
    a = ev.analyse(ev.Settings(seed=121))
    curve = ev.evacuation_curve(a)
    assert len(curve["total"]) == a.exact + 1 and curve["total"][-1] == a.building.total and curve["total"][0] == 0
    assert all(x <= y for x, y in zip(curve["total"], curve["total"][1:]))
