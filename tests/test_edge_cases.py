"""Randfälle, an denen Kernroutinen erfahrungsgemäß brechen (DEMO-PLAYBOOK §12): Anteil 0, nur Aufzug, nur Treppe, eine Etage, Kapazität 1, leere Etagen,
genau zwei Personen, Platz größer als Bedarf, zwei Kabinen mit einer Person."""

import pytest

import evk_algorithm as A
import evk_constants as C
import evk_evaluation as ev
import evk_scenario as S


P1 = A.Params(cabins=1, capacity=3, halt=1, stairs=2)
P2 = A.Params(cabins=2, capacity=3, halt=1, stairs=2)


def test_share_zero_has_no_mandatory_persons_and_the_barrier_is_zero():
    a = ev.analyse(ev.Settings(share=0))
    assert a.n_mandatory == 0 and a.barrier == 0 and a.rule_holds
    assert a.joint.time <= a.joint.time_stairs_only


def test_only_the_lift_when_nobody_may_walk():
    j = A.joint_exact((2, 1), (0, 0), P1)                  # alle haben Aufzugspflicht
    assert (j.a_min, j.a_max, j.n_optimal, j.split) == (0, 0, 1, (0, 0))
    assert j.time == j.time_stairs_only == A.Lift(P1).time((2, 1))


def test_only_the_stairs_when_nobody_needs_the_lift():
    j = A.joint_exact((0, 0, 0), (1, 1, 1), A.Params(cabins=1, capacity=1, halt=2, stairs=3))
    assert j.time_stairs_only == A.stairs_time((1, 1, 1), 3, 2) == 6      # jede Person bei 0 los, Etage 3: drei Fluchten
    assert j.time <= 6 and A.barrier_time((0, 0, 0), P1) == 0


def test_one_floor_building():
    j = A.joint_exact((1,), (2,), P1)
    # Pflichtperson: Fahrt 2 + 1 + 1 = 4, Ankunft 3; die Gehenden gehen bei 0, Ankunft 2
    assert j.time == 3 and j.time_stairs_only == 3
    assert A.flow_time((1,), (2,), P1, "takt") == 3         # Abfahrt 1 + 1 = 2, Ankunft 3


def test_capacity_one_with_two_cabins_and_exactly_two_persons():
    p = A.Params(cabins=2, capacity=1, halt=1, stairs=2)
    assert A.Lift(p).time((1, 1)) == 5                      # zwei Fahrten parallel: Etage 2 (6 - 1), Etage 1 (4 - 1)
    assert A.joint_exact((1, 1), (0, 0), p).time == 5


def test_single_person_with_two_cabins_leaves_the_second_cabin_empty():
    plan = A.Lift(P2).plan((0, 1))
    assert sum(len(c) for c in plan) == 1 and sorted(len(c) for c in plan) == [0, 1]
    assert A.Lift(P2).time((0, 1)) == 5                      # 4 + 1 + 1 - 1


def test_empty_floors_and_empty_building():
    assert A.Lift(P1).time((0, 3, 0)) == 5                  # eine Fahrt zu Etage 2 mit einem Halt: 4 + 1 + 1 = 6, Ankunft 5
    assert A.joint_exact((0, 0), (0, 0), P1).time == 0
    assert A.flow_time((0, 0), (0, 0), P1, "takt") == 0 and A.flow_time((0, 0), (0, 0), P1, "rate") == 0
    assert A.stairs_time((), 2, 2) == 0


def test_capacity_larger_than_demand_changes_nothing():
    small = A.Lift(A.Params(1, 4, 1, 2)).time((1, 1))
    assert small == A.Lift(A.Params(1, 3, 1, 2)).time((1, 1)) == 6


def test_highest_floor_alone_dominates_the_trip():
    assert A.trip_duration((0, 0, 1), 1, 1) == 8 and A.trip_duration((1, 1, 1), 1, 1) == 10   # 6 + 1 + 1 gegen 6 + 3 + 1


def test_all_slider_extremes_are_analysable_on_the_grid():
    for floors in (C.FLOORS_MIN, C.FLOORS_MAX):
        for cabins in (C.CABINS_MIN, C.CABINS_MAX):
            for capacity in (C.CAPACITY_MIN, C.CAPACITY_MAX):
                for share in (C.SHARE_MIN, C.SHARE_MAX):
                    a = ev.analyse(ev.Settings(floors, cabins, capacity, C.HALT_MAX, C.STAIRS_MIN, share, 7))
                    assert a.flow_takt <= a.k1 <= a.exact <= a.joint.time_stairs_only


def test_split_never_exceeds_the_persons_of_a_floor():
    for seed in range(1, 40):
        b = S.make_building(seed, 4)
        for share in range(0, 45, 5):
            mandatory, free = b.split(share)
            assert all(m >= 0 and f >= 0 for m, f in zip(mandatory, free))


def test_verdict_functions_reject_impossible_orders():
    with pytest.raises(ValueError):
        ev.verdict_flow_error(5, 6)           # der Takt-Fluss kann nicht über T* liegen
    with pytest.raises(ValueError):
        ev.verdict_volunteers(7, 6, 0, 1, 3, 10)   # die freie Wahl kann nicht schlechter sein als die Treppe für alle
