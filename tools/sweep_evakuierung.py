"""Messreihe der Demo: alle Reglerstufen (Etagen, Kabinen, Kapazität, Halt, Treppe) x 30 Zufalls-Seeds x Anteil 0 bis 40 %.

Schreibt data/evk_results.json (alles ganzzahlig: Zeitschritte, Personen). Aufruf aus dem Demo-Ordner:
    <python> tools/sweep_evakuierung.py [--workers 12]
Rechenzeit: wenige Minuten mit 12 Prozessen. Die Datei ist die Grundlage der Kurven in der App und der README-Zahlen (tests/test_claims.py)."""
import argparse
import itertools
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import evk_algorithm as A  # noqa: E402
import evk_constants as C  # noqa: E402
import evk_scenario as S  # noqa: E402


def configs():
    return list(itertools.product(range(C.FLOORS_MIN, C.FLOORS_MAX + 1), range(C.CABINS_MIN, C.CABINS_MAX + 1), range(C.CAPACITY_MIN, C.CAPACITY_MAX + 1),
                                  range(C.STAIRS_MIN, C.STAIRS_MAX + 1), range(C.HALT_MIN, C.HALT_MAX + 1)))   # (F, E, K, C, d)


def job(cfg):
    floors, cabins, capacity, stairs, halt = cfg
    params = A.Params(cabins, capacity, halt, stairs)
    rows = []
    for seed in C.SWEEP_SEEDS:
        building = S.make_building(seed, floors)
        for share in C.SHARES:
            mandatory, free = building.split(share)
            rows.append([sum(mandatory), sum(free), *A.measure(mandatory, free, params)])
    return cfg, rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=12)
    args = ap.parse_args()
    t0 = time.time()
    cfgs = sorted(configs(), key=lambda c: -(c[0] * 100 + c[1] * 10 + (5 - c[2])))   # die teuren Zellen zuerst
    data = {}
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        for cfg, rows in ex.map(job, cfgs):
            data[",".join(map(str, cfg))] = rows
            print("fertig", cfg, len(rows), "%.0f s" % (time.time() - t0), flush=True)
    out = {"meta": {"config_keys": "F,E,K,C,d", "columns": ["n_mandatory", "n_free", *A.COLUMNS], "seeds": list(C.SWEEP_SEEDS), "shares_pct": list(C.SHARES),
                    "row_order": "Zufalls-Seed aufsteigend, darin Anteil aufsteigend", "walk": C.WALK_TIME, "lift_time": C.LIFT_TIME,
                    "persons": [C.PERSONS_MIN, C.PERSONS_MAX]},
           "data": {k: data[k] for k in sorted(data)}}
    with open(os.path.join(ROOT, C.RESULTS_FILE), "w", encoding="utf-8") as fh:
        json.dump(out, fh, separators=(",", ":"))
    print("fertig: %d Zellen, %d Zeilen, %.0f s" % (len(data), sum(len(v) for v in data.values()), time.time() - t0), flush=True)


if __name__ == "__main__":
    main()
