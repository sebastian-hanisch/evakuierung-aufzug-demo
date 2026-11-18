"""Handbeispiel (aus der Planung, handbeispiel_02.py): zwei Etagen, von Hand gerechnet, gegen den Kern geprüft.

Etage 1: 1 Person mit Aufzugspflicht und 2 Gehende; Etage 2: 1 Person mit Aufzugspflicht und 1 Gehende. Treppe 2 Personen je Zeitschritt und Flucht,
Gehzeit 2; Aufzug 1 Zeitschritt je Etage, Halt 1, Kapazität 3.

Von Hand, eine Kabine:
  Fahrt mit höchster Etage h und s Halten: 2*h + s + 1. Pflichtgruppe (1, 1) in einer Fahrt: 2*2 + 2 + 1 = 7, Ankunft 7 - 1 = 6.
  Getrennte Fahrten (Einzelhalt): (2 + 1 + 1) + (4 + 1 + 1) = 10, Ankunft 9: Bündeln spart 3 Zeitschritte.
  Treppe für die Gehenden (2, 1): Etage 1 Ankunft 0 + 2 = 2; Etage 2 geht bei 0, kommt bei 2 in Etage 1 an, geht weiter, Ankunft 4: Treppenzeit 4.
  Alle Gehenden auf der Treppe: max(4, 6) = 6. Freiwillige: eine Fahrt hat Platz für 3, die Pflichtgruppe belegt 2, eine Gehende kann mitfahren, ohne die Fahrt zu verlängern.
  Optimal sind (0,0), (1,0), (0,1): T* = 6, kleinste Zahl Freiwilliger 0, größte 1, drei optimale Aufteilungen.
  Fluss (Takt): erste Abfahrt an Etage f bei f + 1, Ankunft f später: Etage 2 Ankunft 5; die Gehenden brauchen 4: Fluss 5, T* - Fluss = 1.
  Fluss (Rate): an Etage 2 (Dauer 6, Durchsatz 3 je 6 Zeitschritte) erste Kapazität im Zeitschritt 4, Ankunft 6: 6.
Zwei Kabinen: Etage 2 Fahrt 6 (Ankunft 5), Etage 1 Fahrt 4 (Ankunft 3): Aufzugszeit 5, T* = 5 = Fluss. Kapazität 1: zwei Fahrten 4 + 6 - 1 = 9."""

import evk_algorithm as A

MANDATORY, FREE = (1, 1), (2, 1)


def test_one_cabin():
    p = A.Params(cabins=1, capacity=3, halt=1, stairs=2)
    lift = A.Lift(p)
    assert lift.time((1, 1)) == 6
    assert A.single_stop_time((1, 1), p, "exact") == 9 and A.single_stop_time((1, 1), p, "lpt") == 9
    assert A.stairs_time(FREE, 2, 2) == 4
    j = A.joint_exact(MANDATORY, FREE, p)
    assert (j.time, j.a_min, j.a_max, j.n_optimal, j.time_stairs_only) == (6, 0, 1, 3, 6)
    assert lift.time((2, 1)) == 6 and lift.time((1, 2)) == 6 and lift.time((3, 1)) == 9 and lift.time((2, 2)) == 9
    assert A.flow_time(MANDATORY, FREE, p, "takt") == 5
    assert A.flow_time(MANDATORY, FREE, p, "rate") == 6
    assert A.barrier_time(MANDATORY, p) == 6
    assert max(A.flow_time(MANDATORY, FREE, p, "takt"), A.barrier_time(MANDATORY, p)) == 6


def test_two_cabins_close_the_gap():
    p = A.Params(cabins=2, capacity=3, halt=1, stairs=2)
    assert A.joint_exact(MANDATORY, FREE, p).time == 5
    assert A.barrier_time(MANDATORY, p) == 5 and A.flow_time(MANDATORY, FREE, p, "takt") == 5


def test_capacity_one_cannot_bundle():
    p = A.Params(cabins=1, capacity=1, halt=1, stairs=2)
    assert A.Lift(p).time((1, 1)) == 9 and A.single_stop_time((1, 1), p, "exact") == 9
    assert A.joint_exact(MANDATORY, FREE, p).time == 9


def test_the_rule_is_violated_and_the_flow_is_one_step_short():
    p = A.Params(cabins=1, capacity=3, halt=1, stairs=2)
    barrier, flow, exact = A.barrier_time(MANDATORY, p), A.flow_time(MANDATORY, FREE, p, "takt"), A.joint_exact(MANDATORY, FREE, p).time
    assert barrier > flow and exact - flow == 1          # Regel R (Schranke <= Fluss) gilt nicht, der Fluss liegt 1 unter T*
