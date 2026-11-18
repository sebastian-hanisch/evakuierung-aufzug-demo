"""Wiederholung mit 300 weiteren Zufalls-Seeds (31 bis 330) im Basisraster, um die Abweichung gegen die Vormessung (Fehler 1,54) einzuordnen."""
import os, sys, time, json
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import evk_algorithm as A, evk_scenario as S, evk_constants as C

BASE = [(f, e, k, 2, 1) for f in (2, 3, 4) for e in (1, 2) for k in (2, 3, 4)]

def job(args):
    cfg, seeds = args
    f, e, k, c, d = cfg
    p = A.Params(e, k, d, c)
    out = []
    for seed in seeds:
        b = S.make_building(seed, f)
        per = []
        for share in C.SHARES[1:]:
            m, fr = b.split(share)
            j = A.joint_exact(m, fr, p)
            flow = A.flow_time(m, fr, p, "takt", hint=j.time + 1)
            per.append((j.time, flow, max(flow, A.barrier_time(m, p))))
        out.append(per)
    return cfg, out

if __name__ == "__main__":
    t0 = time.time()
    seeds = list(range(31, 331))
    chunks = [(c, seeds[i::5]) for c in BASE for i in range(5)]
    res = {}
    with ProcessPoolExecutor(max_workers=12) as ex:
        for cfg, out in ex.map(job, chunks):
            res.setdefault(cfg, []).extend(out)
    arr = np.array([res[c] for c in BASE])          # Zelle, Seed, Anteil, (T*, Fluss, K1)
    err = arr[..., 0] - arr[..., 1]; k1 = arr[..., 0] - arr[..., 2]
    print("300 Seeds: Fehler Takt %.3f, K1 %.3f, T* %.2f, in %.0f s" % (err.mean(), k1.mean(), arr[..., 0].mean(), time.time() - t0))
    for e in (1, 2):
        idx = [i for i, c in enumerate(BASE) if c[1] == e]
        print(" E=%d: Fehler %.3f" % (e, err[idx].mean()))
    ps = err.mean(axis=(0, 2))
    print("je Zufalls-Seed: Mittel %.3f, Standardabweichung %.3f, Standardfehler eines 30er-Mittels %.3f" % (ps.mean(), ps.std(ddof=1), ps.std(ddof=1) / 30 ** 0.5))
