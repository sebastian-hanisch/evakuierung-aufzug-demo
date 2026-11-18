"""Evakuierung mit Aufzug: wo das Flussmodell endet - interaktive Fall-Demo
Sebastian Hanisch - Operations Research und Machine Learning

Treppe als Fluss, Aufzug als Fahrten mit Kapazität (Bündeln plus Maschinenbelegung), Wahl der Gehenden als Entscheidung; Mini-Gebäude, alle Werte Annahmen.
Aufbau nach DEMO-PLAYBOOK §2: Presets in der Seitenleiste, Kernfragen vor dem Expander, exakter Plan als Tab.

Lauffähig mit: streamlit run app.py
"""

import streamlit as st

import evk_algorithm as A
import evk_constants as C
import evk_evaluation as ev
import evk_results as R
import evk_stories
import evk_visualization as V
from evk_layout import dunkles_design, kopf_css
from evk_pdf_export import generate_report_pdf
from evk_presets import (
    aktives_preset,
    bounds,
    init_session_state_defaults,
    load_permalink_settings,
    randomize_seed,
    sidebar_presets,
    sync_query_params,
)

st.set_page_config(page_title="Evakuierung mit Aufzug – Sebastian Hanisch", layout="wide")


@st.cache_data(show_spinner="Rechne den exakten Plan …")
def _analysis(settings):
    return ev.analyse(settings)


@st.cache_data(show_spinner=False)
def _rule_counts():
    return R.rule_counts(R.all_cells())


def _show(verdict):
    kind, text = verdict
    getattr(st, kind)(text)


# Fester Kopf: nur der Titel bleibt beim Scrollen oben (Stylesheet in evk_layout.py).
st.html(kopf_css(dunkles_design()))
with st.container(key="kopf"):
    st.title("🛗 Evakuierung mit Aufzug: wo das Flussmodell endet")
st.markdown(
    """
Ein Gebäude wird geräumt. Die **Treppe** lässt sich als **Fluss** rechnen (Durchsatz je Zeitschritt); der **Aufzug** nicht ohne Weiteres: eine Kabinenfahrt hat eine **Kapazität je Fahrt**, hält an
mehreren Etagen und dauert nach der höchsten Etage. **Menschen mit eingeschränkter Mobilität** (Aufzugspflicht) dürfen nur den Aufzug nehmen, die übrigen wählen frei.
Die Demo vergleicht das **reine Flussmodell**, den **exakten Plan** (Aufzählung plus Pareto-DP) und den Fluss mit **Maschinenschranke** und zeigt, wo das Flussmodell endet.
Mini-Gebäude, alle Werte sind Annahmen, keine Aussage über reale Gebäude, Brandschutz oder reale Zeiten.

Weiter unten: vier **Kernfragen**, der Expander **🔧 Wie wir das erreichen – vollständiger Methodenvergleich** und der Expander **📐 Mathematische Formulierung**.
"""
)

# erklaerseite:einfach:start (erzeugt von tools/set_demo_explainer.py (Website-Repo) aus tools/content/explainers/evakuierung-aufzug-erklaert.json, nicht von Hand ändern)
with st.expander("💬 In einfachen Worten"):
    st.markdown(
        """
Ein kleines Gebäude mit zwei bis vier Etagen wird geräumt. Die **Treppe** lässt je Zeitschritt nur eine bestimmte Zahl von Menschen durch, das lässt sich als **Fluss** rechnen. Der **Aufzug** hat Kabinen mit begrenzter Platzzahl, hält an mehreren Etagen, und eine Fahrt dauert nach der höchsten Etage. **Menschen mit eingeschränkter Mobilität** (Aufzugspflicht) dürfen nur den Aufzug nehmen, die übrigen wählen frei. Die Demo vergleicht drei Rechnungen: das reine Flussmodell, das jeder Etage alle Kabinen für sich gibt, den exakten Plan und den Fluss mit einer Schranke aus der Aufzugszeit der Pflichtgruppe. So zeigt sie, wo das einfache Modell zu kurz rechnet und was den Fehler schließt. Alle Werte sind erfundene Annahmen eines Mini-Gebäudes. Die Ergebnisse sagen nichts über reale Gebäude, Brandschutz oder reale Zeiten.

[Ausführlich und verständlich erklärt, mit Fachteil](https://sebastianhanisch.net/evakuierung-aufzug-erklaert.html)
        """
    )
