"""Kern gegen Handrechnung (Einheit für Einheit, DEMO-PLAYBOOK §1b): Treppe, Fahrtdauer, Aufzug, Aufteilung, Fluss, Schranke, Prüfer.

Die Erwartungswerte stehen als Rechnung im Test (nicht als Zahl, die der Code liefert)."""

import pytest

import evk_algorithm as A
import evk_scenario as S
from evk_rng import SplitMix64


# ------------------------------------------------------------------ Treppe

def test_stairs_two_persons_leave_together_and_arrive_after_the_walk_time():
    assert A.stairs_exits((2,), 2, 2) == ((2, 2),)          # beide gehen im Zeitschritt 0, Ankunft 0 + 2
    assert A.stairs_time((2,), 2, 2) == 2


def test_stairs_queue_on_the_bottleneck_flight():
    # vier Personen auf Etage 1, 2 je Zeitschritt: Abgang bei 0 und 1, Ankunft 2 und 3
    assert A.stairs_exits((4,), 2, 2) == ((2, 2), (3, 2))
    assert A.stairs_time((4,), 2, 2) == 3


def test_stairs_person_from_the_second_floor_needs_two_flights():
    assert A.stairs_time((0, 1), 2, 2) == 4                 # 2 Zeitschritte je Flucht, zwei Fluchten
    assert A.stairs_time((2, 1), 2, 2) == 4                 # Handbeispiel: die Fluchten sind frei, kein Stau


def test_stairs_empty_group_needs_no_time():
    assert A.stairs_time((0, 0, 0), 2, 2) == 0
    assert A.stairs_exits((0, 0), 2, 2) == ()


# ------------------------------------------------------------------ Fahrtdauer und Aufzug

def test_trip_duration_by_hand():
    assert A.trip_duration((1, 1), halt=1, lift_time=1) == 7      # 2*2 + 2 Halte + 1 Entladen
    assert A.trip_duration((2, 0), halt=1, lift_time=1) == 4      # 2*1 + 1 Halt + 1
    assert A.trip_duration((0, 1), halt=1, lift_time=1) == 6      # 2*2 + 1 + 1


def test_trip_duration_formula_is_height_plus_stops():
    # Dauer = 2 * höchste Etage * Etagenzeit + Halte * Halt + Halt (Entladen): Beispiel Etage 3, ein Halt, Halt 2, Etagenzeit 1: 6 + 2 + 2 = 10
    assert A.trip_duration((0, 0, 3), halt=2, lift_time=1) == 10


def test_lift_single_trip_with_two_stops_beats_two_trips(hand):
    lift = A.Lift(hand["params"])
    assert lift.time((1, 1)) == 6                           # eine Fahrt: 7 - 1
    assert A.single_stop_time((1, 1), hand["params"], "exact") == 9   # (2+1+1) + (4+1+1) - 1


def test_lift_capacity_forces_two_trips(hand):
    lift = A.Lift(hand["params"])
    assert lift.time((2, 2)) == 9                           # 4 Personen, Kapazität 3: zwei Fahrten (2,0) = 4 und (0,2) = 6, zusammen 10 - 1; andere Zerlegungen ergeben 10 bis 13
    assert lift.time((2, 1)) == 6 and lift.time((1, 2)) == 6   # Platz für 3: die Mitfahrt verlängert die Fahrt nicht


def test_lift_without_persons_needs_no_time(hand):
    assert A.Lift(hand["params"]).time((0, 0)) == 0


def test_two_cabins_split_the_trips():
    two = A.Params(cabins=2, capacity=3, halt=1, stairs=2)
    assert A.Lift(two).time((1, 1)) == 5                    # Kabine A: Etage 2 (6 - 1), Kabine B: Etage 1 (4 - 1): max(5, 3)


def test_capacity_one_cannot_bundle():
    one = A.Params(cabins=1, capacity=1, halt=1, stairs=2)
    assert A.Lift(one).time((1, 1)) == 9                    # (2+1+1) + (4+1+1) - 1


def test_lift_plan_lists_the_trips_and_the_last_arrival(hand):
    plan = A.Lift(hand["params"]).plan((1, 1))
    assert [[t.load for t in cab] for cab in plan] == [[(1, 1)]]
    trip = plan[0][0]
    assert (trip.start, trip.arrival, trip.end) == (0, 6, 7)


# ------------------------------------------------------------------ gemeinsames Modell

def test_joint_exact_by_hand(hand):
    j = A.joint_exact(hand["mandatory"], hand["free"], hand["params"])
    assert j.time == 6 and j.time_stairs_only == 6          # Pflichtgruppe 6 gegen Treppe 4
    assert (j.a_min, j.a_max, j.n_optimal) == (0, 1, 3)     # (0,0), (1,0), (0,1)
    assert j.split == (0, 0)


def test_joint_exact_second_cabin_closes_the_gap(hand):
    two = A.Params(cabins=2, capacity=3, halt=1, stairs=2)
    assert A.joint_exact(hand["mandatory"], hand["free"], two).time == 5


def test_joint_exact_voluntary_use_helps_when_the_stairs_bind():
    # eine Etage, keine Pflicht, 6 Gehende, Treppe 2 je Zeitschritt (Ankünfte 2, 2, 3, 3, 4, 4: Treppe allein 4), Kabine für 3 mit Halt 1:
    # drei in den Aufzug: Fahrt 2 + 1 + 1 = 4, Ankunft 3; drei auf der Treppe: Ankünfte 2, 2, 3. T = 3 statt 4.
    p = A.Params(cabins=1, capacity=3, halt=1, stairs=2)
    j = A.joint_exact((0,), (6,), p)
    assert (j.time, j.time_stairs_only) == (3, 4)
    assert j.a_min >= 1 and j.a_min <= j.a_max <= 3


