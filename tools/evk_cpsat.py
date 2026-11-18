"""CP-SAT auf dem Zeitnetz (nur Orakel und Messreihe Wartebereich; NICHT in der App, ortools steht nicht in requirements.txt).

Gemeinsames Modell Treppe + Aufzug, freie Wahl der Gehenden, optional Wartebereich mit Rückstau.
Aufzug: ganzzahliger Kabinenfluss über Zustände (Etage f, Zeitschritt t, Beladung l); Kanten: warten, fahren (lift_time je Etage), laden an Etage f
(l -> l + b, dauert halt, b Personen verlassen die Warteschlange der Etage), entladen am Ausgang (l -> 0, dauert halt, die Ankunft zählt zum Beginn).
Treppe: Warteschlange w_f(t), Abgang x_f(t) <= stairs - Sperre_f(t), Ankunft walk Zeitschritte später an Etage f - 1 (Etage 1: Ausgang).
Wartebereich: auf Etage f warten e_f(t) Personen auf den Aufzug (Pflicht plus freiwillige, ab Zeitschritt 0 am Aufzug); `places` Plätze (None = unbegrenzt).
Überlauf o = max(0, e - places) steht im Treppenhaus-Vorraum; je `q` Überlaufpersonen (aufgerundet) fällt ein Durchsatzplatz der Flucht dieser Etage aus:
Sperre = min(stairs, ceil(o / q)). Plätze und q sind ANNAHMEN. Quelle: Vormessung V2 (evak_v2_cpsat.py), auf Params umgestellt."""
from ortools.sat.python import cp_model


def feasible(mandatory, free, params, horizon, places=None, q=2, workers=8, time_limit=60.0):
    """(Status, Aufteilung): Status 'ja' / 'nein' / 'unbekannt'; die Aufteilung nennt die Freiwilligen je Etage."""
    floors = len(mandatory)
    total = sum(mandatory) + sum(free)
    E, K, d, C, tau_s, tau_e = params.cabins, params.capacity, params.halt, params.stairs, params.walk, params.lift_time
    T = horizon
    if total == 0:
        return "ja", (0,) * floors
    mdl = cp_model.CpModel()
    a = [mdl.NewIntVar(0, free[i], "a%d" % i) for i in range(floors)]
    nodes_in, nodes_out, arcs = {}, {}, []
    for f in range(0, floors + 1):
        for t in range(T + 1):
            for l in range(K + 1):
                nodes_in[(f, t, l)] = []
                nodes_out[(f, t, l)] = []

    def add_arc(u, v, kind, f, t, b=0):
        var = mdl.NewIntVar(0, E, "y%d" % len(arcs))
        arcs.append((u, v, var, kind, f, t, b))
        nodes_out[u].append(var)
        nodes_in[v].append(var)

    for f in range(0, floors + 1):
        for t in range(T + 1):
            for l in range(K + 1):
                u = (f, t, l)
                if t + 1 <= T:
                    add_arc(u, (f, t + 1, l), "wait", f, t)
                if t + tau_e <= T:
                    if f + 1 <= floors:
                        add_arc(u, (f + 1, t + tau_e, l), "up", f, t)
                    if f - 1 >= 0:
                        add_arc(u, (f - 1, t + tau_e, l), "down", f, t)
                if f >= 1 and t + d <= T:
                    for b in range(1, K - l + 1):
                        add_arc(u, (f, t + d, l + b), "board", f, t, b)
                if f == 0 and l >= 1:
                    add_arc(u, (0, min(t + d, T), 0), "unload", 0, t, l)
    ends = [mdl.NewIntVar(0, E, "end%d" % f) for f in range(0, floors + 1)]
    for (f, t, l), ins in nodes_in.items():
        outs = list(nodes_out[(f, t, l)])
        ins = list(ins)
        if (f, t, l) == (0, 0, 0):
            ins.append(E)
        if t == T and l == 0:
            outs.append(ends[f])
        mdl.Add(sum(ins) == sum(outs))
    mdl.Add(sum(ends) == E)

    e = [[mdl.NewIntVar(0, total, "e%d_%d" % (f, t)) for t in range(T + 1)] for f in range(floors)]
    board = [[[] for _ in range(T + 1)] for _ in range(floors)]
    for (u, v, var, kind, f, t, b) in arcs:
        if kind == "board":
            board[f - 1][t].append((var, b))
    for f in range(floors):
        mdl.Add(e[f][0] == mandatory[f] + a[f])
        for t in range(T):
            bt = sum(var * b for var, b in board[f][t])
            mdl.Add(e[f][t + 1] == e[f][t] - bt)
        bt = sum(var * b for var, b in board[f][T])
        mdl.Add(e[f][T] - bt == 0)

    w = [[mdl.NewIntVar(0, total, "w%d_%d" % (f, t)) for t in range(T + 1)] for f in range(floors)]
    x = [[mdl.NewIntVar(0, C, "x%d_%d" % (f, t)) for t in range(T + 1)] for f in range(floors)]
    for f in range(floors):
        mdl.Add(w[f][0] == free[f] - a[f])
        mdl.Add(w[f][T] == 0)
        for t in range(T + 1):
            mdl.Add(x[f][t] <= w[f][t])
            if t + tau_s > T:
                mdl.Add(x[f][t] == 0)
            if t < T:
                arr = x[f + 1][t + 1 - tau_s] if (f + 1 < floors and t + 1 - tau_s >= 0) else 0
                mdl.Add(w[f][t + 1] == w[f][t] - x[f][t] + arr)
    if places is not None:
        for f in range(floors):
            for t in range(T + 1):
                o = mdl.NewIntVar(0, total, "o%d_%d" % (f, t))
                mdl.AddMaxEquality(o, [0, e[f][t] - places])
                dv = mdl.NewIntVar(0, total, "dv%d_%d" % (f, t))
                mdl.AddDivisionEquality(dv, o + (q - 1), q)
                blk = mdl.NewIntVar(0, C, "blk%d_%d" % (f, t))
                mdl.AddMinEquality(blk, [C, dv])
                mdl.Add(x[f][t] + blk <= C)

    solver = cp_model.CpSolver()
    solver.parameters.num_workers = workers
    solver.parameters.max_time_in_seconds = time_limit
    st = solver.Solve(mdl)
    if st in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return "ja", tuple(solver.Value(v) for v in a)
    if st == cp_model.INFEASIBLE:
        return "nein", None
    return "unbekannt", None


def min_time(mandatory, free, params, lo=0, places=None, q=2, hi=80, **kw):
    """Kleinstes T mit zulässigem Plan (Suche aufwärts ab lo); (None, None), wenn ein Aufruf unentschieden bleibt."""
    for horizon in range(lo, hi + 1):
        status, a = feasible(mandatory, free, params, horizon, places, q, **kw)
        if status == "ja":
            return horizon, a
        if status == "unbekannt":
            return None, None
    return None, None
