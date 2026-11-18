"""Konstanten: Regler-Grenzen, feste Annahmen (alle ANNAHMEN, keine realen Gebäude), Farben und Presets.

Zähleinheiten überall: Zeitschritt (Räumungszeit), Person, Fahrt. Nie Laufzeit."""

# --- Regler (Seitenleiste); jede Stufe ist in der vorgerechneten Messreihe enthalten (data/evk_results.json)
FLOORS_MIN, FLOORS_MAX, DEFAULT_FLOORS = 2, 4, 3
CABINS_MIN, CABINS_MAX, DEFAULT_CABINS = 1, 2, 1          # exakter Aufzug nur für 1 und 2 Kabinen
CAPACITY_MIN, CAPACITY_MAX, DEFAULT_CAPACITY = 1, 4, 3    # Personen je Fahrt
HALT_MIN, HALT_MAX, DEFAULT_HALT = 1, 2, 1                # Zeitschritte je Halt (Laden und Entladen)
STAIRS_MIN, STAIRS_MAX, DEFAULT_STAIRS = 2, 3, 2          # Personen je Zeitschritt und Flucht, alle Treppenhäuser zusammen
SHARE_MIN, SHARE_MAX, SHARE_STEP, DEFAULT_SHARE = 0, 40, 5, 20   # Prozent Aufzugspflicht
SEED_MIN, SEED_MAX, DEFAULT_SEED = 1, 9999, 121

# --- feste Annahmen
WALK_TIME = 2        # Zeitschritte je Flucht (eine Etage Treppe)
LIFT_TIME = 1        # Zeitschritte je Etage im Aufzug
PERSONS_MIN, PERSONS_MAX = 3, 6   # Personen je Etage, aus dem Zufalls-Seed gezogen

# --- Messreihe
SWEEP_SEEDS = tuple(range(1, 31))                    # 30 feste Zufalls-Seeds: nie ein einzelner Seed als Befund
SHARES = tuple(range(SHARE_MIN, SHARE_MAX + 1, SHARE_STEP))
RESULTS_FILE = "data/evk_results.json"
WAIT_FILE = "data/evk_wait.json"

# --- Wartebereich (vorgerechnet, CP-SAT, nur Gebäude mit 3 Etagen, K = 3, Treppe 2, Halt 1)
WAIT_FLOORS, WAIT_CAPACITY, WAIT_STAIRS, WAIT_HALT = 3, 3, 2, 1
WAIT_SHARES = (20, 30, 40)
WAIT_PLACES = (-1, 2, 1, 0)       # -1 = unbegrenzt
WAIT_OVERFLOW = (1, 2, 4)         # Q: je Q Überlaufpersonen fällt ein Durchsatzplatz der Flucht dieser Etage aus

COLOR_STAIRS = "#4c78a8"
COLOR_LIFT = "#e07b39"
COLOR_FLOW = "#7a7a7a"
COLOR_EXACT = "#2F6B65"

def _preset(floors=DEFAULT_FLOORS, cabins=DEFAULT_CABINS, capacity=DEFAULT_CAPACITY, halt=DEFAULT_HALT, stairs=DEFAULT_STAIRS, share=DEFAULT_SHARE, seed=DEFAULT_SEED):
    return {"floors": floors, "cabins": cabins, "capacity": capacity, "halt": halt, "stairs": stairs, "share": share, "seed": seed}


# Zufalls-Seeds über tools/preset_search.py gesucht (ab 101, also außerhalb der Messreihen-Stichprobe 1 bis 30)
PRESETS = {
    "Standardfall (Voreinstellung)": _preset(seed=121),
    "Wenig Aufzugspflicht: Fluss reicht": _preset(share=5, seed=104),
    "Viel Aufzugspflicht, eine Kabine": _preset(floors=4, capacity=2, share=40, seed=127),
    "Zweite Kabine": _preset(floors=4, cabins=2, capacity=2, share=40, seed=127),
    "Nur freiwillig (Anteil 0)": _preset(share=0, seed=101),
    "Langer Halt, schnelle Treppe": _preset(halt=2, stairs=3, seed=105),
    "Ohne Bündeln (Kapazität 1)": _preset(capacity=1, seed=104),
}
PRESET_HELP = {
    "Standardfall (Voreinstellung)": "3 Etagen, 1 Kabine für 3 Personen, 20 % mit Aufzugspflicht.",
    "Wenig Aufzugspflicht: Fluss reicht": "3 Etagen, 1 Kabine, nur 5 % mit Aufzugspflicht.",
    "Viel Aufzugspflicht, eine Kabine": "4 Etagen, 1 Kabine für 2 Personen, 40 % mit Aufzugspflicht.",
    "Zweite Kabine": "Dasselbe Gebäude wie „Viel Aufzugspflicht“, aber mit 2 Kabinen.",
    "Nur freiwillig (Anteil 0)": "Niemand hat Aufzugspflicht: alle Gehenden dürfen frei wählen.",
    "Langer Halt, schnelle Treppe": "Halt 2 Zeitschritte statt 1, Treppe 3 Personen je Zeitschritt statt 2.",
    "Ohne Bündeln (Kapazität 1)": "Die Kabine fährt nur eine Person je Fahrt: nichts zu bündeln.",
}


# Annahmen-Text: dieselbe Fassung steht wörtlich in der README (tests/test_claims.py sucht den App-Text dort)
ASSUMPTIONS_MARKDOWN = """**Annahmen dieser Demo.** Alle Werte sind Annahmen eines Mini-Gebäudes, keine realen Gebäude und keine Brandschutzvorgaben. Zähleinheiten: Zeitschritt, Person, Fahrt.

| Annahme | Wert |
|---|---|
| Gebäude | 2 bis 4 Etagen über dem Ausgang, 3 bis 6 Personen je Etage (aus dem Zufalls-Seed), höchstens 24 Personen |
| Treppe | alle Treppenhäuser zusammen als eine Flucht je Etage: 2 oder 3 Personen je Zeitschritt, 2 Zeitschritte Gehzeit je Flucht, Staus dort, wo sie auftreten, keine Dichteeffekte |
| Aufzug | 1 oder 2 Kabinen starten am Ausgang, 1 Zeitschritt je Etage, Halt von 1 oder 2 Zeitschritten (Laden und Entladen), 1 bis 4 Personen je Fahrt, eine Fahrt darf an beliebig vielen Etagen halten |
| Aufzugspflicht | Anteil 0 bis 40 % in 5-%-Schritten; diese Menschen nutzen nur den Aufzug; die Mengen sind über den Anteil geschachtelt (wer bei 10 % Aufzugspflicht hat, hat sie auch bei 20 %) |
| Wahl der Übrigen | frei zwischen Treppe und Aufzug, einmal bei Zeitschritt 0: ein Plan mit vollständiger Kenntnis, kein Verhalten von Menschen |
| Zeit | alle Personen sind bei Zeitschritt 0 bereit (keine Reaktionszeit, kein Weg zum Aufzug); Räumungszeit = Zeitschritt, in dem die letzte Person den Ausgang erreicht |
| Wartebereich | nur in der vorgerechneten Tabelle (CP-SAT): 3 Etagen, Kapazität 3, Treppe 2, Halt 1; je Etage W Warteplätze, der Überlauf steht im Treppenhaus, je Q Überlaufpersonen fällt ein Durchsatzplatz der Flucht dieser Etage aus |
| Nicht modelliert | Begleitpersonen, Tragestuhl, Ausfall des Aufzugs, Brandschutz und Rechtslage; im Ernstfall ist ein Aufzug oft gerade nicht zulässig, das Modell sagt dazu nichts |
"""
