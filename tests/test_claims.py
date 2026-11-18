"""Jede Zahl der README wird hier aus data/evk_results.json und data/evk_wait.json nachgerechnet und im README-Text gesucht (DEMO-PLAYBOOK §4, §11a).

Grundgesamtheit „Basisraster“: Etagen 2 bis 4, Kabinen 1 und 2, Kapazität 2 bis 4, Treppe 2, Halt 1 (18 Zellen), Anteil 5 bis 40 %, 30 Zufalls-Seeds: 4320 Paare.
Die Messreihe ist ganzzahlig; das Neu-Rechnen einer Stichprobe steht in tests/test_results.py (exakt). Zahlen, die nur die README nennt und nicht im Test stehen
(Gegenprobe gegen den Kern der Vormessung, 300 weitere Zufalls-Seeds, großer Orakel-Lauf, Zahlen der Vormessung selbst), sind dort als „Messung dieser README“ gekennzeichnet."""

from pathlib import Path

import numpy as np
import pytest

import evk_constants as C
import evk_evaluation as ev
import evk_results as R

README = (Path(__file__).resolve().parent.parent / "README.md").read_text(encoding="utf-8")
BASE = [(f, e, k, 2, 1) for f in (2, 3, 4) for e in (1, 2) for k in (2, 3, 4)]


def de(x, nd=1):
    return ev.de(x, nd).replace("-", "−")


def thousands(n):
    return f"{n:,}".replace(",", " ") if n >= 10000 else str(n)     # Tausendertrenner erst ab fünf Stellen (README-Schreibweise)


def said(*texts):
    for t in texts:
        assert t in README, f"nicht in der README: {t!r}"


def mean_error(cfgs, method="flow_takt"):
    return R.pooled_error(cfgs, method)


def test_the_annotated_population_is_what_the_readme_says():
    assert len(BASE) == 18 and 18 * 30 * 8 == 4320
    assert len(R.all_cells()) == 96 and 96 * 270 == 25920
    said("18 Zellen", "4320 Paare", "25 920 Zeilen", "96 Stufenkombinationen")


def test_flow_error_mean_and_bands():
    said(de(mean_error(BASE), 2), de(np.mean([R.col(c, "exact")[:, 1:].mean() for c in BASE]), 1))
    ps = R.per_seed_error(BASE, "flow_takt")
    lo, hi = R.bootstrap_band(ps)
    said(f"[{de(lo, 2)}; {de(hi, 2)}]")
    assert (round(mean_error(BASE), 2), round(lo, 2), round(hi, 2)) == (1.94, 1.67, 2.23)
    assert round(float(np.mean([R.col(c, "exact")[:, 1:].mean() for c in BASE])), 1) == 9.3
    exact = sum(int((R.col(c, "exact") == R.col(c, "flow_takt"))[:, 1:].sum()) for c in BASE)
    assert exact == 2365
    said(f"exakt in {thousands(exact)} von 4320 Paaren")
    assert all((R.col(c, "flow_takt") <= R.col(c, "exact")).all() for c in R.all_cells())


def test_flow_error_by_cabins_share_floors_and_capacity():
    one, two = [c for c in BASE if c[1] == 1], [c for c in BASE if c[1] == 2]
    for cfgs, expected in ((one, (3.26, 2.84, 3.71)), (two, (0.63, 0.49, 0.77))):
        lo, hi = R.bootstrap_band(R.per_seed_error(cfgs, "flow_takt"))
        assert (round(mean_error(cfgs), 2), round(lo, 2), round(hi, 2)) == expected
        said(f"{de(expected[0], 2)} [{de(expected[1], 2)}; {de(expected[2], 2)}]")
    by_share = [np.mean([(R.col(c, "exact") - R.col(c, "flow_takt"))[:, i].mean() for c in BASE]) for i in range(1, 9)]
    assert (round(by_share[0], 2), round(by_share[-1], 2)) == (0.22, 4.28) and all(x < y for x, y in zip(by_share, by_share[1:]))   # wächst mit dem Anteil
    by_floors = [round(mean_error([c for c in BASE if c[0] == f]), 2) for f in (2, 3, 4)]
    assert by_floors == [0.62, 1.81, 3.40]
    by_capacity = [round(mean_error([c for c in BASE if c[2] == k]), 2) for k in (2, 3, 4)]
    assert by_capacity == [2.82, 1.80, 1.22]
    said("Anteil 5 % 0,22, Anteil 40 % 4,28", "0,62 / 1,81 / 3,40", "2,82 / 1,80 / 1,22")


