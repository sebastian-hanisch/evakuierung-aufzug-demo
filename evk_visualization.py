"""Plotly-Abbildungen. Alle Achsen sind gesperrt (fixedrange), damit Touch-Geräte beim Scrollen nicht am Diagramm hängen bleiben.
Beschriftungen sind Annotationen oder Text, nie lineare Achsen für Namen."""

import plotly.graph_objects as go

import evk_constants as C

FILL_FLOOR = "rgba(128,128,128,0.10)"


def lock_axes(fig):
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    return fig


def _base(fig, height=340):
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", y=-0.22), plot_bgcolor="rgba(0,0,0,0)")
    return lock_axes(fig)


def _persons(label, xs, ys, color, symbol, hover, name_for_legend):
    return go.Scatter(x=xs, y=ys, mode="markers", name=name_for_legend, marker=dict(size=17, color=color, symbol=symbol, line=dict(width=1.5, color="white")),
                      hovertemplate=hover + "<extra></extra>", legendgroup=label, showlegend=bool(xs))


def build_building(mandatory, free, split):
    """Gebäudeschema: Etagen als Bänder, links die Treppe, rechts der Aufzugsschacht; je Etage die Menschen mit Aufzugspflicht (Quadrat), Gehende im Aufzug
    (Kreis, orange) und Gehende auf der Treppe (Kreis, blau) laut optimalem Plan."""
    floors = len(mandatory)
    width = 10.0
    fig = go.Figure()
    fig.add_shape(type="rect", x0=0.1, x1=1.5, y0=-0.5, y1=floors + 0.5, fillcolor="rgba(76,120,168,0.10)", line=dict(width=0))
    fig.add_shape(type="rect", x0=8.4, x1=9.8, y0=-0.5, y1=floors + 0.5, fillcolor="rgba(224,123,57,0.12)", line=dict(width=0))
    for f in range(0, floors + 1):
        fig.add_shape(type="rect", x0=0.1, x1=9.8, y0=f - 0.45, y1=f + 0.45, fillcolor=FILL_FLOOR, line=dict(width=0))
        fig.add_annotation(x=1.6, y=f, text="Ausgang" if f == 0 else f"Etage {f}", showarrow=False, xanchor="left", font=dict(size=12))
    fig.add_annotation(x=0.8, y=floors + 0.75, text="Treppe", showarrow=False, font=dict(size=12, color=C.COLOR_STAIRS))
    fig.add_annotation(x=9.1, y=floors + 0.75, text="Aufzug", showarrow=False, font=dict(size=12, color=C.COLOR_LIFT))
    groups = {"mandatory": ([], []), "volunteer": ([], []), "walker": ([], [])}
    for f in range(1, floors + 1):
        kinds = ["mandatory"] * mandatory[f - 1] + ["volunteer"] * split[f - 1] + ["walker"] * (free[f - 1] - split[f - 1])
        for i, kind in enumerate(kinds):
            groups[kind][0].append(3.9 + i * 0.72)
            groups[kind][1].append(f)
    fig.add_trace(_persons("mandatory", *groups["mandatory"], C.COLOR_LIFT, "square", "Aufzugspflicht (Etage %{y})", "Aufzugspflicht"))
    fig.add_trace(_persons("volunteer", *groups["volunteer"], C.COLOR_LIFT, "circle", "Gehende im Aufzug (Etage %{y})", "Gehende, die den Aufzug nehmen"))
    fig.add_trace(_persons("walker", *groups["walker"], C.COLOR_STAIRS, "circle", "Gehende auf der Treppe (Etage %{y})", "Gehende auf der Treppe"))
    fig.update_xaxes(range=[0, width], visible=False)
    fig.update_yaxes(range=[-0.7, floors + 1.1], visible=False)
    return _base(fig, height=90 * (floors + 1) + 90)