# erklaerseite:einfach:end

st.caption("🔗 Die Adresszeile oben spiegelt Ihre aktuelle Konfiguration wider – einfach kopieren, um ein Szenario zu teilen.")

load_permalink_settings()
init_session_state_defaults()

with st.sidebar:
    sidebar_presets()  # Schnellstart oben, das aktive Preset ist hervorgehoben
    st.header("⚙️ Einstellungen")
    st.markdown("**Gebäude**")
    floors = st.slider("Etagen", *bounds("floors_slider"), key="floors_slider", help="Etagen über dem Ausgang; je Etage 3 bis 6 Personen, gezogen aus dem Zufalls-Seed.")
    share = st.slider("Anteil mit Aufzugspflicht (%)", *bounds("share_slider"), step=C.SHARE_STEP, key="share_slider",
                      help="Diese Menschen nutzen nur den Aufzug. Je Person eine feste Zufallszahl: die Mengen sind über den Anteil geschachtelt.")
    seed = st.number_input("Zufalls-Seed des Gebäudes", *bounds("seed_input"), key="seed_input", step=1, help="Bestimmt Personen je Etage und wer Aufzugspflicht hat.")
    st.markdown("**Aufzug**")
    cabins = st.slider("Kabinen", *bounds("cabins_slider"), key="cabins_slider", help="Exakt gerechnet wird für 1 und 2 Kabinen.")
    capacity = st.slider("Kapazität je Fahrt (Personen)", *bounds("capacity_slider"), key="capacity_slider", help="So viele Personen fährt eine Kabine auf einmal.")
    halt = st.slider("Halt je Etage (Zeitschritte)", *bounds("halt_slider"), key="halt_slider", help="Laden an jeder angefahrenen Etage und Entladen am Ausgang.")
    st.markdown("**Treppe**")
    stairs = st.slider("Durchsatz je Flucht (Personen je Zeitschritt)", *bounds("stairs_slider"), key="stairs_slider",
                       help="Alle Treppenhäuser zusammen; die Gehzeit je Flucht ist fest (2 Zeitschritte).")
    st.button("🎲 Neues Gebäude generieren", width="stretch", on_click=randomize_seed)

sync_query_params({"floors_slider": int(floors), "cabins_slider": int(cabins), "capacity_slider": int(capacity), "halt_slider": int(halt), "stairs_slider": int(stairs),
                   "share_slider": int(share), "seed_input": int(seed)})

settings = ev.Settings(int(floors), int(cabins), int(capacity), int(halt), int(stairs), int(share), int(seed))
a = _analysis(settings)
active = aktives_preset()
if active and active in evk_stories.STORIES:
    st.info(f"**{active}:** {evk_stories.STORIES[active]}")

# --- Ergebnis ------------------------------------------------------------------------------------------------------------------------------

st.markdown("## 🎯 Ergebnis")
st.caption(f"Gebäude: {a.building.total} Menschen auf {settings.floors} Etagen ({', '.join(str(p) for p in a.building.persons)} je Etage von unten), davon {a.n_mandatory} mit Aufzugspflicht.")
m1, m2, m3, m4 = st.columns(4)
# Deltas immer „mein Wert minus Referenz“ (Referenz = exakte Räumungszeit); die Farbe regelt der Zusatz, nie ein Vorzeichen von Hand (DEMO-PLAYBOOK §2).
m1.metric("Räumungszeit exakt (T*)", f"{a.exact} Zeitschritte", delta="Referenz", delta_color="off")
m2.metric("Reines Flussmodell", f"{a.flow_takt} Zeitschritte", delta=f"{a.flow_takt - a.exact:+d} gegen exakt", delta_color="off")
m3.metric("Fluss plus Maschinenschranke", f"{a.k1} Zeitschritte", delta=f"{a.k1 - a.exact:+d} gegen exakt", delta_color="off")
m4.metric("Alle Gehenden auf der Treppe", f"{a.joint.time_stairs_only} Zeitschritte", delta=f"{a.joint.time_stairs_only - a.exact:+d} gegen exakt", delta_color="off")
col_a, col_b = st.columns(2)
with col_a:
    st.markdown("**Gebäude und Plan** (optimale Aufteilung mit den wenigsten Freiwilligen)")
    st.plotly_chart(V.build_building(a.mandatory, a.free, a.joint.split), width="stretch", key="main_building")
    st.caption("Quadrat: Aufzugspflicht. Kreis orange: Gehende, die im Plan den Aufzug nehmen. Kreis blau: Gehende auf der Treppe.")