def test_largest_cell_and_single_buildings():
    worst = max(BASE, key=lambda c: (R.col(c, "exact") - R.col(c, "flow_takt"))[:, 8].mean())
    assert worst == (4, 1, 2, 2, 1)
    err = (R.col(worst, "exact") - R.col(worst, "flow_takt"))[:, 8]
    t_star = R.col(worst, "exact")[:, 8].mean()
    assert (round(err.mean(), 2), round(t_star, 1), round(100 * err.mean() / t_star), int(err.min()), int(err.max())) == (14.57, 30.0, 49, 3, 27)
    said("14,57 bei T\\* = 30,0 (49 %)", "3 bis 27 Zeitschritte")


def test_error_in_the_full_grid_and_single_stop_versions():
    cells = R.all_cells()
    # Gesamtraster, eine Kabine: der Fehler des Flusses ist bei Kapazität 1 am größten und fällt mit der Kapazität; mit Maschinenschranke unter 0,05
    by_cap = [R.pooled_error([c for c in cells if c[1] == 1 and c[2] == k], "flow_takt") for k in (1, 2, 3, 4)]
    assert all(x > y for x, y in zip(by_cap, by_cap[1:]))
    assert all(R.pooled_error([c for c in cells if c[2] == k], "k1") < 0.05 for k in (1, 2, 3, 4))
    worst = max(cells, key=lambda c: (R.col(c, "exact") - R.col(c, "flow_takt"))[:, 8].mean())
    assert worst == (4, 1, 1, 2, 2) and round(float((R.col(worst, "exact") - R.col(worst, "flow_takt"))[:, 8].mean()), 1) == 38.5
    said("am größten bei Kapazität 1", "unter 0,05", "bis 38,5 (4 Etagen, 1 Kabine, Kapazität 1, Halt 2)")
    # Einzelhalt-Fassungen: im Mittel zu lang, aber nicht in allen Paaren; bei Kapazität 1 gleich Fluss plus Schranke
    for method in ("k1_single", "k1_lpt"):
        d = np.concatenate([(R.col(c, "exact") - R.col(c, method))[:, 1:].ravel() for c in BASE])
        assert (int((d < 0).sum()), int((d > 0).sum())) == (1451, 243)
    assert all((R.col(c, "k1") == R.col(c, "k1_single")).all() for c in cells if c[2] == 1)
    said("in 1451 von 4320 Paaren über T\\* und in 243 darunter")


def test_rate_form_is_no_replacement():
    lo, hi = R.bootstrap_band(R.per_seed_error(BASE, "flow_rate"))
    assert (round(mean_error(BASE, "flow_rate"), 2), round(lo, 2), round(hi, 2)) == (0.03, -0.20, 0.26)
    said(f"0,03 [{de(lo, 2)}; {de(hi, 2)}]")
    over = sum(int((R.col(c, "flow_rate") > R.col(c, "exact"))[:, 1:].sum()) for c in BASE)
    under = sum(int((R.col(c, "flow_rate") < R.col(c, "exact"))[:, 1:].sum()) for c in BASE)
    same = sum(int((R.col(c, "flow_rate") == R.col(c, "exact"))[:, 1:].sum()) for c in BASE)
    assert (over, under, same) == (1818, 821, 1681) and over + under + same == 4320
    mean_abs = float(np.mean([np.abs(R.col(c, "exact") - R.col(c, "flow_rate"))[:, 1:].mean() for c in BASE]))
    mean_abs_takt = float(np.mean([np.abs(R.col(c, "exact") - R.col(c, "flow_takt"))[:, 1:].mean() for c in BASE]))
    assert (round(mean_abs, 2), round(mean_abs_takt, 2)) == (1.44, 1.94)
    said("in 1818 Paaren über T\\*, in 821 darunter, in 1681 gleich", "1,44 gegen 1,94")


def test_flow_plus_machine_barrier():
    lo, hi = R.bootstrap_band(R.per_seed_error(BASE, "k1"))
    assert (round(mean_error(BASE, "k1"), 2), round(lo, 2), round(hi, 2)) == (0.07, 0.04, 0.10)
    exact_k1 = sum(int((R.col(c, "exact") == R.col(c, "k1"))[:, 1:].sum()) for c in BASE)
    assert exact_k1 == 4037 and round(100 * exact_k1 / 4320, 1) == 93.4
    assert sum(int((R.col(c, "k1") > R.col(c, "exact")).sum()) for c in R.all_cells()) == 0
    lo2, hi2 = R.bootstrap_band(R.per_seed_error(BASE, "k1_single"))
    assert (round(mean_error(BASE, "k1_single"), 2), round(lo2, 2), round(hi2, 2)) == (-1.33, -1.52, -1.15)
    assert round(mean_error(BASE, "k1_lpt"), 2) == -1.35
    said("**0,07** [0,04; 0,10]", "4037 von 4320 Paaren (93,4 %)", "0 Verletzungen in allen 25 920 Zeilen", "−1,33 [−1,52; −1,15] (exakt) und −1,35 (Listenregel)")


