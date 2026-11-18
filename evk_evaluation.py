"""Kennzahlen einer Einstellung, Räumungskurve und Verdikte (reine Funktionen `verdict_*`: Art, Text).

Zähleinheiten: Zeitschritte, Personen, Fahrten. Fehler des Flusses = T* minus Flusswert (positiv: der Fluss unterschätzt die Räumungszeit)."""

from dataclasses import dataclass

import evk_algorithm as A
import evk_constants as C
import evk_scenario as S


def de(x: float, digits: int = 1) -> str:
    """Zahl mit Dezimalkomma (Anzeigetexte sind deutsch)."""
    return f"{x:.{digits}f}".replace(".", ",")


def steps(n: int) -> str:
    return f"{n} Zeitschritt" if n == 1 else f"{n} Zeitschritte"


@dataclass(frozen=True)
class Settings:
    floors: int = C.DEFAULT_FLOORS
    cabins: int = C.DEFAULT_CABINS
    capacity: int = C.DEFAULT_CAPACITY
    halt: int = C.DEFAULT_HALT
    stairs: int = C.DEFAULT_STAIRS
    share: int = C.DEFAULT_SHARE
    seed: int = C.DEFAULT_SEED

    @property
    def params(self) -> A.Params:
        return A.Params(self.cabins, self.capacity, self.halt, self.stairs)

    @property
    def cell(self) -> tuple[int, int, int, int, int]:
        """Zelle der vorgerechneten Messreihe: (Etagen, Kabinen, Kapazität, Treppe, Halt)."""
        return (self.floors, self.cabins, self.capacity, self.stairs, self.halt)


@dataclass(frozen=True)
class Analysis:
    settings: Settings
    building: S.Building
    mandatory: tuple[int, ...]
    free: tuple[int, ...]
    joint: A.Joint
    flow_takt: int
    flow_rate: int
    barrier: int                      # Aufzugszeit der Pflichtgruppe allein (Maschinenschranke)
    k1: int                           # Fluss plus Maschinenschranke
    single_exact: int                 # Einzelhalt-Fassung der Schranke (exakt), mit dem Fluss maximiert
    single_lpt: int
    cabins_plan: tuple[tuple[A.Trip, ...], ...]   # Fahrten je Kabine eines optimalen Plans (mit der Aufteilung joint.split)
    stairs_exits: tuple[tuple[int, int], ...]     # Ankünfte der Treppengruppe im Plan

    @property
    def exact(self) -> int:
        return self.joint.time

    @property
    def gap(self) -> int:
        """Fehler des Flusses (Takt): T* minus Flusswert, nie negativ (der Takt-Fluss ist eine untere Schranke)."""
        return self.joint.time - self.flow_takt

    @property
    def rule_holds(self) -> bool:
        """Faustregel R: die Pflichtgruppe braucht im Aufzug allein höchstens so lange wie der Flusswert."""
        return self.barrier <= self.flow_takt

    @property
    def n_mandatory(self) -> int:
        return sum(self.mandatory)

    @property
    def n_walkers(self) -> int:
        return sum(self.free)

    @property
    def n_lift(self) -> int:
        return self.n_mandatory + sum(self.joint.split)


def analyse(settings: Settings) -> Analysis:
    building = S.make_building(settings.seed, settings.floors)
    mandatory, free = building.split(settings.share)
    p = settings.params
    lift = A.lift_for(p)
    joint = A.joint_exact(mandatory, free, p, lift)
    flow_takt = A.flow_time(mandatory, free, p, "takt", hint=joint.time + 1)
    flow_rate = A.flow_time(mandatory, free, p, "rate", hint=joint.time + 1)
    barrier = A.barrier_time(mandatory, p, lift)
    riders = tuple(m + a for m, a in zip(mandatory, joint.split))
    cabins = tuple(tuple(c) for c in lift.plan(riders))
    stair_exits = A.stairs_exits(tuple(f - a for f, a in zip(free, joint.split)), p.stairs, p.walk)
    return Analysis(settings, building, mandatory, free, joint, flow_takt, flow_rate, barrier, max(flow_takt, barrier),
                    max(flow_takt, A.single_stop_time(mandatory, p, "exact")), max(flow_takt, A.single_stop_time(mandatory, p, "lpt")), cabins, stair_exits)