with col_b:
    st.markdown("**Menschen draußen über die Zeit**")
    st.plotly_chart(V.build_curve(ev.evacuation_curve(a), a.exact), width="stretch", key="main_curve")
    st.caption(f"Die Räumung endet bei Zeitschritt {a.exact} (T*): {a.n_lift} Menschen fahren im Aufzug, {sum(a.free) - sum(a.joint.split)} gehen über die Treppe.")

trip_rows = [(f"Kabine {i + 1}", t.start, t.arrival, t.end, ", ".join(f"Etage {f + 1}: {x}" for f, x in enumerate(t.load) if x)) for i, cab in enumerate(a.cabins_plan) for t in cab]
summary = [
    f"Gebäude: {settings.floors} Etagen, Personen je Etage {', '.join(str(p) for p in a.building.persons)}, Anteil mit Aufzugspflicht {settings.share} %, Zufalls-Seed {settings.seed}.",
    f"Aufzug: {settings.cabins} Kabine(n), {settings.capacity} Personen je Fahrt, Halt {settings.halt} Zeitschritt(e); Treppe: {settings.stairs} Personen je Zeitschritt und Flucht.",
    f"Räumungszeit exakt (T*): {a.exact} Zeitschritte; reines Flussmodell: {a.flow_takt}; Fluss plus Maschinenschranke: {a.k1}; alle Gehenden auf der Treppe: {a.joint.time_stairs_only}.",
    f"Freiwillige Aufzugsnutzer in einer optimalen Aufteilung: mindestens {a.joint.a_min}, höchstens {a.joint.a_max} (optimale Aufteilungen: {a.joint.n_optimal}).",
    "Alle Werte sind Annahmen eines Mini-Gebäudes, keine Aussage über reale Gebäude.",
]
st.download_button("📄 Bericht als PDF", generate_report_pdf("Evakuierung mit Aufzug", summary, trip_rows), file_name="evakuierung-aufzug.pdf", mime="application/pdf")

# --- Kernfragen ----------------------------------------------------------------------------------------------------------------------------

st.markdown("## ❓ Kernfrage 1: Wie weit liegt der Fluss unter der exakten Räumungszeit, und was schließt die Lücke?")
_show(ev.verdict_flow_error(a.exact, a.flow_takt))
other = 2 if settings.cabins == 1 else 1
cell_here, cell_other = settings.cell, (settings.floors, other, settings.capacity, settings.stairs, settings.halt)
shares = list(C.SHARES)
st.plotly_chart(
    V.build_lines(shares, [
        (f"Fluss, {settings.cabins} Kabine{'n' if settings.cabins > 1 else ''}", R.error_by_share(cell_here), C.COLOR_FLOW, False),
        (f"Fluss, {other} Kabine{'n' if other > 1 else ''}", R.error_by_share(cell_other), C.COLOR_FLOW, True),
        (f"Fluss plus Schranke, {settings.cabins} Kabine{'n' if settings.cabins > 1 else ''}", R.error_by_share(cell_here, "k1"), C.COLOR_EXACT, False),
    ], "Fehler: T* minus Verfahren (Zeitschritte)"), width="stretch", key="chart_error")
