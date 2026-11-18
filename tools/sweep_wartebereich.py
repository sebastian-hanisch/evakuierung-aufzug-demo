"""Messreihe Wartebereich: endliche Warteplätze je Etage, Rückstau auf die Treppe (CP-SAT auf dem Zeitnetz, tools/evk_cpsat.py).

Gebäude mit 3 Etagen, Kapazität 3, Treppe 2, Halt 1; Kabinen 1 und 2; Anteil 20, 30, 40 %; Plätze unbegrenzt / 2 / 1 / 0; Überlauf Q = 1, 2, 4 (nur bei endlichen Plätzen);
30 feste Zufalls-Seeds. Schreibt data/evk_wait.json: je Zelle Zeilen [Zufalls-Seed, T unbegrenzt (Verfahren der App), T mit Wartebereich, Freiwillige]. Zeitschritte, Personen.
Aufruf: <python> tools/sweep_wartebereich.py [--workers 8]   (braucht ortools: Test-venv)"""
import argparse
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import evk_algorithm as A  # noqa: E402
import evk_constants as C  # noqa: E402
import evk_cpsat as CS  # noqa: E402
import evk_scenario as S  # noqa: E402

VARIANTS = [(-1, 0)] + [(w, q) for w in (2, 1, 0) for q in (1, 2, 4)]


def job(args):
    seed, cabins = args
    params = A.Params(cabins, C.WAIT_CAPACITY, C.WAIT_HALT, C.WAIT_STAIRS)
    building = S.make_building(seed, C.WAIT_FLOORS)
    out = []
    for share in C.WAIT_SHARES:
        mandatory, free = building.split(share)
        t_star = A.joint_exact(mandatory, free, params).time
        for places, q in VARIANTS:
            kw = dict(lo=t_star, places=None if places < 0 else places, q=q or 2, hi=t_star + 30)
            t, a = CS.min_time(mandatory, free, params, workers=2, time_limit=60.0, **kw)
            if t is None:   # Zeitlimit unter Last: mit mehr Zeit und mehr Threads wiederholen, nie ein unentschiedenes Ergebnis speichern
                t, a = CS.min_time(mandatory, free, params, workers=4, time_limit=900.0, **kw)
            out.append((cabins, share, places, q, seed, t_star, t, None if a is None else sum(a)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()
    t0 = time.time()
    jobs = [(s, e) for s in C.SWEEP_SEEDS for e in (1, 2)]
    data, unknown = {}, 0
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        for i, rows in enumerate(ex.map(job, jobs)):
            for cabins, share, places, q, seed, t_star, t, a in rows:
                if t is None:
                    unknown += 1
                    continue
                data.setdefault(f"{cabins},{share},{places},{q}", []).append([seed, t_star, t, a])
            if i % 10 == 0:
                print(i, "%.0f s" % (time.time() - t0), flush=True)
    assert unknown == 0, f"{unknown} Aufrufe blieben unentschieden"
    out = {"meta": {"key": "Kabinen,Anteil,Plätze(-1 = unbegrenzt),Überlauf Q", "row": ["Zufalls-Seed", "T unbegrenzt (Verfahren der App)", "T mit Wartebereich (CP-SAT)", "Freiwillige"],
                    "floors": C.WAIT_FLOORS, "capacity": C.WAIT_CAPACITY, "stairs": C.WAIT_STAIRS, "halt": C.WAIT_HALT},
           "data": {k: data[k] for k in sorted(data)}}
    with open(os.path.join(ROOT, C.WAIT_FILE), "w", encoding="utf-8") as fh:
        json.dump(out, fh, separators=(",", ":"))
    print("fertig: %d Zellen, %.0f s" % (len(data), time.time() - t0), flush=True)


if __name__ == "__main__":
    main()
