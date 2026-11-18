"""Kern der Demo (numpy, scipy, Standardbibliothek): Treppe, Aufzug, gemeinsames exaktes Modell, Flussmodell, Maschinenschranke, Prüfer.

Alle Zahlen sind ganzzahlig (Zeitschritte, Personen, Fahrten); es gibt keine Gleitkommarechnung und keine Zufallszahl im Kern.
Alle Parameter sind ANNAHMEN eines Mini-Gebäudes, keine realen Gebäude und keine Brandschutzvorgaben.

Modell (Etagen 1..F über dem Ausgang, alle Personen zum Zeitschritt 0 auf ihrer Etage bereit):
  Treppe  : je Flucht (Etage f nach f - 1) bis zu `stairs` Personen je Zeitschritt (alle Treppenhäuser zusammen), `walk` Zeitschritte je Flucht,
            Staus dort, wo sie auftreten. Räumungszeit der Treppengruppe = Zeitschritt, in dem die letzte Person den Ausgang erreicht.
  Aufzug  : `cabins` Kabinen (1 oder 2) starten am Ausgang; eine Fahrt nimmt höchstens `capacity` Personen und darf an beliebig vielen Etagen
            halten (Mehrfachhalt). Dauer einer Fahrt mit höchster Etage h und s Halten: 2·h·lift_time + s·halt + halt (hoch, Halte, runter,
            Entladen). Die letzte Ankunft am Ausgang ist die größte Summe der Fahrtdauern je Kabine minus `halt` (unabhängig von der Reihenfolge).
  Wahl    : Menschen mit Aufzugspflicht nutzen nur den Aufzug; von den übrigen nehmen a_f je Etage den Aufzug, der Rest die Treppe. Die Aufteilung
            ist Teil der Entscheidung (ein Plan mit vollständiger Kenntnis, kein Verhalten).
  Ziel    : T* = kleinste Räumungszeit über alle Aufteilungen und Fahrtenpläne; Gesamtzeit = Maximum von Treppen- und Aufzugsgruppe.
"""

import itertools
from dataclasses import dataclass
from functools import lru_cache

import numpy as np
from scipy.sparse import csr_array
from scipy.sparse.csgraph import maximum_flow

import evk_constants as C

BIG = 10 ** 6


@dataclass(frozen=True)
class Params:
    """Annahmen des Gebäudes (Zeitschritte und Personen)."""
    cabins: int = C.DEFAULT_CABINS
    capacity: int = C.DEFAULT_CAPACITY
    halt: int = C.DEFAULT_HALT
    stairs: int = C.DEFAULT_STAIRS
    walk: int = C.WALK_TIME
    lift_time: int = C.LIFT_TIME


# ---------------------------------------------------------------- Treppe

@lru_cache(maxsize=None)
def stairs_exits(able: tuple[int, ...], stairs: int, walk: int) -> tuple[tuple[int, int], ...]:
    """Ankünfte am Ausgang der Treppengruppe als ((Zeitschritt, Personen), ...) aufsteigend; `able` = Personen je Etage 1..F.
    Je Flucht und Zeitschritt gehen bis zu `stairs` Personen, Staus entstehen dort, wo sie auftreten (arbeitserhaltend)."""
    floors = len(able)
    total = sum(able)
    exits: dict[int, int] = {}
    if total == 0:
        return ()
    queue = list(able)
    arrivals: dict[int, list[tuple[int, int]]] = {}
    out, t = 0, 0
    while out < total:
        for f, c in arrivals.pop(t, ()):
            queue[f] += c
        for f in range(floors):
            if queue[f]:
                dep = min(queue[f], stairs)
                queue[f] -= dep
                if f == 0:
                    out += dep
                    exits[t + walk] = exits.get(t + walk, 0) + dep
                else:
                    arrivals.setdefault(t + walk, []).append((f - 1, dep))
        t += 1
    return tuple(sorted(exits.items()))


def stairs_time(able: tuple[int, ...], stairs: int, walk: int) -> int:
    """Räumungszeit der Treppengruppe (0 ohne Personen)."""
    exits = stairs_exits(tuple(able), stairs, walk)
    return exits[-1][0] if exits else 0