st.caption(f"Vorgerechnet (30 feste Zufalls-Seeds, Mittel): Fehler des Verfahrens gegen die exakte Räumungszeit über den Anteil, für {settings.floors} Etagen, Kapazität {settings.capacity}, "
           f"Halt {settings.halt}, Treppe {settings.stairs}. Das Gebäude oben ist dagegen eine Einzelinstanz.")

st.markdown("## ❓ Kernfrage 2: Wann reicht der Fluss?")
counts = _rule_counts()
_show(ev.verdict_rule(a.rule_holds, a.barrier, a.flow_takt, a.exact, (counts["true_hit"], counts["true"]), (counts["false_hit"], counts["false"])))
st.dataframe(
    [{"Faustregel": "gilt (Pflichtgruppe allein ≤ Fluss)", "Zellen": counts["true"], "Fehler ≤ 1": counts["true_hit"], "Fehler = 0": counts["true_exact"], "größter Fehler": counts["true_max_error"]},
     {"Faustregel": "gilt nicht", "Zellen": counts["false"], "Fehler ≤ 1": counts["false_hit"], "Fehler = 0": counts["false_exact"], "größter Fehler": counts["false_max_error"]}],
    hide_index=True, width="stretch")
st.caption("Zellen = Zufalls-Seed × Anteil von 5 bis 40 % × Reglerstufe (alle 96 Stufen-Kombinationen der Seitenleiste außer der Wahl des Zufalls-Seeds); Fehler = T* minus Fluss in Zeitschritten.")

st.markdown("## ❓ Kernfrage 3: Was bringt freiwillige Aufzugsnutzung, und wo kippt die Räumung?")
_show(ev.verdict_volunteers(a.exact, a.joint.time_stairs_only, a.joint.a_min, a.joint.a_max, a.n_walkers, a.barrier))
tip_here, tip_other = R.tipping_median(cell_here), R.tipping_median(cell_other)
_show(ev.verdict_tipping(tip_here, R.tipping_count(cell_here), R.SEEDS, settings.cabins, tip_other, R.tipping_count(cell_other)))
st.plotly_chart(
    V.build_lines(shares, [
        ("exakt (T*)", R.mean_by_share(cell_here, "exact"), C.COLOR_EXACT, False),
        ("Fluss", R.mean_by_share(cell_here, "flow_takt"), C.COLOR_FLOW, False),
        ("Pflichtgruppe allein im Aufzug", R.mean_by_share(cell_here, "barrier"), C.COLOR_LIFT, True),
        ("alle Gehenden auf der Treppe", R.mean_by_share(cell_here, "stairs_all_free"), C.COLOR_STAIRS, True),
    ], "Räumungszeit (Zeitschritte, Mittel)"), width="stretch", key="chart_tipping")
st.caption("Vorgerechnet, Mittel über 30 feste Zufalls-Seeds. Kipppunkt = kleinster Anteil, bei dem T* größer ist als bei Anteil 0; „über 40 %“ heißt: im Median nicht bis 40 %.")

st.markdown("## ❓ Kernfrage 4: Ist der Wartebereich ein Hebel?")
st.caption("Nur vorgerechnet (CP-SAT, Mittel über 30 Zufalls-Seeds): 3 Etagen, Kapazität 3, Halt 1, Treppe 2. Aus der Seitenleiste wirkt hier nur die Zahl der Kabinen.")
w1, w2 = st.columns(2)
wait_share = w1.radio("Anteil mit Aufzugspflicht (%)", C.WAIT_SHARES, index=0, horizontal=True, key="wait_share")
wait_q = w2.radio("Überlauf Q (Personen je ausgefallenem Durchsatzplatz)", C.WAIT_OVERFLOW, index=1, horizontal=True, key="wait_q")
wait_places = st.radio("Warteplätze je Etage", C.WAIT_PLACES, index=3, horizontal=True, key="wait_places", format_func=lambda p: "unbegrenzt" if p < 0 else str(p))
effects = [R.wait_effect(settings.cabins, wait_share, p, 0 if p < 0 else wait_q) for p in C.WAIT_PLACES]
chosen = effects[C.WAIT_PLACES.index(wait_places)]
second = (R.wait_effect(1, wait_share, wait_places, 0 if wait_places < 0 else wait_q)["mean_time"] - R.wait_effect(2, wait_share, wait_places, 0 if wait_places < 0 else wait_q)["mean_time"])
_show(ev.verdict_waiting(chosen["mean_effect"], chosen["seeds_affected"], chosen["seeds"], second, wait_places))
st.plotly_chart(V.build_wait(list(C.WAIT_PLACES), [e["mean_effect"] for e in effects], [e["seeds_affected"] for e in effects]), width="stretch", key="chart_wait")
st.caption("Wirkung = mittlere Verlängerung der Räumungszeit gegen unbegrenzte Warteplätze, gepaart über die Zufalls-Seeds; beschriftet: Zahl der Zufalls-Seeds mit Wirkung. W und Q sind Annahmen.")