def test_rule_of_thumb_in_the_basic_grid_and_in_all_cells():
    r = R.rule_counts(BASE)
    assert (r["true"], r["true_hit"], r["true_max_error"], r["false"], r["false_hit"], r["false_max_error"], r["false_exact"]) == (2644, 2629, 2, 1676, 506, 27, 0)
    assert round(100 * r["true_hit"] / r["true"], 1) == 99.4 and round(100 * r["false_hit"] / r["false"], 1) == 30.2
    err = np.concatenate([(R.col(c, "exact") - R.col(c, "flow_takt"))[:, 1:].ravel() for c in BASE])
    rho = np.concatenate([(R.col(c, "barrier")[:, 1:] / R.col(c, "flow_takt")[:, 1:]).ravel() for c in BASE])
    assert round(float(err[rho > 1].mean()), 2) == 4.83
    big = rho > 1.5
    assert (int(big.sum()), int(((err <= 1) & big).sum())) == (822, 0)
    said("2629 von 2644", "(99,4 %, größter Fehler 2)", "506 von 1676 (30,2 %), mittlerer Fehler 4,83, größter 27", "(822 Paare)", "in 0 davon")
    allc = R.rule_counts(R.all_cells())
    assert (allc["true"], allc["true_hit"], allc["false"], allc["false_hit"], allc["false_max_error"]) == (12816, 12786, 10224, 1134, 68)
    assert round(100 * allc["false_hit"] / allc["false"], 1) == 11.1 and allc["true_max_error"] == 2
    said("12 786 von 12 816", "1134 von 10 224 (11,1 %, größter Fehler 68)")


def test_every_rule_hit_requires_the_rule_to_hold():
    # jeder Treffer mit Fehler 0 liegt im Fall „Regel gilt“ (R falsch hat 0 exakte Zellen): R ist notwendig für einen exakten Fluss
    for c in R.all_cells():
        exact_rows = (R.col(c, "exact") == R.col(c, "flow_takt"))[:, 1:]
        rule = (R.col(c, "barrier") <= R.col(c, "flow_takt"))[:, 1:]
        assert not (exact_rows & ~rule).any(), c


def test_voluntary_use_by_share():
    expected = {0: (414, 1.59, 13.3, 11.9, 0.98), 4: (89, 0.26, 10.5, 2.5, 0.18), 8: (12, 0.02, 7.5, 0.3, 0.02)}
    for i, (helps_n, amin, walkers, pct, gain) in expected.items():
        helps = sum(int((R.col(c, "exact")[:, i] < R.col(c, "stairs_only")[:, i]).sum()) for c in BASE)
        a_min = np.mean([R.col(c, "a_min")[:, i].mean() for c in BASE])
        w = np.mean([R.col(c, "n_free")[:, i].mean() for c in BASE])
        g = np.mean([(R.col(c, "stairs_only") - R.col(c, "exact"))[:, i].mean() for c in BASE])
        assert (helps, round(a_min, 2), round(w, 1), round(100 * a_min / w, 1), round(g, 2)) == (helps_n, amin, walkers, pct, gain), i
    cells_min = [R.col(c, "a_min")[:, 0].mean() for c in BASE]
    assert round(min(cells_min), 1) == 1.0 and round(max(cells_min), 1) == 2.2
    said("in 414 von 540 Gebäuden", "1,59 von 13,3 Gehenden (11,9 %), Gewinn im Mittel 0,98 Zeitschritte", "89 von 540, 0,26 Freiwillige (2,5 %), Gewinn 0,18", "12 von 540, 0,02 Freiwillige (0,3 %), Gewinn 0,02")