# ---------------------------------------------------------------- Aufzug: exakter Pareto-DP über Fahrtenmengen

def trip_duration(load: tuple[int, ...], halt: int, lift_time: int) -> int:
    """Dauer, die eine Fahrt die Kabine belegt: hoch bis zur höchsten Etage mit Personen, Halt an jeder Etage mit Personen, runter, Entladen."""
    highest = max(i + 1 for i, x in enumerate(load) if x)
    stops = sum(1 for x in load if x)
    return 2 * highest * lift_time + stops * halt + halt


@dataclass(frozen=True)
class Trip:
    load: tuple[int, ...]   # Personen je Etage
    start: int              # Zeitschritt, in dem die Kabine am Ausgang startet
    arrival: int            # Zeitschritt, in dem sie am Ausgang ankommt (die Ankunft zählt zu Beginn des Entladens)
    end: int                # Zeitschritt, in dem die Kabine wieder frei ist (nach dem Entladen)


class Lift:
    """Räumungszeit der Aufzugsgruppe exakt für 1 und 2 Kabinen: kleinste letzte Ankunft am Ausgang bei beliebig vielen Halten je Fahrt.

    Zustand = verbleibende Personen je Etage; Wert = Pareto-Menge der (sortierten) Belegungszeiten der Kabinen. Eine Fahrt ist ein Auftrag, dessen Dauer
    von seiner Zusammensetzung abhängt (Kapazität, höchste Etage, Zahl der Halte): Bündeln plus Maschinenbelegung."""

    def __init__(self, params: Params):
        assert params.cabins in (1, 2), "exakt nur für 1 und 2 Kabinen"
        self.p = params
        self.memo: dict[tuple[int, ...], list[tuple[int, ...]]] = {}

    def busy(self, load) -> int:
        return trip_duration(load, self.p.halt, self.p.lift_time)

    def _loads(self, rem):
        """Alle Zusammensetzungen einer Fahrt; sie nimmt mindestens eine Person der untersten Etage mit Wartenden (Symmetriebruch: jede Menge von Fahrten
        lässt sich so ordnen)."""
        f0 = next(i for i, x in enumerate(rem) if x)
        cap = self.p.capacity
        ranges = [range(1, min(rem[i], cap) + 1) if i == f0 else range(0, min(rem[i], cap) + 1) for i in range(len(rem))]
        for load in itertools.product(*ranges):
            if sum(load) <= cap:
                yield load

    @staticmethod
    def _prune(cands):
        keep: list[tuple[int, ...]] = []
        for c in sorted(set(cands)):
            if not any(all(k[i] <= c[i] for i in range(len(c))) for k in keep):
                keep.append(c)
        return keep

    def frontier(self, rem: tuple[int, ...]) -> list[tuple[int, ...]]:
        rem = tuple(rem)
        if sum(rem) == 0:
            return [(0,) * self.p.cabins]
        cached = self.memo.get(rem)
        if cached is not None:
            return cached
        cands = []
        for load in self._loads(rem):
            b = self.busy(load)
            for t in self.frontier(tuple(x - y for x, y in zip(rem, load))):
                for i in range(self.p.cabins):
                    if i and t[i] == t[i - 1]:
                        continue
                    nt = list(t)
                    nt[i] += b
                    cands.append(tuple(sorted(nt)))
        result = self._prune(cands)
        self.memo[rem] = result
        return result

    def time(self, persons) -> int:
        """Räumungszeit der Aufzugsgruppe (0 ohne Personen)."""
        persons = tuple(persons)
        if sum(persons) == 0:
            return 0
        return min(max(t) for t in self.frontier(persons)) - self.p.halt

    def _trace(self, rem, target):
        """Fahrten je Kabine (ausgerichtet an der aufsteigend sortierten Zielbelegung `target`)."""
        if sum(rem) == 0:
            return [[] for _ in range(self.p.cabins)]
        for load in self._loads(rem):
            b = self.busy(load)
            rest = tuple(x - y for x, y in zip(rem, load))
            for t in self.frontier(rest):
                for i in range(self.p.cabins):
                    if i and t[i] == t[i - 1]:
                        continue
                    nt = list(t)
                    nt[i] += b
                    if tuple(sorted(nt)) == target:
                        seqs = self._trace(rest, t)
                        seqs[i] = seqs[i] + [load]
                        order = sorted(range(self.p.cabins), key=lambda j: sum(self.busy(x) for x in seqs[j]))
                        return [seqs[j] for j in order]
        raise AssertionError("Wiederherstellung der Fahrten gescheitert")  # pragma: no cover

    def plan(self, persons) -> list[list[Trip]]:
        """Ein optimaler Fahrtenplan: je Kabine die Fahrten nacheinander (die Reihenfolge ändert die letzte Ankunft nicht)."""
        persons = tuple(persons)
        if sum(persons) == 0:
            return [[] for _ in range(self.p.cabins)]
        target = min(self.frontier(persons), key=lambda t: (max(t), t))
        cabins = []
        for loads in self._trace(persons, target):
            trips, clock = [], 0
            for load in sorted(loads, key=lambda x: (-max(i for i, v in enumerate(x) if v), x)):
                b = self.busy(load)
                trips.append(Trip(load, clock, clock + b - self.p.halt, clock + b))
                clock += b
            cabins.append(trips)
        return cabins


