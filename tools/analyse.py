"""Auswertung der Messreihe data/evk_results.json (und data/evk_wait.json): druckt alle Zahlen, die README und VERGLEICH.md nennen.

Aufruf: <python> tools/analyse.py [abschnitt ...]   (ohne Argument alles). Abschnitte: t1 t2 t3 t4 t6 wait nullen.
Die Grundgesamtheit "Basisraster" = Etagen 2 bis 4, Kabinen 1 und 2, Kapazität 2 bis 4, Treppe 2, Halt 1 (18 Zellen, wie die Vormessung V2);
"alle Zellen" = alle 96 Zellen der Reglerstufen (auch Kapazität 1, Treppe 3, Halt 2). Anteile ab 5 % ("mit Aufzugspflicht"), außer wo anders genannt."""
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import evk_constants as C  # noqa: E402
import evk_results as R  # noqa: E402

BASE = [(f, e, k, 2, 1) for f in (2, 3, 4) for e in (1, 2) for k in (2, 3, 4)]


def base_cells(**fixed):
    names = ("F", "E", "K", "C", "d")
    return [c for c in BASE if all(c[names.index(k)] == v for k, v in fixed.items())]


def mean_abs(cfgs, method, start=1):
    return float(np.mean([np.abs(R.col(c, "exact") - R.col(c, method))[:, start:].mean() for c in cfgs]))


def t1():
    print("== T1: Fehler des reinen Flussmodells (Takt) im Basisraster, Anteil ab 5 %, Mittel über 18 Zellen x 30 Zufalls-Seeds x 8 Anteile")
    print("T* %.2f, Fehler Takt %.2f, Rate %.2f, K1 %.2f, K1 (LPT, Einzelhalt) %.2f, K1 (exakt, Einzelhalt) %.2f" % (
        np.mean([R.col(c, "exact")[:, 1:].mean() for c in BASE]), R.pooled_error(BASE, "flow_takt"), R.pooled_error(BASE, "flow_rate"), R.pooled_error(BASE, "k1"),
        R.pooled_error(BASE, "k1_lpt"), R.pooled_error(BASE, "k1_single")))
    print("mittlerer absoluter Fehler: Takt %.2f, Rate %.2f, K1 %.2f, K1 Einzelhalt exakt %.2f, LPT %.2f" % tuple(mean_abs(BASE, m) for m in ("flow_takt", "flow_rate", "k1", "k1_single", "k1_lpt")))
    exact_k1 = sum(int((R.col(c, "exact") == R.col(c, "k1"))[:, 1:].sum()) for c in BASE)
    n = len(BASE) * R.SEEDS * (R.SHARES - 1)
    print("K1 exakt in %d von %d Zeilen; Fluss (Takt) exakt in %d" % (exact_k1, n, sum(int((R.col(c, "exact") == R.col(c, "flow_takt"))[:, 1:].sum()) for c in BASE)))
    over = sum(int((R.col(c, "k1") > R.col(c, "exact")).sum()) for c in R.all_cells())
    over_f = sum(int((R.col(c, "flow_takt") > R.col(c, "exact")).sum()) for c in R.all_cells())
    print("Ordnungsverletzungen über alle Zellen: K1 > T*: %d, Fluss > T*: %d" % (over, over_f))
    for name, groups in (("E", [(1,), (2,)]), ("K", [(2,), (3,), (4,)]), ("F", [(2,), (3,), (4,)])):
        for g in groups:
            cells = [c for c in BASE if c[{"E": 1, "K": 2, "F": 0}[name]] == g[0]]
            print("  %s = %d: Fehler Takt %.2f (T* %.1f)" % (name, g[0], R.pooled_error(cells, "flow_takt"), np.mean([R.col(c, "exact")[:, 1:].mean() for c in cells])))
    for i, s in enumerate(C.SHARES):
        if i == 0:
            continue
        print("  Anteil %d %%: Fehler Takt %.2f (T* %.1f), Rate %.2f" % (s, np.mean([(R.col(c, "exact") - R.col(c, "flow_takt"))[:, i].mean() for c in BASE]),
                                                                      np.mean([R.col(c, "exact")[:, i].mean() for c in BASE]), np.mean([(R.col(c, "exact") - R.col(c, "flow_rate"))[:, i].mean() for c in BASE])))
    worst = max(BASE, key=lambda c: (R.col(c, "exact") - R.col(c, "flow_takt"))[:, 8].mean())
    err = (R.col(worst, "exact") - R.col(worst, "flow_takt"))[:, 8].mean()
    print("größter Zellenmittelwert bei 40 %%: Zelle %s: Fehler %.2f bei T* %.1f" % (worst, err, R.col(worst, "exact")[:, 8].mean()))
    print("Spanne der Zelle (F,E,K) = (4,1,2) bei 40 %%: Fehler min %d max %d" % ((R.col((4, 1, 2, 2, 1), 'exact') - R.col((4, 1, 2, 2, 1), 'flow_takt'))[:, 8].min(), (R.col((4, 1, 2, 2, 1), 'exact') - R.col((4, 1, 2, 2, 1), 'flow_takt'))[:, 8].max()))
    for c in [(3, 1, 3, 2, 1), (3, 2, 3, 2, 1), (4, 1, 3, 2, 1)]:
        print("  Beispiel %s: Fehler je Anteil" % (c,), np.round(R.error_by_share(c), 2).tolist())


