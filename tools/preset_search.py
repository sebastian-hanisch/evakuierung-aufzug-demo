"""Sucht die Zufalls-Seeds der Presets: erster Seed ab 101 (außerhalb der Messreihen-Stichprobe 1 bis 30), bei dem das Preset zeigt, wofür es steht.

Aufruf: <python> tools/preset_search.py   (druckt je Preset den Seed und die Kennzahlen; die Werte stehen danach in evk_constants.PRESETS)."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import evk_evaluation as ev  # noqa: E402

START, STOP = 101, 700


def settings(seed, floors=3, cabins=1, capacity=3, halt=1, stairs=2, share=20):
    return ev.Settings(floors, cabins, capacity, halt, stairs, share, seed)


def first(pred, **kw):
    for seed in range(START, STOP):
        a = ev.analyse(settings(seed, **kw))
        if pred(a):
            return seed, a
    return None, None


def show(name, seed, a):
    if a is None:
        print(name, "kein Seed gefunden")
        return
    print("%-34s Seed %d: Gehende %d, Pflicht %d, T* %d, Fluss %d, Schranke %d, Rate %d, getrennt %d, a %d..%d, optimal %d" % (
        name, seed, a.n_walkers, a.n_mandatory, a.exact, a.flow_takt, a.barrier, a.flow_rate, a.joint.time_stairs_only, a.joint.a_min, a.joint.a_max, a.joint.n_optimal))


def main():
    seed, a = first(lambda a: 2 <= a.gap <= 3 and a.exact >= 8 and a.n_mandatory >= 2 and 12 <= a.building.total <= 16)
    show("Standardfall (F3 E1 K3, 20 %)", seed, a)
    seed, a = first(lambda a: a.gap == 0 and a.rule_holds and a.barrier > 0 and a.n_mandatory >= 1 and a.building.total >= 11, share=5)
    show("Fluss reicht (5 %)", seed, a)
    for seed in range(START, STOP):
        a1 = ev.analyse(settings(seed, floors=4, cabins=1, capacity=2, share=40))
        a2 = ev.analyse(settings(seed, floors=4, cabins=2, capacity=2, share=40))
        if a1.gap >= 6 and a2.gap <= 1 and a1.building.total >= 17:
            show("Viel Pflicht, eine Kabine", seed, a1)
            show("Zweite Kabine", seed, a2)
            break
    seed, a = first(lambda a: a.joint.time < a.joint.time_stairs_only and a.joint.a_min >= 2 and a.building.total >= 12, share=0)
    show("Nur freiwillig (0 %)", seed, a)
    seed, a = first(lambda a: a.gap >= 3 and a.n_mandatory >= 2, halt=2, stairs=3)
    show("Langer Halt, schnelle Treppe", seed, a)
    for seed in range(START, STOP):
        a1 = ev.analyse(settings(seed, capacity=1))
        a3 = ev.analyse(settings(seed, capacity=3))
        if a1.exact >= a3.exact + 4 and a1.n_mandatory >= 3 and a1.gap >= 2:
            show("Ohne Bündeln (K = 1)", seed, a1)
            show("   zum Vergleich K = 3", seed, a3)
            break


if __name__ == "__main__":
    main()
