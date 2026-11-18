"""Vorgerechnete Messreihe (data/evk_results.json, erzeugt von tools/sweep_evakuierung.py) und ihre Auswertung.

Je Zelle (Etagen F, Kabinen E, Kapazität K, Treppe C, Halt d) 30 feste Zufalls-Seeds x 9 Anteile (0 bis 40 % in 5-%-Schritten) = 270 Zeilen, alles ganzzahlig.
Fehler eines Verfahrens = T* minus Wert des Verfahrens in Zeitschritten (positiv: das Verfahren unterschätzt die exakte Räumungszeit)."""

import json
import os
from functools import lru_cache

import numpy as np

import evk_constants as C

ROOT = os.path.dirname(os.path.abspath(__file__))
SEEDS = len(C.SWEEP_SEEDS)
SHARES = len(C.SHARES)
NEVER = 45          # „bis 40 % nie“ zählt im Median als 45 (Zeichen der Obergrenze der Messreihe)


@lru_cache(maxsize=1)
def load() -> dict:
    with open(os.path.join(ROOT, C.RESULTS_FILE), encoding="utf-8") as fh:
        return json.load(fh)


@lru_cache(maxsize=1)
def columns() -> dict[str, int]:
    return {name: i for i, name in enumerate(load()["meta"]["columns"])}


def cell_key(floors: int, cabins: int, capacity: int, stairs: int, halt: int) -> str:
    return f"{floors},{cabins},{capacity},{stairs},{halt}"


@lru_cache(maxsize=None)
def cell(floors: int, cabins: int, capacity: int, stairs: int, halt: int) -> np.ndarray:
    """Array (Seed, Anteil, Spalte) der Zelle; Spaltennamen in columns()."""
    rows = load()["data"][cell_key(floors, cabins, capacity, stairs, halt)]
    return np.array(rows, dtype=np.int64).reshape(SEEDS, SHARES, -1)


def col(cfg: tuple, name: str) -> np.ndarray:
    """Spalte `name` der Zelle als Array (Seed, Anteil)."""
    return cell(*cfg)[:, :, columns()[name]]


def all_cells() -> list[tuple]:
    return [tuple(int(x) for x in key.split(",")) for key in sorted(load()["data"])]


def error_by_share(cfg: tuple, method: str = "flow_takt") -> np.ndarray:
    """Mittlerer Fehler (T* minus Verfahren) je Anteil, Mittel über die 30 Zufalls-Seeds (Array der Länge 9)."""
    return (col(cfg, "exact") - col(cfg, method)).mean(axis=0)


def mean_by_share(cfg: tuple, name: str) -> np.ndarray:
    return col(cfg, name).mean(axis=0)


def pooled_error(cfgs: list[tuple], method: str, min_share_index: int = 1) -> float:
    """Mittlerer Fehler über alle Seeds und alle Anteile ab min_share_index (1 = ab 5 %) der Zellen."""
    return float(np.mean([(col(c, "exact") - col(c, method))[:, min_share_index:].mean() for c in cfgs]))


def rule_counts(cfgs: list[tuple], min_share_index: int = 1) -> dict[str, int]:
    """Faustregel R: Aufzugszeit der Pflichtgruppe allein <= Flusswert (Takt). Zählt Zellen (Seed x Anteil >= 5 %) je Fall und Fehler des Flusses <= 1."""
    out = {"true": 0, "true_hit": 0, "false": 0, "false_hit": 0, "true_max_error": 0, "false_max_error": 0, "true_exact": 0, "false_exact": 0}
    for c in cfgs:
        err = (col(c, "exact") - col(c, "flow_takt"))[:, min_share_index:]
        rule = (col(c, "barrier") <= col(c, "flow_takt"))[:, min_share_index:]
        for key, mask in (("true", rule), ("false", ~rule)):
            out[key] += int(mask.sum())
            out[key + "_hit"] += int(((err <= 1) & mask).sum())
            out[key + "_exact"] += int(((err == 0) & mask).sum())
            if mask.any():
                out[key + "_max_error"] = max(out[key + "_max_error"], int(err[mask].max()))
    return out


