"""Szenario: Mini-Gebäude mit Personen je Etage und je Person einer gekoppelten Zufallszahl (nur SplitMix64, ganzzahlig).

Menschen mit Aufzugspflicht (dürfen nur den Aufzug nehmen): Person i hat Aufzugspflicht, wenn ihre Zufallszahl kleiner ist als
Anteil_in_Prozent * 10 000 (Zufallszahlen 0 bis 999 999). Die Mengen sind in dem Anteil geschachtelt: wer bei 10 % Aufzugspflicht hat, hat sie auch bei 20 %."""

from dataclasses import dataclass

import evk_constants as C
from evk_rng import SplitMix64


@dataclass(frozen=True)
class Building:
    seed: int
    persons: tuple[int, ...]            # Personen je Etage 1..F
    draws: tuple[tuple[int, ...], ...]  # je Etage eine Zufallszahl 0..999999 je Person

    @property
    def floors(self) -> int:
        return len(self.persons)

    @property
    def total(self) -> int:
        return sum(self.persons)

    def split(self, share_percent: int) -> tuple[tuple[int, ...], tuple[int, ...]]:
        """(Personen mit Aufzugspflicht je Etage, übrige Personen je Etage) bei diesem Anteil in Prozent."""
        bound = int(share_percent) * 10_000
        mandatory = tuple(sum(1 for x in row if x < bound) for row in self.draws)
        free = tuple(m - n for m, n in zip(self.persons, mandatory))
        return mandatory, free


def make_building(seed: int, floors: int, pmin: int = C.PERSONS_MIN, pmax: int = C.PERSONS_MAX) -> Building:
    """Deterministisch aus (seed, floors): Personen je Etage gleichverteilt pmin..pmax, je Person eine Zufallszahl."""
    rng = SplitMix64(int(seed) * 1_000_003 + int(floors) * 7_919 + 20_261_118)
    persons = tuple(pmin + rng.below(pmax - pmin + 1) for _ in range(floors))
    draws = tuple(tuple(rng.below(1_000_000) for _ in range(m)) for m in persons)
    return Building(int(seed), persons, draws)