st.markdown("---")

# --- Methodenvergleich ---------------------------------------------------------------------------------------------------------------------

with st.expander("🔧 Wie wir das erreichen – vollständiger Methodenvergleich"):
    tab_methods, tab_exact, tab_assumptions = st.tabs(["Verfahren", "🧮 Exakt (Aufzählung + Pareto-DP)", "Annahmen"])
    with tab_methods:
        rows = [
            ("Reines Flussmodell (Takt)", a.flow_takt, "Zeitnetz, Aufzug als Kante mit Kapazität Kabinen × Kapazität zu den Abfahrtszeiten; jede Etage hat alle Kabinen für sich (untere Schranke)."),
            ("Reines Flussmodell (Rate)", a.flow_rate, "Aufzug als Kante mit gerundetem Durchsatz je Zeitschritt, wie man ihn im Zeitfluss anlegen würde; kann über und unter T* liegen."),
            ("Fluss plus Maschinenschranke", a.k1, "Maximum aus Fluss und der Aufzugszeit der Pflichtgruppe allein (exakt, Mehrfachhalt): eine untere Schranke."),
            ("Fluss plus Schranke, Einzelhalt (exakt)", a.single_exact, "Dieselbe Idee, aber jede Fahrt hält nur an einer Etage: überschätzt im Mittel (nicht in allen Gebäuden), vermutlich weil die Kabinen schlechter gefüllt werden; bei Kapazität 1 gleich Fluss plus Schranke."),
            ("Fluss plus Schranke, Einzelhalt (LPT)", a.single_lpt, "Einzelhalt mit der Listenregel höchste Etage zuerst."),
            ("Exakt (Aufzählung + Pareto-DP)", a.exact, "Aufteilung der Gehenden aufgezählt, Treppe simuliert, Aufzug als Menge von Fahrten mit Pareto-DP."),
            ("Alle Gehenden auf der Treppe", a.joint.time_stairs_only, "Keine freie Wahl: nur die Pflichtgruppe fährt im Aufzug."),
        ]
        st.dataframe([{"Verfahren": n, "Zeitschritte": v, "T* minus Wert": a.exact - v, "Hinweis": t} for n, v, t in rows], hide_index=True, width="stretch")
        st.caption("Gebäude oben (eine Einzelinstanz); T* minus Wert positiv heißt: das Verfahren unterschätzt, negativ: es überschätzt.")
    with tab_exact:
        st.markdown(
            "Der exakte Plan zählt alle Aufteilungen der Gehenden auf; je Aufteilung gilt die Treppenzeit der Simulation und die Aufzugszeit des Pareto-DP über Fahrtenmengen "
            "(eine Fahrt ist ein Auftrag, dessen Dauer von seiner Zusammensetzung abhängt). Er braucht hier in der Regel deutlich unter einer Sekunde (Worst Case mit 24 Menschen und Anteil 0: 0,81 s auf einem Entwicklungsrechner), darum ohne Rechenknopf."
        )
        n_splits = 1
        for g in a.free:
            n_splits *= g + 1
        e1, e2, e3 = st.columns(3)
        e1.metric("Aufteilungen aufgezählt", n_splits)
        e2.metric("davon optimal", a.joint.n_optimal)
        e3.metric("Freiwillige (kleinste bis größte Zahl)", f"{a.joint.a_min} bis {a.joint.a_max}")
        st.markdown("**Fahrten des Plans** (Balken: Kabine belegt; Beschriftung: Personen je Etage)")
        if trip_rows:
            st.plotly_chart(V.build_trips(a.cabins_plan, a.exact), width="stretch", key="chart_trips")
            st.dataframe([{"Kabine": c, "Start": s, "Ankunft am Ausgang": ar, "frei ab": en, "Personen": p} for c, s, ar, en, p in trip_rows], hide_index=True, width="stretch")
        else:
            st.info("Niemand fährt im Aufzug: keine Pflichtperson und keine Freiwilligen.")
        riders = tuple(m + s for m, s in zip(a.mandatory, a.joint.split))
        problems, plan_time = A.evaluate_plan(a.mandatory, a.free, a.joint.split, [list(c) for c in a.cabins_plan], settings.params)
        if problems or plan_time != a.exact:
            st.error("Der Prüfer meldet den Plan als unzulässig: " + "; ".join(problems))
        else:
            st.success(f"Prüfer: der Plan ist zulässig (Kapazität, jede Person genau einmal, Dauer der Fahrten) und endet bei Zeitschritt {plan_time}; im Aufzug fahren {sum(riders)} Menschen.")
    with tab_assumptions:
        st.markdown(C.ASSUMPTIONS_MARKDOWN)

