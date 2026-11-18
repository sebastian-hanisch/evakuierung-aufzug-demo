"""Orakel-Tests: Kern gegen unabhängige Rechenwege (DEMO-PLAYBOOK §12, ORACLE-PLAYBOOK §2).

  * Treppenzeit (Simulation) gegen den Maximalfluss im Zeitnetz: networkx und `linprog` (zwei unabhängige Löser).
  * Aufzug (Pareto-DP über Fahrtenmengen) gegen eine Vollaufzählung aller Fahrtenpläne mit Mehrfachhalt (andere Zustandsdarstellung: verbleibende Personen und
    sortierte Freizeiten der Kabinen).
  * Gemeinsames exaktes Modell gegen die Vollaufzählung aller Aufteilungen mit diesen beiden Orakeln und gegen CP-SAT auf dem Zeitnetz (T* zulässig, T* - 1 unzulässig).
  * Wartebereich (CP-SAT, tools/evk_cpsat.py): unbegrenzt gleich exaktem Modell, monoton in den Plätzen, Rückstau wirkt auf einer festen Instanz.
  * Maximalfluss des Kerns (scipy, Dinic) gegen networkx auf demselben Netz; Prüfer gegen den Plan jeder Zufallsinstanz.
Schnelle Fassung (wenige Sekunden). Der große Lauf mit mindestens 200 Zufallsinstanzen steht im Scratch-Ordner (tools/oracle_lauf.py) und ist in VERGLEICH.md berichtet."""

import itertools
from functools import lru_cache

import pytest

import evk_algorithm as A
from evk_rng import SplitMix64

nx = pytest.importorskip("networkx")
np = pytest.importorskip("numpy")


# ------------------------------------------------------------------ Orakel Treppe

def stairs_graph(able, stairs, walk, horizon):
    """Zeitnetz der Treppe als networkx-Graph: Knoten (Etage, Zeit); Warten unbegrenzt, Flucht f -> f - 1 mit Kapazität `stairs`, Etage 1 -> Senke."""
    g = nx.DiGraph()
    for f in range(1, len(able) + 1):
        if able[f - 1]:
            g.add_edge("Q", (f, 0), capacity=able[f - 1])
        for t in range(horizon):
            g.add_edge((f, t), (f, t + 1))
        for t in range(horizon - walk + 1):
            g.add_edge((f, t), "S" if f == 1 else (f - 1, t + walk), capacity=stairs)
    return g


def nx_stairs_time(able, stairs, walk):
    total = sum(able)
    if total == 0:
        return 0
    for horizon in range(0, 60):
        g = stairs_graph(able, stairs, walk, horizon)
        if "S" in g and "Q" in g and nx.maximum_flow_value(g, "Q", "S") == total:
            return horizon
    raise AssertionError("keine Zeit gefunden")


def lp_max_flow(g, source, sink):
    """Maximalfluss als LP (scipy, HiGHS): Erhaltung an allen inneren Knoten, Kapazitäten als Schranken."""
    from scipy.optimize import linprog
    edges = list(g.edges(data="capacity"))
    nodes = [v for v in g.nodes if v not in (source, sink)]
    index = {v: i for i, v in enumerate(nodes)}
    a_eq = np.zeros((len(nodes), len(edges)))
    cost = np.zeros(len(edges))
    for k, (u, v, cap) in enumerate(edges):
        if u in index:
            a_eq[index[u], k] -= 1
        if v in index:
            a_eq[index[v], k] += 1
        if v == sink:
            cost[k] = -1
    res = linprog(cost, A_eq=a_eq, b_eq=np.zeros(len(nodes)), bounds=[(0, cap) for _, _, cap in edges], method="highs")
    assert res.status == 0
    return round(-res.fun)


def stairs_feasible(able, stairs, walk, horizon, solver):
    """Bringt der Maximalfluss im Zeitnetz mit Horizont `horizon` alle hinaus? solver: 'networkx' oder 'linprog'."""
    if sum(able) == 0:
        return True                                  # nichts zu räumen: jeder Horizont reicht
    g = stairs_graph(able, stairs, walk, horizon)
    if "S" not in g or "Q" not in g:
        return False
    value = nx.maximum_flow_value(g, "Q", "S") if solver == "networkx" else lp_max_flow(g, "Q", "S")
    return value == sum(able)