def tipping_points(cfg: tuple, kind: str = "exact") -> list[int]:
    """Kipppunkt je Zufalls-Seed in Prozent (NEVER = bis 40 % nie).
    kind 'exact': kleinster Anteil mit T* größer als bei Anteil 0; 'binding': kleinster Anteil, bei dem die Pflichtgruppe allein länger braucht als alle
    Gehenden auf der Treppe; 'flow': wie 'exact' für das Flussmodell (Takt)."""
    if kind == "exact":
        values = col(cfg, "exact")
        crossed = values > values[:, :1]
    elif kind == "flow":
        values = col(cfg, "flow_takt")
        crossed = values > values[:, :1]
    elif kind == "binding":
        crossed = col(cfg, "barrier") > col(cfg, "stairs_all_free")
    else:
        raise ValueError(kind)
    shares = list(C.SHARES)
    out = []
    for s in range(SEEDS):
        idx = [i for i in range(1, SHARES) if crossed[s, i]]
        out.append(shares[idx[0]] if idx else NEVER)
    return out


def tipping_median(cfg: tuple, kind: str = "exact") -> float:
    return float(np.median(tipping_points(cfg, kind)))


def tipping_count(cfg: tuple, kind: str = "exact") -> int:
    """Zahl der Zufalls-Seeds, die bis 40 % kippen."""
    return sum(1 for x in tipping_points(cfg, kind) if x < NEVER)


def volunteers(cfg: tuple) -> dict[str, np.ndarray]:
    """Freiwillige Aufzugsnutzer je Anteil (Mittel über Seeds): kleinste/größte Zahl in einer optimalen Aufteilung; Zahl der Seeds, in denen die freie
    Wahl strikt hilft (T* kleiner als die Räumungszeit, wenn alle Gehenden die Treppe nehmen)."""
    exact, sep = col(cfg, "exact"), col(cfg, "stairs_only")
    return {"a_min": col(cfg, "a_min").mean(axis=0), "a_max": col(cfg, "a_max").mean(axis=0), "helps": (exact < sep).sum(axis=0),
            "gain": (sep - exact).mean(axis=0), "walkers": col(cfg, "n_free").mean(axis=0)}


# ---------------------------------------------------------------- Wartebereich (vorgerechnet mit CP-SAT, data/evk_wait.json)

@lru_cache(maxsize=1)
def load_wait() -> dict:
    with open(os.path.join(ROOT, C.WAIT_FILE), encoding="utf-8") as fh:
        return json.load(fh)


def wait_rows(cabins: int, share: int, places: int, overflow: int) -> list[list[int]]:
    """Zeilen [Zufalls-Seed, T unbegrenzt, T mit Wartebereich, Freiwillige] der Zelle; places -1 = unbegrenzt."""
    return load_wait()["data"][f"{cabins},{share},{places},{overflow}"]


def wait_effect(cabins: int, share: int, places: int, overflow: int) -> dict:
    """Wirkung = T(Plätze) minus T(unbegrenzt), gepaart über die Zufalls-Seeds: Mittel, Zahl der Seeds mit Wirkung, mittleres T."""
    rows = np.array(wait_rows(cabins, share, places, overflow))
    diff = rows[:, 2] - rows[:, 1]
    return {"mean_effect": float(diff.mean()), "seeds_affected": int((diff > 0).sum()), "seeds": len(rows), "mean_time": float(rows[:, 2].mean()),
            "mean_volunteers": float(rows[:, 3].mean())}


# ---------------------------------------------------------------- Bootstrap-Band über die Zufalls-Seeds (nur Auswertung, nicht die App)

def per_seed_error(cfgs: list[tuple], method: str, min_share_index: int = 1) -> np.ndarray:
    """Fehler (T* minus Verfahren) je Zufalls-Seed, gemittelt über die Zellen und die Anteile ab min_share_index (Array der Länge 30)."""
    return np.mean([(col(c, "exact") - col(c, method))[:, min_share_index:].mean(axis=1) for c in cfgs], axis=0)


def bootstrap_band(per_seed: np.ndarray, draws: int = 2000, seed: int = 2026) -> tuple[float, float]:
    """95-%-Band des Mittels über die Zufalls-Seeds (Perzentile 2,5 und 97,5 von `draws` Ziehungen mit Zurücklegen; Zufall: SplitMix64, ganzzahlig)."""
    from evk_rng import SplitMix64
    rng = SplitMix64(seed)
    n = len(per_seed)
    means = sorted(float(np.mean([per_seed[rng.below(n)] for _ in range(n)])) for _ in range(draws))
    return means[int(0.025 * draws)], means[int(0.975 * draws) - 1]