with st.expander("📐 Mathematische Formulierung"):
    # erklaerseite:lesehilfe:start (erzeugt von tools/set_demo_explainer.py (Website-Repo) aus tools/content/explainers/evakuierung-aufzug-erklaert.json, nicht von Hand ändern)
    st.markdown(
        r"""
**Lesehilfe.** Gegeben sind ein Gebäude mit Etagen $f = 1, \dots, F$, je Etage $n_f$ Menschen mit Aufzugspflicht und $g_f$ Gehende; Treppe und Aufzug mit den Werten der Seitenleiste. Gesucht ist die Aufteilung der Gehenden und die Fahrten, bei denen die letzte Person möglichst früh draußen ist.

| Symbol | Bedeutung |
|---|---|
| $F$, $f$ | Zahl der Etagen, Etage ($f = 1$ ist die unterste über dem Ausgang) |
| $n_f$, $g_f$ | Menschen mit Aufzugspflicht, Gehende auf Etage $f$ |
| $a_f$ | Gehende auf Etage $f$, die den Aufzug nehmen ($0 \le a_f \le g_f$) |
| $C$, $\tau_s$ | Durchsatz der Treppe je Flucht und Zeitschritt, Gehzeit je Flucht |
| $E$, $K$, $\tau_e$, $d$ | Kabinen, Kapazität je Fahrt, Zeit je Etage im Aufzug, Halt |
| $x_{f,t}$, $w_{f,t}$ | Personen, die im Zeitschritt $t$ von Etage $f$ die Flucht nach unten antreten, Personen, die dort zu Beginn von $t$ auf der Treppe warten |
| $y_{f,j}$ | Personen von Etage $f$ in Fahrt $j$ ($j = 1, \dots, J$) |
| $H_j$, $s_j$, $D_j$ | höchste Etage mit Personen in Fahrt $j$, Zahl der Etagen mit Personen, Dauer, die die Fahrt die Kabine belegt |
| $z_{j,e}$ | 1, wenn Fahrt $j$ von Kabine $e$ gefahren wird |
| $T$ | Räumungszeit: Zeitschritt, in dem die letzte Person den Ausgang erreicht |

[Schritt für Schritt erklärt, mit Herleitung und Literatur](https://sebastianhanisch.net/evakuierung-aufzug-erklaert.html#fachleute)
        """
    )
    # erklaerseite:lesehilfe:end
    st.markdown(
        """
**Lesehilfe.** *Gegeben:* ein Gebäude mit Etagen $f = 1, \\dots, F$, je Etage $n_f$ Menschen mit Aufzugspflicht und $g_f$ Gehende; Treppe und Aufzug mit den Werten der Seitenleiste.
*Gesucht:* die Aufteilung der Gehenden und die Fahrten, bei denen die letzte Person möglichst früh draußen ist.

| Symbol | Bedeutung |
|---|---|
| $F$, $f$ | Zahl der Etagen, Etage ($f = 1$ ist die unterste über dem Ausgang) |
| $n_f$, $g_f$ | Menschen mit Aufzugspflicht, Gehende auf Etage $f$ |
| $a_f$ | Gehende auf Etage $f$, die den Aufzug nehmen ($0 \\le a_f \\le g_f$) |
| $C$, $\\tau_s$ | Durchsatz der Treppe je Flucht und Zeitschritt, Gehzeit je Flucht |
| $E$, $K$, $\\tau_e$, $d$ | Kabinen, Kapazität je Fahrt, Zeit je Etage im Aufzug, Halt |
| $x_{f,t}$, $w_{f,t}$ | Personen, die im Zeitschritt $t$ von Etage $f$ die Flucht nach unten antreten, Personen, die dort zu Beginn von $t$ auf der Treppe warten |
| $y_{f,j}$ | Personen von Etage $f$ in Fahrt $j$ ($j = 1, \\dots, J$) |
| $H_j$, $s_j$, $D_j$ | höchste Etage mit Personen in Fahrt $j$, Zahl der Etagen mit Personen, Dauer, die die Fahrt die Kabine belegt |
| $z_{j,e}$ | 1, wenn Fahrt $j$ von Kabine $e$ gefahren wird |
| $T$ | Räumungszeit: Zeitschritt, in dem die letzte Person den Ausgang erreicht |

Treppe (Fluss im Zeitnetz, Ankunft am Ausgang nach $\\tau_s$ Zeitschritten):

$$w_{f,0} = g_f - a_f, \\qquad w_{f,t+1} = w_{f,t} - x_{f,t} + x_{f+1,\\,t+1-\\tau_s}$$

$$0 \\le x_{f,t} \\le \\min(C,\\, w_{f,t}), \\qquad x_{f,t} = 0 \\text{ für } t > T - \\tau_s, \\qquad w_{f,T} = 0 \\qquad (x_{F+1,\\cdot} = 0)$$

Aufzug (Fahrten bündeln, Kabinen belegen):

$$\\sum_{j} y_{f,j} = n_f + a_f, \\qquad y_{f,j} \\in \\mathbb{N}_0$$

$$\\sum_{f} y_{f,j} \\le K$$

$$H_j = \\max\\{f : y_{f,j} > 0\\}, \\qquad s_j = |\\{f : y_{f,j} > 0\\}|$$

$$D_j = 2\\,\\tau_e H_j + (s_j + 1)\\,d$$

$$\\sum_{e} z_{j,e} = 1$$

$$\\sum_{j} D_j\\, z_{j,e} - d \\le T \\quad \\text{für jede Kabine } e \\text{ mit mindestens einer Fahrt}$$

Ziel: $\\min T$ über $a$, $y$, $z$ und die Treppenflüsse. Die Dauer $D_j$ hängt von der Zusammensetzung der Fahrt ab (höchste Etage, Zahl der Halte): eine Kabinenfahrt ist deshalb keine Kante mit fester Kapazität
je Zeitschritt, sondern ein Auftrag, dessen Länge man durch das Bündeln selbst bestimmt. Das reine Flussmodell ersetzt diesen Teil durch Kanten und lässt jede Etage alle Kabinen für sich haben.
Das Wartebereich-Modell (nur in der Messreihe, CP-SAT) ergänzt Sperren der Treppe und steht nicht in diesen Formeln.
"""
    )

st.markdown("---")
st.caption(
    "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
    "Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). "
    "Mehr zu den Demos: [Interaktive Demos](https://sebastianhanisch.net/demos.html)."
)