def test_stairs_time_is_the_smallest_feasible_horizon_in_two_independent_solvers():
    """T reicht und T - 1 reicht nicht, gerechnet als Maximalfluss im Zeitnetz (networkx und linprog)."""
    rng = SplitMix64(31)
    cases = []
    for _ in range(25):
        floors = 1 + rng.below(4)
        cases.append((tuple(rng.below(6) for _ in range(floors)), 1 + rng.below(3), 1 + rng.below(3), "networkx"))
    cases += [((4, 3), 2, 2, "linprog"), ((0, 5, 2), 1, 2, "linprog"), ((6,), 3, 1, "linprog"), ((2, 2, 2, 2), 2, 2, "linprog")]
    for able, stairs, walk, solver in cases:
        t = A.stairs_time(able, stairs, walk)
        assert stairs_feasible(able, stairs, walk, t, solver), (able, stairs, walk, solver)
        if t > 0:
            assert not stairs_feasible(able, stairs, walk, t - 1, solver), (able, stairs, walk, solver)


# ------------------------------------------------------------------ Orakel Aufzug

def enum_lift_min(n, cabins, capacity, halt, lift_time=1):
    """Vollaufzählung aller Fahrtenpläne: jede Fahrt lädt einen Vektor mit Summe <= capacity; sie braucht 2*h*lift_time + Halte*halt bis zur Ankunft,
    danach `halt` zum Entladen; die früheste freie Kabine fährt als Nächste. Rückgabe: kleinste letzte Ankunft."""
    floors = len(n)

    @lru_cache(maxsize=None)
    def best(rem, frees):
        if sum(rem) == 0:
            return 0
        result = None
        start = frees[0]
        for load in itertools.product(*[range(0, min(rem[i], capacity) + 1) for i in range(floors)]):
            if not 1 <= sum(load) <= capacity:
                continue
            high = max(i + 1 for i, x in enumerate(load) if x)
            stops = sum(1 for x in load if x)
            arrive = start + 2 * high * lift_time + stops * halt
            value = max(arrive, best(tuple(r - x for r, x in zip(rem, load)), tuple(sorted(frees[1:] + (arrive + halt,)))))
            result = value if result is None else min(result, value)
        return result

    return best(tuple(n), (0,) * cabins)


def test_lift_dp_equals_full_enumeration():
    rng = SplitMix64(5)
    checked = 0
    for _ in range(60):
        floors = 2 + rng.below(2)
        n = tuple(rng.below(4) for _ in range(floors))
        capacity, halt, cabins = 1 + rng.below(4), 1 + rng.below(2), 1 + rng.below(2)
        if sum(n) == 0 or sum(n) > 8:
            continue
        assert A.Lift(A.Params(cabins, capacity, halt, 2)).time(n) == enum_lift_min(n, cabins, capacity, halt), (n, cabins, capacity, halt)
        checked += 1
    assert checked >= 30


def test_lift_dp_equals_enumeration_with_longer_floor_time():
    for n, cabins, capacity, halt in [((2, 1), 1, 2, 1), ((1, 2, 1), 2, 3, 1), ((2, 0, 2), 1, 4, 2)]:
        p = A.Params(cabins, capacity, halt, 2, lift_time=2)
        assert A.Lift(p).time(n) == enum_lift_min(n, cabins, capacity, halt, lift_time=2), n


# ------------------------------------------------------------------ Orakel gemeinsames Modell

def brute_joint(mandatory, free, p):
    floors = len(mandatory)
    best = None
    for a in itertools.product(*[range(free[i] + 1) for i in range(floors)]):
        stairs_t = nx_stairs_time(tuple(free[i] - a[i] for i in range(floors)), p.stairs, p.walk)
        lift_t = enum_lift_min(tuple(mandatory[i] + a[i] for i in range(floors)), p.cabins, p.capacity, p.halt, p.lift_time)
        t = max(stairs_t, lift_t)
        best = t if best is None else min(best, t)
    return best


def tiny(rng, floors, pmax):
    m = [1 + rng.below(pmax) for _ in range(floors)]
    mandatory = tuple(rng.below(min(m[i], 2) + 1) for i in range(floors))
    return mandatory, tuple(m[i] - mandatory[i] for i in range(floors))