@lru_cache(maxsize=None)
def lift_for(params: Params) -> Lift:
    """Ein Aufzug je Annahmensatz, damit der Speicher der Pareto-Mengen zwischen den Aufrufen erhalten bleibt."""
    return Lift(params)


# ---------------------------------------------------------------- Gemeinsames exaktes Modell

@dataclass(frozen=True)
class Joint:
    time: int                 # T*: kleinste Räumungszeit über alle Aufteilungen
    a_min: int                # kleinste Zahl freiwilliger Aufzugsnutzer in einer optimalen Aufteilung
    a_max: int                # größte
    time_stairs_only: int     # Räumungszeit, wenn alle Gehenden die Treppe nehmen (Pflichtgruppe im Aufzug)
    n_optimal: int            # Zahl der optimalen Aufteilungen
    split: tuple[int, ...]    # eine optimale Aufteilung mit a_min Freiwilligen (erste in der Aufzählung)


def joint_exact(mandatory, free, params: Params, lift: Lift | None = None) -> Joint:
    """Aufzählung aller Aufteilungen der Gehenden (a_f von 0 bis free_f je Etage), je Aufteilung Treppenzeit und exakte Aufzugszeit; T* = Minimum
    des Maximums. Der Speicher der Aufzugs-DP wird zwischen den Aufteilungen geteilt."""
    mandatory, free = tuple(mandatory), tuple(free)
    lift = lift or lift_for(params)
    floors = len(mandatory)
    t_sep = max(stairs_time(free, params.stairs, params.walk), lift.time(mandatory))
    best, a_min, a_max, count, split = None, 0, 0, 0, (0,) * floors
    for a in itertools.product(*[range(free[i] + 1) for i in range(floors)]):
        ts = stairs_time(tuple(free[i] - a[i] for i in range(floors)), params.stairs, params.walk)
        if best is not None and ts > best:
            continue
        t = max(ts, lift.time(tuple(mandatory[i] + a[i] for i in range(floors))))
        s = sum(a)
        if best is None or t < best:
            best, a_min, a_max, count, split = t, s, s, 1, a
        elif t == best:
            count += 1
            a_max = max(a_max, s)
            if s < a_min:
                a_min, split = s, a
    return Joint(best, a_min, a_max, t_sep, count, split)


# ---------------------------------------------------------------- Prüfer

