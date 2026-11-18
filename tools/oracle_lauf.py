"""Großer Orakel-Lauf (Scratch, nicht im Schnelltest): mindestens 200 Zufallsinstanzen (SplitMix64, Zufalls-Seed 2026118).

Je Instanz: gemeinsames exaktes Modell gegen (1) Vollaufzählung aller Aufteilungen und Fahrtenpläne mit Treppen-Maximalfluss (networkx; nur kleine Instanzen), (2) CP-SAT auf dem
Zeitnetz (T* zulässig, T* - 1 unzulässig), (3) den Prüfer (Plan zulässig, Zeit gleich T*), (4) das Flussmodell (untere Schranke) und die Maschinenschranke; dazu der Wartebereich
(unbegrenzt gleich T*, monoton in den Plätzen). Aufruf: <python> tools/oracle_lauf.py [N]   (Test-venv mit ortools und networkx). Druckt die Zählungen."""
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for sub in ("", "tools", "tests"):
    sys.path.insert(0, os.path.join(ROOT, sub))
import evk_algorithm as A  # noqa: E402
import evk_cpsat as CS  # noqa: E402
from evk_rng import SplitMix64  # noqa: E402
from test_oracle_evakuierung_aufzug import brute_joint  # noqa: E402


def main(n_instances=240):
    rng = SplitMix64(2026118)
    t0 = time.time()
    s = dict(n=0, brute_n=0, brute_gleich=0, cpsat_n=0, cpsat_gleich=0, cpsat_unbekannt=0, pruefer_ok=0, fluss_unter_exakt=0, fluss_ueber_exakt=0, schranke_ueber_exakt=0,
             freie_wahl_strikt=0, w_n=0, w_monoton=0, w_unbegrenzt_gleich=0, w_wirkt=0, w_unbekannt=0)
    for i in range(n_instances):
        floors = 2 + rng.below(2)
        m = [2 + rng.below(5 if floors == 2 else 3) for _ in range(floors)]
        mandatory = tuple(rng.below(min(m[j], 3) + 1) for j in range(floors))
        free = tuple(m[j] - mandatory[j] for j in range(floors))
        p = A.Params(1 + rng.below(2), 1 + rng.below(4), 1 + rng.below(2), 2 + rng.below(2))
        j = A.joint_exact(mandatory, free, p)
        s["n"] += 1
        s["freie_wahl_strikt"] += j.time < j.time_stairs_only
        flow = A.flow_time(mandatory, free, p, "takt", hint=j.time + 1)
        s["fluss_unter_exakt"] += flow < j.time
        s["fluss_ueber_exakt"] += flow > j.time
        s["schranke_ueber_exakt"] += A.barrier_time(mandatory, p) > j.time
        riders = tuple(a + b for a, b in zip(mandatory, j.split))
        problems, plan_time = A.evaluate_plan(mandatory, free, j.split, [list(c) for c in A.Lift(p).plan(riders)], p)
        s["pruefer_ok"] += (problems == [] and plan_time == j.time)
        if sum(mandatory) + sum(free) <= 10 and sum(x + 1 for x in free) <= 14:
            b = brute_joint(mandatory, free, p)
            s["brute_n"] += 1
            s["brute_gleich"] += b == j.time
            assert b == j.time, ("Vollaufzählung weicht ab", mandatory, free, p, j.time, b)
        yes, _ = CS.feasible(mandatory, free, p, j.time, workers=8)
        no = CS.feasible(mandatory, free, p, j.time - 1, workers=8)[0] if j.time > 0 else "nein"
        s["cpsat_n"] += 1
        if "unbekannt" in (yes, no):
            s["cpsat_unbekannt"] += 1
        else:
            s["cpsat_gleich"] += (yes == "ja" and no == "nein")
            assert yes == "ja" and no == "nein", ("CP-SAT weicht ab", mandatory, free, p, j.time, yes, no)
        if i < 140 and sum(mandatory) > 0:
            vals = {w: CS.min_time(mandatory, free, p, lo=j.time, places=w, q=2, workers=8, hi=j.time + 20)[0] for w in (None, 2, 1, 0)}
            s["w_n"] += 1
            if None in vals.values():
                s["w_unbekannt"] += 1
                continue
            s["w_unbegrenzt_gleich"] += vals[None] == j.time
            s["w_monoton"] += vals[None] <= vals[2] <= vals[1] <= vals[0]
            s["w_wirkt"] += vals[0] > vals[None]
            assert vals[None] == j.time and vals[None] <= vals[2] <= vals[1] <= vals[0], ("Wartebereich", mandatory, free, p, vals)
        if i % 20 == 0:
            print(i, s, "%.0f s" % (time.time() - t0), flush=True)
    print("ENDE", s, "%.0f s" % (time.time() - t0))


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 240)