def test_joint_exact_equals_full_enumeration_of_splits_and_plans():
    rng = SplitMix64(77)
    helped = 0
    for _ in range(14):
        mandatory, free = tiny(rng, 2, 3)
        p = A.Params(1 + rng.below(2), 1 + rng.below(3), 1, 2)
        j = A.joint_exact(mandatory, free, p)
        assert j.time == brute_joint(mandatory, free, p), (mandatory, free, p)
        assert j.time <= j.time_stairs_only and j.a_min <= j.a_max and j.n_optimal >= 1
        helped += j.time < j.time_stairs_only
    # Zweigtest: die freie Wahl hilft auf einer festen Instanz wirklich (T = 5 statt 6 mit zwei Kabinen)
    p = A.Params(2, 3, 1, 2)
    j = A.joint_exact((1, 0), (2, 6), p)
    assert (j.time, j.time_stairs_only) == (5, 6) and j.a_min >= 1
    assert brute_joint((1, 0), (2, 6), p) == 5


def test_joint_exact_equals_cpsat_feasibility():
    pytest.importorskip("ortools")
    import evk_cpsat as CS
    rng = SplitMix64(123)
    for _ in range(6):
        mandatory, free = tiny(rng, 2, 3)
        p = A.Params(1 + rng.below(2), 2 + rng.below(2), 1, 2)
        t = A.joint_exact(mandatory, free, p).time
        yes, _ = CS.feasible(mandatory, free, p, t, workers=4)
        no, _ = CS.feasible(mandatory, free, p, t - 1, workers=4) if t > 0 else ("nein", None)
        assert yes == "ja" and no == "nein", (mandatory, free, p, t)


def test_waiting_area_unlimited_equals_exact_and_the_effect_is_monotone():
    pytest.importorskip("ortools")
    import evk_cpsat as CS
    p = A.Params(1, 3, 1, 2)
    mandatory, free = (3, 0), (1, 2)
    t = A.joint_exact(mandatory, free, p).time
    times = {w: CS.min_time(mandatory, free, p, lo=t, places=w, q=2, workers=4)[0] for w in (None, 2, 1, 0)}
    assert times[None] == t                                    # unbegrenzter Wartebereich = exaktes Modell
    assert times[None] <= times[2] <= times[1] <= times[0]      # weniger Plätze, mehr Rückstau
    assert (times[None], times[2], times[0]) == (4, 4, 5)       # Zweigtest: der Rückstau wirkt auf dieser Instanz (4 gegen 5 Zeitschritte)


# ------------------------------------------------------------------ Orakel Fluss

def test_core_max_flow_equals_networkx_on_the_flow_network():
    rng = SplitMix64(9)
    for _ in range(12):
        floors = 2 + rng.below(2)
        mandatory, free = tiny(rng, floors, 4)
        p = A.Params(1 + rng.below(2), 1 + rng.below(4), 1 + rng.below(2), 2 + rng.below(2))
        for mode in ("takt", "rate"):
            for horizon in (4, 7, 11):
                n_nodes, edges, s, t = A.flow_network(mandatory, free, p, horizon, mode)
                g = nx.DiGraph()
                for u, v, c in edges:
                    g.add_edge(u, v, capacity=c)
                expected = nx.maximum_flow_value(g, s, t) if s in g and t in g else 0
                assert A.max_flow_value(n_nodes, edges, s, t) == expected


def test_flow_is_a_lower_bound_and_barrier_too_and_the_plan_is_feasible():
    rng = SplitMix64(2026)
    flow_below = 0
    for _ in range(25):
        floors = 2 + rng.below(2)
        mandatory, free = tiny(rng, floors, 4)
        p = A.Params(1 + rng.below(2), 1 + rng.below(4), 1 + rng.below(2), 2 + rng.below(2))
        j = A.joint_exact(mandatory, free, p)
        flow = A.flow_time(mandatory, free, p, "takt", hint=j.time + 1)
        barrier = A.barrier_time(mandatory, p)
        assert flow <= max(flow, barrier) <= j.time <= j.time_stairs_only, (mandatory, free, p)
        riders = tuple(m + a for m, a in zip(mandatory, j.split))
        problems, plan_time = A.evaluate_plan(mandatory, free, j.split, [list(c) for c in A.Lift(p).plan(riders)], p)
        assert problems == [] and plan_time == j.time
        flow_below += flow < j.time
    assert flow_below >= 1            # Zweigtest: der Fluss liegt auf manchen Instanzen wirklich unter dem exakten Wert