def evacuation_curve(a: Analysis) -> dict[str, list[int]]:
    """Menschen draußen je Zeitschritt 0 bis T* (kumuliert): Treppengruppe, Aufzugsgruppe, zusammen."""
    horizon = a.exact
    stairs = [0] * (horizon + 1)
    lift = [0] * (horizon + 1)
    for t, n in a.stairs_exits:
        stairs[t] += n
    for cab in a.cabins_plan:
        for trip in cab:
            lift[trip.arrival] += sum(trip.load)
    out_s, out_l, tot_s, tot_l = [], [], 0, 0
    for t in range(horizon + 1):
        tot_s += stairs[t]
        tot_l += lift[t]
        out_s.append(tot_s)
        out_l.append(tot_l)
    return {"stairs": out_s, "lift": out_l, "total": [x + y for x, y in zip(out_s, out_l)]}


# ---------------------------------------------------------------- Verdikte (reine Funktionen: Art, Text)

def verdict_flow_error(exact: int, flow: int) -> tuple[str, str]:
    """Kernfrage 1: trifft der Fluss die exakte Räumungszeit? `flow` ist der Takt-Fluss und nie größer als `exact`."""
    if flow > exact:
        raise ValueError("der Takt-Fluss ist eine untere Schranke und kann T* nicht übersteigen")
    gap = exact - flow
    if gap == 0:
        return "success", f"Der Fluss trifft hier die exakte Räumungszeit: beide {steps(exact)}."
    share = 100 * gap / exact
    if gap == 1:
        return "info", f"Der Fluss liegt hier nur {steps(1)} unter der exakten Räumungszeit ({flow} statt {exact}, {de(share, 0)} % von T*)."
    return "warning", (f"Der Fluss unterschätzt die Räumungszeit um **{steps(gap)}**: {flow} statt {exact}, das sind {de(share, 0)} % von T* "
                       "(Der Fluss gibt jeder Etage alle Kabinen für sich; in Wahrheit teilen sich die Etagen die Kabinenzeit.)")


def verdict_rule(holds: bool, barrier: int, flow: int, exact: int, rate_true: tuple[int, int], rate_false: tuple[int, int]) -> tuple[str, str]:
    """Kernfrage 2: Faustregel R (Aufzugszeit der Pflichtgruppe allein höchstens so groß wie der Flusswert).
    rate_true / rate_false = (Zellen mit Fehler des Flusses höchstens 1, Zellen insgesamt) der Messreihe, wenn R wahr beziehungsweise falsch ist."""
    gap = exact - flow
    if barrier == 0:
        return "success", ("Keine Person mit Aufzugspflicht: die Faustregel gilt trivial (0 ≤ Fluss), der Aufzug ist hier kein Zwang. "
                           f"Fluss und exakter Wert unterscheiden sich um {steps(gap)}.")
    if holds:
        if gap <= 1:
            return "success", (f"Die Faustregel gilt: die Pflichtgruppe braucht im Aufzug allein {barrier} ≤ Fluss {flow}, und der Fluss liegt höchstens 1 unter T* "
                               f"({steps(gap)}). In der Messreihe (alle Reglerstufen, Anteil ab 5 %) stimmt das in {rate_true[0]} von {rate_true[1]} Zellen, wenn die Regel gilt.")
        return "warning", (f"Die Faustregel gilt ({barrier} ≤ {flow}), trifft hier aber nicht zu: der Fluss liegt {steps(gap)} unter T*. "
                           f"Ausnahme; in der Messreihe (alle Reglerstufen, Anteil ab 5 %) sind es {rate_true[1] - rate_true[0]} von {rate_true[1]} Zellen.")
    return "warning", (f"Die Faustregel gilt nicht: die Pflichtgruppe braucht allein {barrier} > Fluss {flow}. Der Fluss liegt hier {steps(gap)} unter T*; "
                       f"in der Messreihe (alle Reglerstufen, Anteil ab 5 %) liegt er in dieser Lage nur in {rate_false[0]} von {rate_false[1]} Zellen höchstens 1 unter T*.")