def test_tipping_points():
    one, two = [c for c in BASE if c[1] == 1], [c for c in BASE if c[1] == 2]
    med1 = [R.tipping_median(c) for c in one]
    med2 = [R.tipping_median(c) for c in two]
    assert (min(med1), max(med1)) == (15.0, 27.5) and all(m <= 40 for m in med1)
    assert (min(R.tipping_count(c) for c in one), max(R.tipping_count(c) for c in one)) == (26, 30)
    assert (min(med2), max(med2)) == (25.0, 45.0) and sum(m > 40 for m in med2) == 4
    assert (min(R.tipping_count(c) for c in two), max(R.tipping_count(c) for c in two)) == (1, 28)
    flow = {c: R.tipping_median(c, "flow") for c in BASE}
    assert sum(m > 40 for m in flow.values()) == 17 and [(c, m) for c, m in flow.items() if m <= 40] == [((4, 1, 2, 2, 1), 30.0)]
    said("**15 bis 27,5 %**", "26 bis 30 von 30", "25 % bis über 40 %, in 4 von 9 Zellen im Median über 40 % (1 bis 28 von 30", "17 von 18 Zellen", "4 Etagen, 1 Kabine, Kapazität 2: 30 %")


def test_sensitivity_of_the_tipping_point():
    got = {}
    for label, cell in (("basis", (3, 2, 3, 2, 1)), ("stairs", (3, 2, 3, 3, 1)), ("halt", (3, 2, 3, 2, 2))):
        got[label] = (R.tipping_median(cell), R.tipping_median(cell, "binding"))
    assert got == {"basis": (37.5, 32.5), "stairs": (30.0, 25.0), "halt": (25.0, 20.0)}
    assert [R.tipping_median(c) for c in ((3, 1, 3, 2, 1), (3, 1, 3, 3, 1), (3, 1, 3, 2, 2))] == [15.0, 15.0, 15.0]
    said("37,5 % (Treppe 2, Halt 1), 30 % (Treppe 3), 25 % (Halt 2)")


def test_waiting_area():
    def effect(e, share, w, q):
        return R.wait_effect(e, share, w, q)
    e = {w: effect(1, 20, w, 2) for w in (2, 1, 0)}
    assert [round(e[w]["mean_effect"], 2) for w in (2, 1, 0)] == [0.03, 0.13, 0.47] and e[0]["seeds_affected"] == 11
    q1, q4 = effect(1, 20, 0, 1), effect(1, 20, 0, 4)
    assert (round(q1["mean_effect"], 2), q1["seeds_affected"], round(q4["mean_effect"], 2), q4["seeds_affected"]) == (0.97, 17, 0.37, 9)
    gain0 = effect(1, 30, 0, 2)["mean_time"] - effect(2, 30, 0, 2)["mean_time"]
    gain_u = effect(1, 30, -1, 0)["mean_time"] - effect(2, 30, -1, 0)["mean_time"]
    assert (round(gain0, 2), round(effect(1, 30, 0, 2)["mean_time"], 2), round(effect(2, 30, 0, 2)["mean_time"], 2)) == (3.83, 12.17, 8.33)
    assert (round(gain_u, 2), round(effect(1, 30, -1, 0)["mean_time"], 2), round(effect(2, 30, -1, 0)["mean_time"], 2)) == (4.20, 11.67, 7.47)
    said("2 Plätze 0,03, 1 Platz 0,13, 0 Plätze **0,47** (11 von 30", "mit Q = 1 0,97 (17 von 30), mit Q = 4 0,37 (9 von 30)", "3,83 Zeitschritte (12,17 auf 8,33)", "4,20 (11,67 auf 7,47)")


def test_zero_violations_and_the_unlimited_column():
    for c in R.all_cells():
        assert (R.col(c, "flow_takt") <= R.col(c, "k1")).all() and (R.col(c, "k1") <= R.col(c, "exact")).all()
    assert sum(int((R.col(c, "exact") < R.col(c, "stairs_only")).sum()) for c in R.all_cells()) == 2512
    said("2512 solche Zeilen von 25 920")


def test_assumptions_text_in_the_app_is_the_same_as_in_the_readme():
    assert C.ASSUMPTIONS_MARKDOWN.strip() in README


def test_the_test_count_in_the_readme_matches_the_suite():
    import re
    import subprocess
    import sys
    out = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider", str(Path(__file__).resolve().parent)],
                         capture_output=True, text=True, timeout=300).stdout
    n = int(re.search(r"(\d+) tests? collected", out).group(1))
    assert f"{n} Tests in `tests/`" in README, n


def test_the_readme_has_the_required_sections_and_the_live_link_marker():
    for heading in ("## Warum dieses Problem", "## Modell", "## Methodik", "## Befunde (gemessen, keine Behauptungen)", "## Befunde und Korrekturen", "## Ehrliche Grenzen",
                    "## Verifikation", "## Dateistruktur", "## Bewusst nicht umgesetzt", "## Lokal ausführen", "## Tests ausführen"):
        assert heading in README, heading
    assert "TODO nach dem Deploy" in README
    for word in ("Behinderte", "Saatwert", "trägt "):
        assert word not in README
