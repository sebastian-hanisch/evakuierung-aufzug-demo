"""Vorgerechnete Messreihen (data/evk_results.json, data/evk_wait.json): Aufbau, Ordnungsketten, Zweigtests (keine tote Variante), Neu-Rechnen einer Stichprobe.

Alles ist ganzzahlig und ohne C-Bibliothek gerechnet: das Neu-Rechnen stimmt auf jeder Plattform exakt (kein Band nötig)."""

import itertools

import numpy as np
import pytest

import evk_algorithm as A
import evk_constants as C
import evk_results as R
import evk_scenario as S

CELLS = R.all_cells()


def test_structure_every_slider_combination_has_a_cell_with_270_rows():
    expected = set(itertools.product(range(2, 5), range(1, 3), range(1, 5), range(2, 4), range(1, 3)))
    assert set(CELLS) == expected and len(CELLS) == 96
    for c in CELLS:
        assert R.cell(*c).shape == (30, 9, 14)
    meta = R.load()["meta"]
    assert meta["seeds"] == list(range(1, 31)) and meta["shares_pct"] == list(range(0, 45, 5)) and meta["columns"][:2] == ["n_mandatory", "n_free"]


def test_order_chain_in_every_row():
    for c in CELLS:
        flow, barrier, k1 = R.col(c, "flow_takt"), R.col(c, "barrier"), R.col(c, "k1")
        exact, sep = R.col(c, "exact"), R.col(c, "stairs_only")
        assert (flow <= k1).all() and (k1 <= exact).all() and (exact <= sep).all(), c                    # Fluss <= Fluss + Schranke <= T* <= alle Gehenden Treppe
        assert (barrier <= k1).all() and (R.col(c, "k1_single") >= k1).all() and (R.col(c, "k1_lpt") >= R.col(c, "k1_single")).all(), c
        assert (R.col(c, "a_min") <= R.col(c, "a_max")).all() and (R.col(c, "n_optimal") >= 1).all()


def test_persons_per_building_are_constant_over_the_shares():
    for c in CELLS[:12]:
        total = R.col(c, "n_mandatory") + R.col(c, "n_free")
        assert (total == total[:, :1]).all() and ((total >= 3 * c[0]) & (total <= 6 * c[0])).all()
        assert (np.diff(R.col(c, "n_mandatory"), axis=1) >= 0).all()                                      # geschachtelte Mengen


def test_recomputing_a_sample_reproduces_the_stored_rows_exactly():
    for cfg, seeds in [((2, 1, 2, 2, 1), (1, 7)), ((3, 2, 3, 3, 2), (2, 30)), ((4, 1, 1, 2, 1), (5,)), ((4, 2, 4, 3, 1), (11,)), ((3, 1, 3, 2, 1), (1, 2, 3))]:
        floors, cabins, capacity, stairs, halt = cfg
        p = A.Params(cabins, capacity, halt, stairs)
        for seed in seeds:
            building = S.make_building(seed, floors)
            for i, share in enumerate(C.SHARES):
                mandatory, free = building.split(share)
                row = [sum(mandatory), sum(free), *A.measure(mandatory, free, p)]
                assert row == R.cell(*cfg)[seed - 1, i].tolist(), (cfg, seed, share)


# ------------------------------------------------------------------ Zweigtests: jede Variante weicht irgendwo von der Nachbarvariante ab

def _differs(cell_a, cell_b, name="exact"):
    return int((R.col(cell_a, name) != R.col(cell_b, name)).sum())


def test_every_variant_changes_the_result_somewhere():
    assert _differs((3, 1, 3, 2, 1), (3, 2, 3, 2, 1)) > 100         # zweite Kabine
    assert _differs((3, 1, 1, 2, 1), (3, 1, 2, 2, 1)) > 100         # Kapazität 1 gegen 2
    assert _differs((3, 1, 2, 2, 1), (3, 1, 3, 2, 1)) > 100         # Kapazität 2 gegen 3
    assert _differs((3, 1, 4, 2, 1), (3, 1, 3, 2, 1)) > 20          # Kapazität 4 gegen 3
    assert _differs((3, 1, 3, 2, 1), (3, 1, 3, 2, 2)) > 100         # Halt 2 gegen 1
    assert _differs((3, 1, 3, 2, 1), (3, 1, 3, 3, 1)) > 20          # Treppe 3 gegen 2
    assert _differs((2, 1, 3, 2, 1), (3, 1, 3, 2, 1)) > 100         # Etagen
    for a, b in [("flow_takt", "exact"), ("flow_rate", "flow_takt"), ("k1", "flow_takt"), ("k1", "exact"), ("k1_single", "k1"), ("k1_lpt", "k1_single"), ("stairs_only", "exact")]:
        assert sum(int((R.col(c, a) != R.col(c, b)).sum()) for c in CELLS) > 0, (a, b)