# ------------------------------------------------------------------ Fluss und Schranke

def test_flow_takt_and_rate_by_hand(hand):
    assert A.flow_time(hand["mandatory"], hand["free"], hand["params"], "takt") == 5     # Etage 2: Abfahrt 3, Ankunft 5
    assert A.flow_time(hand["mandatory"], hand["free"], hand["params"], "rate") == 6     # erste Kapazität an Etage 2 im Zeitschritt 4, Ankunft 6


def test_flow_closed_form_for_one_floor_of_mandatory_persons():
    # n Personen nur auf Etage f, E Kabinen mit K Plätzen: Abfahrten bei f + d + j * (2f + 2d), Ankunft f später; ceil(n / (E K)) Abfahrten nötig:
    # T = 2 f + d + (ceil(n / (E K)) - 1) * (2 f + 2 d)
    for f, n, e, k, d in [(1, 5, 1, 2, 1), (2, 7, 2, 3, 1), (3, 4, 1, 4, 2), (2, 1, 2, 4, 2)]:
        p = A.Params(cabins=e, capacity=k, halt=d, stairs=2)
        mandatory = tuple(n if i == f - 1 else 0 for i in range(f))
        expected = 2 * f + d + (-(-n // (e * k)) - 1) * (2 * f + 2 * d)
        assert A.flow_time(mandatory, (0,) * f, p, "takt") == expected, (f, n, e, k, d)


def test_barrier_is_the_lift_time_of_the_mandatory_group_alone(hand):
    assert A.barrier_time(hand["mandatory"], hand["params"]) == 6
    assert A.barrier_time((0, 0), hand["params"]) == 0


def test_chain_flow_barrier_exact_stairs_only(hand):
    p = hand["params"]
    flow = A.flow_time(hand["mandatory"], hand["free"], p, "takt")
    k1 = max(flow, A.barrier_time(hand["mandatory"], p))
    j = A.joint_exact(hand["mandatory"], hand["free"], p)
    assert flow <= k1 <= j.time <= j.time_stairs_only


def test_single_stop_versions_overestimate_in_the_hand_example(hand):
    p = hand["params"]
    assert A.single_stop_time((1, 1), p, "exact") == 9 and A.single_stop_time((1, 1), p, "lpt") == 9


def test_measure_row_matches_the_single_functions(hand):
    row = dict(zip(A.COLUMNS, A.measure(hand["mandatory"], hand["free"], hand["params"])))
    assert (row["exact"], row["a_min"], row["a_max"], row["stairs_only"], row["n_optimal"]) == (6, 0, 1, 6, 3)
    assert (row["barrier"], row["stairs_all_free"], row["flow_takt"], row["flow_rate"], row["k1"]) == (6, 4, 5, 6, 6)
    assert (row["k1_lpt"], row["k1_single"]) == (9, 9)


# ------------------------------------------------------------------ Prüfer

def test_checker_accepts_the_optimal_plan(hand):
    p = hand["params"]
    j = A.joint_exact(hand["mandatory"], hand["free"], p)
    plan = [list(c) for c in A.Lift(p).plan(tuple(m + a for m, a in zip(hand["mandatory"], j.split)))]
    assert A.evaluate_plan(hand["mandatory"], hand["free"], j.split, plan, p) == ([], 6)


def test_checker_finds_each_kind_of_violation(hand):
    p = hand["params"]
    ok = A.Trip((1, 1), 0, 6, 7)
    assert A.evaluate_plan(hand["mandatory"], hand["free"], (0, 0), [[A.Trip((1, 2), 0, 6, 7)]], p)[0]          # falsche Zahl befördert
    assert A.evaluate_plan(hand["mandatory"], hand["free"], (0, 0), [[A.Trip((2, 2), 0, 9, 10)]], p)[0]        # über der Kapazität
    assert A.evaluate_plan(hand["mandatory"], hand["free"], (0, 0), [[A.Trip((1, 1), 0, 5, 6)]], p)[0]         # falsche Dauer
    assert A.evaluate_plan(hand["mandatory"], hand["free"], (0, 0), [[ok], [ok]], p)[0]                        # zu viele Kabinen
    assert A.evaluate_plan(hand["mandatory"], hand["free"], (3, 0), [[ok]], p)[0]                              # Aufteilung über der Zahl der Gehenden
    assert A.evaluate_plan(hand["mandatory"], hand["free"], (0, 0), [[A.Trip((1, 1), 0, 6, 7), A.Trip((0, 0), 7, 13, 14)]], p)[0]   # leere Fahrt


# ------------------------------------------------------------------ Szenario

def test_building_is_deterministic_and_the_shares_are_nested():
    b1, b2 = S.make_building(7, 3), S.make_building(7, 3)
    assert b1 == b2 and all(3 <= m <= 6 for m in b1.persons)
    previous = (0,) * 3
    for share in range(0, 45, 5):
        mandatory, free = b1.split(share)
        assert all(x >= y for x, y in zip(mandatory, previous))          # geschachtelt: mehr Anteil, mehr Pflicht
        assert all(m + f == p for m, f, p in zip(mandatory, free, b1.persons))
        previous = mandatory
    assert b1.split(0)[0] == (0, 0, 0)


def test_rng_is_splitmix64_with_known_first_value():
    # Referenzwert des SplitMix64-Algorithmus (Vigna) für Zustand 0: erste Ausgabe 0xE220A8397B1DCDAF
    assert SplitMix64(0).next() == 0xE220A8397B1DCDAF
    assert all(0 <= SplitMix64(5).below(6) < 6 for _ in range(20))