def t2():
    print("== T3b: Faustregel R (Aufzugszeit der Pflichtgruppe allein <= Fluss), Basisraster, Anteil ab 5 %")
    r = R.rule_counts(BASE)
    print(r, "Trefferquote wahr %.1f %%, falsch %.1f %%" % (100 * r["true_hit"] / r["true"], 100 * r["false_hit"] / r["false"]))
    print("alle Zellen:", R.rule_counts(R.all_cells()))
    rho_bins = [(0, 0.5), (0.5, 0.8), (0.8, 1.0), (1.0, 1.5), (1.5, 99)]
    flat = [(R.col(c, "barrier")[:, 1:] / R.col(c, "flow_takt")[:, 1:], (R.col(c, "exact") - R.col(c, "flow_takt"))[:, 1:]) for c in BASE]
    rho = np.concatenate([a.ravel() for a, _ in flat])
    err = np.concatenate([b.ravel() for _, b in flat])
    for lo, hi in rho_bins:
        m = (rho > lo) & (rho <= hi) if lo > 0 else (rho <= hi)
        print("  rho in (%.1f, %.1f]: %d Zellen, Fehler<=1 in %.1f %%, mittlerer Fehler %.2f, größter %d" % (lo, hi, m.sum(), 100 * (err[m] <= 1).mean(), err[m].mean(), err[m].max()))


def t3():
    print("== T2: freiwillige Aufzugsnutzung (Basisraster, K = 2, 3, 4 zusammen; je (F, E) und Anteil)")
    for f in (2, 3, 4):
        for e in (1, 2):
            cells = base_cells(F=f, E=e)
            for i in (0, 2, 4, 8):
                amin = np.mean([R.col(c, "a_min")[:, i].mean() for c in cells])
                amax = np.mean([R.col(c, "a_max")[:, i].mean() for c in cells])
                walkers = np.mean([R.col(c, "n_free")[:, i].mean() for c in cells])
                helps = sum(int((R.col(c, "exact")[:, i] < R.col(c, "stairs_only")[:, i]).sum()) for c in cells)
                gain = np.mean([(R.col(c, "stairs_only") - R.col(c, "exact"))[:, i].mean() for c in cells])
                print("  F=%d E=%d Anteil %2d %%: Gehende %.1f, a_min %.1f (%.0f %%), a_max %.1f, hilft in %d von %d, Gewinn %.2f" % (
                    f, e, C.SHARES[i], walkers, amin, 100 * amin / walkers, amax, helps, 90, gain))
    for i in (0, 4, 8):
        helps = sum(int((R.col(c, "exact")[:, i] < R.col(c, "stairs_only")[:, i]).sum()) for c in BASE)
        print("  Basisraster, Anteil %d %%: Freiwillige helfen in %d von %d Zeilen" % (C.SHARES[i], helps, len(BASE) * R.SEEDS))


