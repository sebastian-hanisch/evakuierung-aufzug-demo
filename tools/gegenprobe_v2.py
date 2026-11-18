"""Kern der Demo gegen den V2-Kern der Vormessung auf denselben Instanzen (V2-Generator) und gegen v2_rohdaten.json.
Aufruf aus dem Demo-Ordner; braucht den Planungsordner der Website neben dem Demo-Ordner. Ergebnis beim Bau: 8100 Zeilen, 0 Abweichungen in allen zwölf Spalten."""
import json, os, sys, time
from concurrent.futures import ProcessPoolExecutor
DEMO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V2 = os.path.normpath(os.path.join(DEMO, "..", "sebastianhanisch-website", "docs", "planung", "barrierefreiheit-planung", "vormessung_evakuierung", "v2"))
sys.path.insert(0, V2); sys.path.insert(0, DEMO)
import evak_v2_model as M2
import evk_algorithm as A

def job(args):
    cfg, rows = args
    F, E, K, C, d = cfg
    p = A.Params(E, K, d, C)
    bad = []
    n_checked = 0
    for r in rows:
        (_, _, _, _, _, seed, al, npf, nfr, T, amin, amax, tsep, cnt, tlp, tsf, ftakt, frate, k1, k2, k3, af, k1l, k1s) = r
        mini = M2.make_mini(seed, F)
        n, free = mini.split(al)
        got = A.measure(n, free, p)
        exp = (T, amin, amax, tsep, cnt, tlp, tsf, ftakt, frate, k1, k1l, k1s)
        n_checked += 1
        if got != exp:
            bad.append((cfg, seed, al, got, exp))
    return cfg, n_checked, bad

if __name__ == "__main__":
    t0 = time.time()
    data = json.load(open(os.path.join(V2, "v2_rohdaten.json")))
    byc = {}
    for r in data["rows"]:
        byc.setdefault(tuple(r[:5]), []).append(r)
    tot = 0; bads = []
    with ProcessPoolExecutor(max_workers=12) as ex:
        for cfg, n, bad in ex.map(job, list(byc.items())):
            tot += n; bads += bad
    print("Zeilen", tot, "Abweichungen", len(bads), "%.0f s" % (time.time() - t0))
    for b in bads[:10]: print(b)