def evaluate_plan(mandatory, free, split, cabins: list[list[Trip]], params: Params) -> tuple[list[str], int]:
    """Unabhängiger Zulässigkeitsprüfer: (Verstöße, Räumungszeit des Plans). Ohne Verstöße ist der Plan zulässig und die Zeit die des Plans."""
    problems: list[str] = []
    floors = len(mandatory)
    if len(split) != floors or any(not 0 <= split[i] <= free[i] for i in range(floors)):
        problems.append("Aufteilung außerhalb von 0 bis zur Zahl der Gehenden je Etage")
        return problems, -1
    if len(cabins) > params.cabins:
        problems.append("mehr Kabinen als vorhanden")
    carried = [0] * floors
    lift_last = 0
    for k, trips in enumerate(cabins):
        clock = 0
        for trip in trips:
            if len(trip.load) != floors or sum(trip.load) == 0 or min(trip.load) < 0:
                problems.append(f"Kabine {k}: leere oder fehlerhafte Fahrt")
                continue
            if sum(trip.load) > params.capacity:
                problems.append(f"Kabine {k}: Fahrt über der Kapazität")
            for i, x in enumerate(trip.load):
                carried[i] += x
            dur = trip_duration(trip.load, params.halt, params.lift_time)
            if trip.start < clock:
                problems.append(f"Kabine {k}: Fahrt startet vor dem Ende der vorigen")
            if trip.end - trip.start != dur or trip.arrival != trip.end - params.halt:
                problems.append(f"Kabine {k}: Dauer der Fahrt stimmt nicht")
            clock = trip.end
            lift_last = max(lift_last, trip.arrival)
    want = [mandatory[i] + split[i] for i in range(floors)]
    if carried != want:
        problems.append("nicht jede Person mit Aufzug genau einmal befördert")
    t_stairs = stairs_time(tuple(free[i] - split[i] for i in range(floors)), params.stairs, params.walk)
    return problems, max(lift_last, t_stairs)


# ---------------------------------------------------------------- Reines Flussmodell (Zeitnetz, Treppe und Aufzug als Kanten)

def flow_network(mandatory, free, params: Params, horizon: int, mode: str = "takt"):
    """Ein Zeitnetz für beide Wege; Knoten: Quelle 0, Senke 1, Etagenknoten für Pflicht und Gehende, Treppenknoten und Aufzugsknoten (Etage, Zeit).
    Aufzug 'takt': Kapazität Kabinen·Kapazität nur zu den Abfahrtszeiten (jede Etage hat alle Kabinen für sich); 'rate': gerundeter Durchsatz je Zeitschritt.
    Personen mit Aufzugspflicht erreichen nur die Aufzugskanten."""
    p, floors = params, len(mandatory)
    base = 2 + 2 * floors
    stair = lambda f, t: base + (f - 1) * (horizon + 1) + t
    lbase = base + floors * (horizon + 1)
    lift = lambda f, t: lbase + (f - 1) * (horizon + 1) + t
    edges = []
    for f in range(1, floors + 1):
        pflicht_node, frei_node = 2 + (f - 1), 2 + floors + (f - 1)
        if mandatory[f - 1]:
            edges.append((0, pflicht_node, mandatory[f - 1]))
            edges.append((pflicht_node, lift(f, 0), BIG))
        if free[f - 1]:
            edges.append((0, frei_node, free[f - 1]))
            edges.append((frei_node, lift(f, 0), BIG))
            edges.append((frei_node, stair(f, 0), BIG))
        for t in range(horizon):
            edges.append((stair(f, t), stair(f, t + 1), BIG))
            edges.append((lift(f, t), lift(f, t + 1), BIG))
        for t in range(horizon - p.walk + 1):
            edges.append((stair(f, t), 1 if f == 1 else stair(f - 1, t + p.walk), p.stairs))
        period = 2 * f * p.lift_time + 2 * p.halt
        first = f * p.lift_time + p.halt
        if mode == "takt":
            j = 0
            while first + j * period + f * p.lift_time <= horizon:
                edges.append((lift(f, first + j * period), 1, p.cabins * p.capacity))
                j += 1
        else:
            s = 0
            while first + s + f * p.lift_time <= horizon:
                c = ((s + 1) * p.cabins * p.capacity) // period - (s * p.cabins * p.capacity) // period
                if c > 0:
                    edges.append((lift(f, first + s), 1, c))
                s += 1
    return lbase + floors * (horizon + 1), edges, 0, 1


def max_flow_value(n_nodes: int, edges, source: int, sink: int) -> int:
    if not edges:
        return 0
    us = np.array([e[0] for e in edges], dtype=np.int32)
    vs = np.array([e[1] for e in edges], dtype=np.int32)
    cs = np.array([e[2] for e in edges], dtype=np.int32)
    graph = csr_array((cs, (us, vs)), shape=(n_nodes, n_nodes))
    return int(maximum_flow(graph, source, sink, method="dinic").flow_value)