def t4():
    print("== T4: Kipppunkte (Median über 30 Zufalls-Seeds; 45 = bis 40 % nie), Basisraster")
    for c in BASE:
        print("  F=%d E=%d K=%d: alpha_1 %.1f (%d/30)  alpha_B %.1f (%d/30)  alpha_F %.1f (%d/30)" % (
            c[0], c[1], c[2], R.tipping_median(c, "exact"), R.tipping_count(c, "exact"), R.tipping_median(c, "binding"), R.tipping_count(c, "binding"),
            R.tipping_median(c, "flow"), R.tipping_count(c, "flow")))


def t6():
    print("== T6: Empfindlichkeit F = 3: Treppe C = 3 und Halt d = 2 gegen die Basis (K = 3)")
    for label, cfg_of in (("Basis", lambda e: (3, e, 3, 2, 1)), ("Treppe 3", lambda e: (3, e, 3, 3, 1)), ("Halt 2", lambda e: (3, e, 3, 2, 2))):
        for e in (1, 2):
            c = cfg_of(e)
            print("  %-9s E=%d: alpha_1 %.1f (%d/30), alpha_B %.1f (%d/30), Fehler Takt bei 20 %% %.2f, bei 40 %% %.2f" % (
                label, e, R.tipping_median(c, "exact"), R.tipping_count(c, "exact"), R.tipping_median(c, "binding"), R.tipping_count(c, "binding"),
                R.error_by_share(c)[4], R.error_by_share(c)[8]))


def wait():
    print("== Wartebereich (F = 3, K = 3, Treppe 2, Halt 1; Wirkung = T(Plätze) minus T(unbegrenzt), gepaart; 30 Zufalls-Seeds)")
    for e in (1, 2):
        for share in C.WAIT_SHARES:
            for places, q in [(-1, 0), (2, 2), (1, 2), (0, 2), (0, 1), (0, 4), (2, 1), (1, 1), (2, 4), (1, 4)]:
                w = R.wait_effect(e, share, places, q)
                print("  E=%d Anteil %d %% W=%2d Q=%d: T %.2f, Wirkung %.2f, Seeds mit Wirkung %d/%d, Freiwillige %.2f" % (
                    e, share, places, q, w["mean_time"], w["mean_effect"], w["seeds_affected"], w["seeds"], w["mean_volunteers"]))
    for share in (30, 40):
        base = R.wait_effect(1, share, 0, 2)["mean_time"]
        print("  Hebel Anteil %d %%: E=1 W=0 %.2f; E=1 unbegrenzt %.2f; E=2 W=0 %.2f; E=2 unbegrenzt %.2f" % (
            share, base, R.wait_effect(1, share, -1, 0)["mean_time"], R.wait_effect(2, share, 0, 2)["mean_time"], R.wait_effect(2, share, -1, 0)["mean_time"]))


def nullen():
    print("== Nullspaltenprüfung (alle 96 Zellen, 25 920 Zeilen)")
    names = R.load()["meta"]["columns"]
    total = sum(len(v) for v in R.load()["data"].values())
    for name in names:
        zeros = sum(int((R.col(c, name) == 0).sum()) for c in R.all_cells()) if name in R.columns() else 0
        print("  %-16s Nullen %6d von %d" % (name, zeros, total))
    lt = sum(int((R.col(c, "flow_takt") < R.col(c, "exact")).sum()) for c in R.all_cells())
    print("  Fluss (Takt) kleiner als T*: %d; K1 gleich T*: %d; T* kleiner als T getrennt: %d; K1 größer T*: %d" % (
        lt, sum(int((R.col(c, "k1") == R.col(c, "exact")).sum()) for c in R.all_cells()),
        sum(int((R.col(c, "exact") < R.col(c, "stairs_only")).sum()) for c in R.all_cells()), sum(int((R.col(c, "k1") > R.col(c, "exact")).sum()) for c in R.all_cells())))


SECTIONS = {"t1": t1, "t2": t2, "t3": t3, "t4": t4, "t6": t6, "wait": wait, "nullen": nullen}

if __name__ == "__main__":
    for key in (sys.argv[1:] or list(SECTIONS)):
        SECTIONS[key]()
        print()