def build_curve(curve, exact):
    """Menschen draußen über die Zeit: Treppengruppe, Aufzugsgruppe, zusammen. Die Zeitachse endet bei T* (feste Achse)."""
    xs = list(range(len(curve["total"])))
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=xs, y=curve["stairs"], mode="lines", line=dict(color=C.COLOR_STAIRS, width=2, shape="hv"), name="Treppe",
                             hovertemplate="Zeitschritt %{x}: %{y} draußen<extra>Treppe</extra>"))
    fig.add_trace(go.Scatter(x=xs, y=curve["lift"], mode="lines", line=dict(color=C.COLOR_LIFT, width=2, shape="hv"), name="Aufzug",
                             hovertemplate="Zeitschritt %{x}: %{y} draußen<extra>Aufzug</extra>"))
    fig.add_trace(go.Scatter(x=xs, y=curve["total"], mode="lines", line=dict(color=C.COLOR_EXACT, width=3, shape="hv"), name="zusammen",
                             hovertemplate="Zeitschritt %{x}: %{y} draußen<extra>zusammen</extra>"))
    fig.update_xaxes(title_text="Zeitschritt", range=[0, max(exact, 1)])
    fig.update_yaxes(title_text="Menschen draußen")
    return _base(fig)


def build_trips(cabins, exact):
    """Fahrten des optimalen Plans als Zeitstrahl je Kabine: Balken = Kabine belegt (hoch, Halte, runter, Entladen); Beschriftung = Personen je Etage."""
    fig = go.Figure()
    names = [f"Kabine {i + 1}" for i in range(len(cabins))]
    for i, trips in enumerate(cabins):
        for trip in trips:
            label = ", ".join(f"E{f + 1}: {x}" for f, x in enumerate(trip.load) if x)
            fig.add_trace(go.Bar(x=[trip.end - trip.start], y=[names[i]], base=[trip.start], orientation="h", marker=dict(color=C.COLOR_LIFT, line=dict(color="white", width=2)),
                                 text=[label], textposition="inside", insidetextanchor="middle", showlegend=False,
                                 hovertemplate=f"{names[i]}: Start {trip.start}, Ankunft am Ausgang {trip.arrival}, frei ab {trip.end}<br>{label}<extra></extra>"))
    fig.update_xaxes(title_text="Zeitschritt", range=[0, max(exact, 1) + 1])
    fig.update_yaxes(categoryorder="array", categoryarray=names[::-1])
    fig.update_layout(barmode="overlay")
    return _base(fig, height=110 + 70 * len(cabins))


def build_lines(xs, series, ytitle, xtitle="Anteil mit Aufzugspflicht (%)", height=340):
    """Linien über dem Anteil. series = [(Name, Werte, Farbe, gestrichelt?), ...]."""
    fig = go.Figure()
    for name, ys, color, dash in series:
        fig.add_trace(go.Scatter(x=list(xs), y=[float(y) for y in ys], mode="lines+markers", name=name, line=dict(color=color, width=3, dash="dash" if dash else "solid"),
                                 hovertemplate=name + ": %{y:.2f}<extra></extra>"))
    fig.update_xaxes(title_text=xtitle)
    fig.update_yaxes(title_text=ytitle)
    return _base(fig, height)


def build_wait(places, effects, seeds_affected):
    """Wirkung des Wartebereichs (mittlere Verlängerung der Räumung gegen unbegrenzte Plätze) je Zahl der Warteplätze; Text = betroffene Zufalls-Seeds."""
    labels = ["unbegrenzt" if p < 0 else ("1 Platz" if p == 1 else f"{p} Plätze") for p in places]
    fig = go.Figure(go.Bar(x=labels, y=effects, marker_color=C.COLOR_LIFT, text=[f"{k} von 30" for k in seeds_affected], textposition="outside",
                           hovertemplate="%{x}: %{y:.2f} Zeitschritte<extra></extra>"))
    fig.update_yaxes(title_text="Verlängerung (Zeitschritte)", rangemode="tozero")
    fig.update_xaxes(title_text="Warteplätze je Etage")
    return _base(fig, 300)