def flow_time(mandatory, free, params: Params, mode: str = "takt", hint: int | None = None) -> int:
    """Kleinste Zeit T, in der der Maximalfluss im Zeitnetz alle Personen hinausbringt (monoton in T, Binärsuche). `hint` = obere Schranke, falls bekannt."""
    total = sum(mandatory) + sum(free)
    if total == 0:
        return 0
    hi = max(hint or 8, 1)
    while True:
        n_nodes, edges, s, t = flow_network(mandatory, free, params, hi, mode)
        if max_flow_value(n_nodes, edges, s, t) == total:
            break
        hi *= 2
    lo = 0
    while lo < hi:
        mid = (lo + hi) // 2
        n_nodes, edges, s, t = flow_network(mandatory, free, params, mid, mode)
        if max_flow_value(n_nodes, edges, s, t) == total:
            hi = mid
        else:
            lo = mid + 1
    return lo


# ---------------------------------------------------------------- Maschinenschranke und Einzelhalt-Fassungen

def barrier_time(mandatory, params: Params, lift: Lift | None = None) -> int:
    """Maschinenschranke: Räumungszeit der Pflichtgruppe allein im Aufzug (exakt, Mehrfachhalt). Eine untere Schranke für T*: die Pflichtgruppe hat keine andere Wahl."""
    return (lift or lift_for(params)).time(tuple(mandatory))


def _single_stop_durations(persons, params: Params) -> list[tuple[int, int]]:
    """(Etage, Dauer) je Einzelhaltfahrt: jede Fahrt hält an genau einer Etage; Dauer 2·f·lift_time + 2·halt."""
    return [(f, 2 * f * params.lift_time + 2 * params.halt)
            for f in range(1, len(persons) + 1) for _ in range(-(-persons[f - 1] // params.capacity))]


def single_stop_time(persons, params: Params, rule: str = "exact") -> int:
    """Aufzugszeit der Gruppe im Einzelhalt-Modell: `exact` (kleinste Belegung, 1 oder 2 Kabinen) oder `lpt` (höchste Etage zuerst, freie Kabine zuerst)."""
    trips = _single_stop_durations(tuple(persons), params)
    if not trips:
        return 0
    if rule == "lpt":
        free_at = [0] * params.cabins
        last = 0
        for _, r in sorted(trips, key=lambda x: -x[0]):
            i = min(range(params.cabins), key=lambda j: (free_at[j], j))
            last = max(last, free_at[i] + r - params.halt)
            free_at[i] += r
        return last
    durations = [r for _, r in trips]
    total = sum(durations)
    if params.cabins == 1:
        return total - params.halt
    reach = 1
    for r in durations:
        reach |= reach << r
    s = -(-total // 2)
    while not (reach >> s) & 1:
        s += 1
    return s - params.halt


# ---------------------------------------------------------------- Messzeile (alles, was die Messreihen je Gebäude und Anteil festhalten)

COLUMNS = ("exact", "a_min", "a_max", "stairs_only", "n_optimal", "barrier", "stairs_all_free", "flow_takt", "flow_rate", "k1", "k1_lpt", "k1_single")


def measure(mandatory, free, params: Params) -> tuple[int, ...]:
    """Eine Zeile der Messreihe in der Reihenfolge von COLUMNS."""
    lift = lift_for(params)
    joint = joint_exact(mandatory, free, params, lift)
    flow = flow_time(mandatory, free, params, "takt", hint=joint.time + 1)
    rate = flow_time(mandatory, free, params, "rate", hint=joint.time + 1)
    barrier = lift.time(tuple(mandatory))
    return (joint.time, joint.a_min, joint.a_max, joint.time_stairs_only, joint.n_optimal, barrier,
            stairs_time(tuple(free), params.stairs, params.walk), flow, rate, max(flow, barrier),
            max(flow, single_stop_time(mandatory, params, "lpt")), max(flow, single_stop_time(mandatory, params, "exact")))