def test_columns_that_are_mostly_zero_are_explained_and_not_all_zero():
    names = R.load()["meta"]["columns"]
    for name in names:
        zeros = sum(int((R.col(c, name) == 0).sum()) for c in CELLS)
        total = sum(R.col(c, name).size for c in CELLS)
        assert zeros < total, name                                   # keine Spalte mit lauter Nullen (sonst läuft die Variante nie)
    # a_min ist meist 0 (Aufteilung ohne Freiwillige ist oft optimal), a_max aber in vielen Zeilen positiv: beide Zweige laufen
    assert sum(int((R.col(c, "a_min") > 0).sum()) for c in CELLS) > 1000
    assert sum(int((R.col(c, "a_max") > 0).sum()) for c in CELLS) > 10000
    # barrier ist 0 genau dort, wo niemand Aufzugspflicht hat
    for c in CELLS[:20]:
        assert ((R.col(c, "barrier") == 0) == (R.col(c, "n_mandatory") == 0)).all()


def test_the_flow_is_below_exact_for_one_and_two_cabins_and_free_choice_helps():
    for cabins in (1, 2):
        cells = [c for c in CELLS if c[1] == cabins]
        assert sum(int((R.col(c, "flow_takt") < R.col(c, "exact")).sum()) for c in cells) > 500
        assert sum(int((R.col(c, "exact") < R.col(c, "stairs_only")).sum()) for c in cells) > 200


# ------------------------------------------------------------------ Hilfsfunktionen der Auswertung

def test_tipping_helper_on_synthetic_columns():
    cfg = (3, 1, 3, 2, 1)
    points = R.tipping_points(cfg, "exact")
    assert len(points) == 30 and all(p in list(C.SHARES[1:]) + [R.NEVER] for p in points)
    values = R.col(cfg, "exact")
    for s, p in enumerate(points):                                  # Gegenprobe ohne die Hilfsfunktion: kleinster Anteil mit T* über dem bei Anteil 0
        first = next((C.SHARES[i] for i in range(1, 9) if values[s, i] > values[s, 0]), R.NEVER)
        assert p == first
    assert R.tipping_count(cfg) == sum(1 for p in points if p < R.NEVER)


def test_rule_counts_add_up():
    r = R.rule_counts(CELLS)
    assert r["true"] + r["false"] == len(CELLS) * 30 * 8
    assert r["true_hit"] <= r["true"] and r["false_hit"] <= r["false"] and r["false_exact"] == 0


# ------------------------------------------------------------------ Wartebereich (CP-SAT, vorgerechnet)

def test_waiting_data_structure_and_unlimited_column_equals_the_exact_model():
    wait = R.load_wait()
    assert wait["meta"]["floors"] == 3 and wait["meta"]["capacity"] == 3
    assert len(wait["data"]) == 2 * 3 * 10                          # Kabinen x Anteile x (unbegrenzt + 3 Plätze x 3 Überläufe)
    for cabins in (1, 2):
        p = A.Params(cabins, 3, 1, 2)
        for share in C.WAIT_SHARES:
            rows = R.wait_rows(cabins, share, -1, 0)
            assert [r[0] for r in rows] == list(range(1, 31))
            for seed, t_star, t_wait, _ in rows[:6]:
                mandatory, free = S.make_building(seed, 3).split(share)
                assert t_star == t_wait == A.joint_exact(mandatory, free, p).time


def test_waiting_effect_is_monotone_in_the_places_and_in_the_overflow_for_every_seed():
    for cabins, share in itertools.product((1, 2), C.WAIT_SHARES):
        for q in (1, 2, 4):
            t = {w: [r[2] for r in R.wait_rows(cabins, share, w, q)] for w in (2, 1, 0)}
            unlimited = [r[2] for r in R.wait_rows(cabins, share, -1, 0)]
            for u, t2, t1, t0 in zip(unlimited, t[2], t[1], t[0]):
                assert u <= t2 <= t1 <= t0
        for w in (2, 1, 0):
            by_q = {q: [r[2] for r in R.wait_rows(cabins, share, w, q)] for q in (1, 2, 4)}
            assert all(a >= b >= c for a, b, c in zip(by_q[1], by_q[2], by_q[4]))                 # mehr Überlauf je Platz, weniger Rückstau


def test_waiting_branch_runs_and_the_second_cabin_is_the_bigger_lever():
    effect = R.wait_effect(1, 20, 0, 2)
    assert effect["seeds_affected"] > 0 and effect["mean_effect"] > 0                              # W = 0 wirkt (Zweigtest)
    for share in (30, 40):
        gain = R.wait_effect(1, share, 0, 2)["mean_time"] - R.wait_effect(2, share, 0, 2)["mean_time"]
        assert gain > 5 * R.wait_effect(1, share, 0, 2)["mean_effect"]


def test_waiting_rows_can_be_recomputed_with_cpsat():
    pytest.importorskip("ortools")
    import evk_cpsat as CS
    for cabins, share, places, q, seed in [(1, 20, 0, 2, 1), (2, 40, 1, 1, 3)]:
        row = next(r for r in R.wait_rows(cabins, share, places, q) if r[0] == seed)
        p = A.Params(cabins, 3, 1, 2)
        mandatory, free = S.make_building(seed, 3).split(share)
        t_star = A.joint_exact(mandatory, free, p).time
        t, _ = CS.min_time(mandatory, free, p, lo=t_star, places=places, q=q, workers=4)
        assert t == row[2] and row[1] == t_star