def verdict_volunteers(exact: int, stairs_only: int, a_min: int, a_max: int, walkers: int, barrier: int) -> tuple[str, str]:
    """Kernfrage 3a: was bringt die freie Wahl der Gehenden? stairs_only = Räumungszeit, wenn alle Gehenden die Treppe nehmen; barrier = Aufzugszeit der Pflichtgruppe allein."""
    if exact > stairs_only:
        raise ValueError("die freie Wahl kann nicht schlechter sein als die Treppe für alle Gehenden")
    if exact < stairs_only:
        return "success", (f"Freiwillige helfen: mit freier Wahl {steps(exact)} statt {stairs_only}, wenn alle Gehenden die Treppe nehmen. "
                           f"Mindestens {a_min} von {walkers} Gehenden fahren im Aufzug, höchstens {a_max} dürfen es, ohne dass es schlechter wird.")
    if walkers == 0:
        return "info", "Es gibt keine Gehenden: alle haben Aufzugspflicht, die Wahl entfällt."
    tail = (f"Keine der {walkers} Gehenden darf den Aufzug nehmen, ohne dass es schlechter wird." if a_max == 0
            else f"Bis zu {a_max} von {walkers} Gehenden dürfen den Aufzug nehmen, ohne dass es schlechter wird.")
    return "info", (f"Freiwillige helfen hier nicht: auch mit freier Wahl bleibt es bei T* = {exact}"
                    + (f" (die Pflichtgruppe allein braucht im Aufzug {barrier})" if barrier == exact else "") + f". {tail}")


def verdict_tipping(median: float, tipped: int, seeds: int, cabins: int, other_median: float, other_tipped: int) -> tuple[str, str]:
    """Kernfrage 3b: Kipppunkt (kleinster Anteil, ab dem die Aufzugspflicht die Räumung gegenüber Anteil 0 verlängert; Median über die Zufalls-Seeds).
    `other_*`: dieselbe Zahl für die jeweils andere Kabinenzahl. Median ab 45 heißt: bis 40 % kippt es im Median nicht."""
    def name(m):
        return "über 40 %" if m > 40 else f"bei {de(m, 1 if m % 1 else 0)} %"
    other_cabins = 2 if cabins == 1 else 1
    base = (f"Mit {cabins} Kabine{'n' if cabins > 1 else ''} kippt die Räumung im Median {name(median)} Aufzugspflicht ({tipped} von {seeds} Zufalls-Seeds kippen bis 40 %); "
            f"mit {other_cabins} Kabine{'n' if other_cabins > 1 else ''} {name(other_median)} ({other_tipped} von {seeds}).")
    return ("warning" if median <= 20 else "info"), base


def verdict_waiting(effect: float, affected: int, seeds: int, second_cabin_gain: float, places: int) -> tuple[str, str]:
    """Kernfrage 4: Wartebereich (vorgerechnet). effect = mittlere Verlängerung gegen unbegrenzte Plätze; second_cabin_gain = mittlere Verkürzung durch die zweite Kabine."""
    if places < 0:
        return "info", "Unbegrenzter Wartebereich: kein Rückstau, das ist das Verfahren der App (Wirkung 0)."
    noun = "1 Warteplatz" if places == 1 else f"{places} Warteplätzen"
    text = (f"Mit {noun} je Etage verlängert sich die Räumung im Mittel um {de(effect, 2)} Zeitschritte ({affected} von {seeds} Zufalls-Seeds betroffen); "
            f"die zweite Kabine verkürzt sie bei gleichem Anteil um {de(second_cabin_gain, 2)}.")
    return ("success" if effect <= 0.5 else "info"), text
