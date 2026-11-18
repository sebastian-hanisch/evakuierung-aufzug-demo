# Evakuierung mit Aufzug: wo das Flussmodell endet – Streamlit-Demo

<!-- TODO nach dem Deploy: direkt hierher den Live-Link setzen (Leerzeile davor und danach):
**[→ Demo live ausprobieren](https://sebastianhanisch-evakuierung-aufzug-demo.streamlit.app/)** -->

Fall-Demo für die Website „Sebastian Hanisch – Operations Research und Machine Learning“ (`demos.html`, Gruppe „Gesundheit und Rettung“). Ein Mini-Gebäude (2 bis 4 Etagen, 3 bis 6 Menschen je Etage, höchstens 24) wird geräumt: die **Treppe** als Fluss (Durchsatz je Zeitschritt), der **Aufzug** als Fahrten mit Kapazität, Halt an mehreren Etagen und einer Dauer nach der höchsten Etage. **Menschen mit eingeschränkter Mobilität** (Aufzugspflicht) dürfen nur den Aufzug nehmen, die übrigen wählen frei. Verglichen werden das **reine Flussmodell** (Zeitnetz, Maximalfluss), der **exakte Plan** (Aufzählung der Aufteilungen plus Pareto-DP über Fahrtenmengen) und der **Fluss mit Maschinenschranke** der Pflichtgruppe; der Wartebereich mit Rückstau ist vorgerechnet (CP-SAT, nicht in der App).

Alle Werte sind Annahmen eines Mini-Gebäudes. **Keine Aussage über reale Gebäude, Brandschutzvorgaben, Verordnungen oder reale Zeiten**; im Ernstfall ist ein Aufzug oft gerade nicht zulässig, das Modell sagt dazu nichts.

## Warum dieses Problem

Die Treppe lässt sich als Fluss rechnen, das ist das Modell der `zeitfluss-demo`; die Aufzugsfahrten sind Aufträge, deren Dauer von ihrer Zusammensetzung abhängt, das ist Bündeln plus Maschinenbelegung (anders als die festen Aufträge der `lpt-scheduling-demo`). Kernfrage: **Wann reicht ein Flussmodell für die Räumung mit Aufzug, und wo endet es, weil sich die Etagen die Kabinen teilen und eine Fahrt je nach Zusammensetzung unterschiedlich lang eine Kabine belegt, das Flussmodell aber jeder Etage alle Kabinen für sich gibt?**

## Modell

Etagen 1 bis F über dem Ausgang, alle Menschen zum Zeitschritt 0 bereit. **Treppe:** je Flucht (Etage f nach f − 1) bis zu C Menschen je Zeitschritt (alle Treppenhäuser zusammen), 2 Zeitschritte Gehzeit je Flucht, Staus dort, wo sie auftreten. **Aufzug:** E Kabinen (1 oder 2) starten am Ausgang; eine Fahrt nimmt höchstens K Menschen und darf an beliebig vielen Etagen halten; Dauer = 2 · höchste Etage · Etagenzeit + Halte · Halt + Halt (Entladen); die letzte Ankunft ist die größte Summe der Fahrtdauern je Kabine minus Halt, unabhängig von der Reihenfolge. **Wahl:** Menschen mit Aufzugspflicht fahren im Aufzug, von den übrigen nehmen a_f je Etage den Aufzug (Teil der Entscheidung). **Ziel:** T\*, die kleinste Räumungszeit (Zeitschritt, in dem der letzte Mensch den Ausgang erreicht). Die vollständige Formulierung steht im Expander „📐 Mathematische Formulierung“ der App.

**Annahmen dieser Demo.** Alle Werte sind Annahmen eines Mini-Gebäudes, keine realen Gebäude und keine Brandschutzvorgaben. Zähleinheiten: Zeitschritt, Person, Fahrt.

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

## Methodik

* **Reines Flussmodell** (`evk_algorithm.flow_time`): Zeitnetz, beide Wege als Kanten, Menschen mit Aufzugspflicht nur zum Aufzug; Maximalfluss (scipy, Dinic), kleinstes T per Binärsuche. *Takt:* Kapazität Kabinen · K nur zu den Abfahrtszeiten, jede Etage hat alle Kabinen für sich (eine untere Schranke von T\*); *Rate:* gerundeter Durchsatz je Zeitschritt, wie man den Aufzug im Zeitfluss anlegen würde.
* **Exakt** (`evk_algorithm.joint_exact`): alle Aufteilungen der Gehenden aufzählen (höchstens 7^4 = 2401 bei 24 Menschen; in der App in der Regel deutlich unter einer Sekunde, im Worst Case mit 24 Menschen und Anteil 0 gemessen 0,81 s auf einem Entwicklungsrechner, auf anderen Rechnern kann es länger dauern); Treppenzeit per Simulation, Aufzugszeit per Pareto-DP über Mengen von Fahrten (Zustand: verbleibende Menschen je Etage, Wert: Pareto-Menge der sortierten Belegungszeiten der Kabinen); T\* = Minimum des Maximums. Ein Prüfer (`evaluate_plan`) kontrolliert jeden angezeigten Plan.
* **Fluss plus Maschinenschranke:** Maximum aus Fluss und der Aufzugszeit der Pflichtgruppe allein (exakt, Mehrfachhalt). Einzelhalt-Fassungen (jede Fahrt hält an einer Etage, exakt oder mit Listenregel) zum Vergleich.
* **Wartebereich** (`tools/evk_cpsat.py`, nur Messreihe und Orakel): CP-SAT auf dem Zeitnetz; auf Etage f warten e Menschen am Aufzug, der Überlauf o = max(0, e − W) steht im Treppenhaus, je Q Überlaufmenschen (aufgerundet) fällt ein Durchsatzplatz der Flucht dieser Etage aus.
* **Messreihe** (`tools/sweep_evakuierung.py`): alle 96 Stufenkombinationen (Etagen 2 bis 4, Kabinen 1 und 2, Kapazität 1 bis 4, Treppe 2 und 3, Halt 1 und 2) × 30 feste Zufalls-Seeds (1 bis 30) × Anteil 0 bis 40 % in 5-%-Schritten = 25 920 Zeilen, alles ganzzahlig (Generator SplitMix64, keine Gleitkommafunktion der C-Bibliothek). Die Presets nutzen Zufalls-Seeds ab 101, außerhalb dieser Stichprobe.

## Befunde (gemessen, keine Behauptungen)

**Grundgesamtheit „Basisraster“:** Etagen 2 bis 4, Kabinen 1 und 2, Kapazität 2 bis 4, Treppe 2, Halt 1 (18 Zellen, dieselben wie in der Vormessung), Anteil 5 bis 40 %, je 30 Zufalls-Seeds: 4320 Paare aus Gebäude und Anteil. Mittel = Mittel über Zellen, Seeds und Anteile; Bänder = 95-%-Bootstrap über die 30 Zufalls-Seeds (2000 Ziehungen). Fehler = T\* minus Verfahren in Zeitschritten (positiv: das Verfahren unterschätzt). Jede Zahl wird in `tests/test_claims.py` aus `data/evk_results.json` nachgerechnet; die Messreihe selbst wird in `tests/test_results.py` stichprobenweise neu gerechnet (exakt, alles ganzzahlig).

| Frage | Befund (Voraussetzung: Basisraster, 30 Zufalls-Seeds) |
|---|---|
| Wie weit liegt das reine Flussmodell (Takt) unter der exakten Räumungszeit? | im Mittel **1,94** [1,67; 2,23] Zeitschritte bei einer mittleren Räumungszeit T\* von 9,3; nie darüber; exakt in 2365 von 4320 Paaren |
| Hängt das an der Zahl der Kabinen? | eine Kabine 3,26 [2,84; 3,71], zwei Kabinen 0,63 [0,49; 0,77] |
| Wie hängt der Fehler von Anteil, Etagen und Kapazität ab? | er wächst mit dem Anteil und den Etagen und fällt mit der Kapazität: Anteil 5 % 0,22, Anteil 40 % 4,28; 2 / 3 / 4 Etagen 0,62 / 1,81 / 3,40; Kapazität 2 / 3 / 4: 2,82 / 1,80 / 1,22. Im Gesamtraster (96 Kombinationen) ist er bei einer Kabine am größten bei Kapazität 1. Das passt zur gemeinsamen Kabinenzeit der Etagen als Ursache, nicht zur Kapazität je Fahrt: mit der Maschinenschranke bleibt der Fehler bei Kapazität 1 bis 4 unter 0,05 (Mittel je Kapazität, Gesamtraster) |
| Größter Fehler im Basisraster? | Zelle 4 Etagen, 1 Kabine, Kapazität 2, Anteil 40 %: im Mittel 14,57 bei T\* = 30,0 (49 %); einzelne Gebäude 3 bis 27 Zeitschritte darunter. Im Gesamtraster (96 Kombinationen) liegt das Zellenmittel bei Anteil 40 % bis 38,5 (4 Etagen, 1 Kabine, Kapazität 1, Halt 2) |
| Ist die Ratenform ein Ersatz? | Mittel 0,03 [−0,20; 0,26], aber nur, weil sich Über- und Unterschätzung aufheben: in 1818 Paaren über T\*, in 821 darunter, in 1681 gleich; mittlerer Betrag 1,44 gegen 1,94 beim Takt |
| Schließt der Fluss plus Maschinenschranke den Fehler? | Fehler im Mittel **0,07** [0,04; 0,10]; exakt in 4037 von 4320 Paaren (93,4 %); nie über T\* (0 Verletzungen in allen 25 920 Zeilen der Messreihe). Die Einzelhalt-Fassungen überschätzen im Mittel: −1,33 [−1,52; −1,15] (exakt) und −1,35 (Listenregel); im Einzelnen liegen beide in 1451 von 4320 Paaren über T\* und in 243 darunter, bei Kapazität 1 stimmen sie mit Fluss plus Schranke überein |
| Wann reicht der Fluss? (Faustregel R: Aufzugszeit der Pflichtgruppe allein ≤ Flusswert) | gilt R, liegt der Fluss in 2629 von 2644 Paaren höchstens 1 Zeitschritt unter T\* (99,4 %, größter Fehler 2); gilt R nicht, nur in 506 von 1676 (30,2 %), mittlerer Fehler 4,83, größter 27. Ist die Schranke mehr als das 1,5-Fache des Flusses (822 Paare), liegt der Fluss in 0 davon höchstens 1 unter T\* |
| Wie anders in allen 96 Stufenkombinationen? | R gilt: 12 786 von 12 816 Paaren mit Fehler höchstens 1 (größter 2); R gilt nicht: 1134 von 10 224 (11,1 %, größter Fehler 68): die Trefferquote bei falscher Regel hängt an der Auswahl der Stufen |
| Hilft die freie Wahl der Gehenden? | Anteil 0 %: in 414 von 540 Gebäuden ist T\* kleiner als bei „alle Gehenden auf der Treppe“; kleinste Zahl Freiwilliger im Mittel 1,59 von 13,3 Gehenden (11,9 %), Gewinn im Mittel 0,98 Zeitschritte. Anteil 20 %: 89 von 540, 0,26 Freiwillige (2,5 %), Gewinn 0,18. Anteil 40 %: 12 von 540, 0,02 Freiwillige (0,3 %), Gewinn 0,02 |
| Wo kippt die Räumung durch die Aufzugspflicht? (kleinster Anteil, bei dem T\* größer ist als bei Anteil 0; Median über 30 Zufalls-Seeds, je Zelle) | eine Kabine: **15 bis 27,5 %** über die 9 Zellen, in 26 bis 30 von 30 Zufalls-Seeds kippt es bis 40 %; zwei Kabinen: 25 % bis über 40 %, in 4 von 9 Zellen im Median über 40 % (1 bis 28 von 30 Seeds kippen bis 40 %). Das reine Flussmodell sieht den Kipppunkt in 17 von 18 Zellen im Median nicht bis 40 % (einzige Ausnahme: 4 Etagen, 1 Kabine, Kapazität 2: 30 %) |
| Wie hängt der Kipppunkt an den Annahmen? (3 Etagen, Kapazität 3) | eine Kabine: 15 % bei Treppe 2 / Halt 1, bei Treppe 3 und bei Halt 2 ebenfalls 15 %. Zwei Kabinen: 37,5 % (Treppe 2, Halt 1), 30 % (Treppe 3), 25 % (Halt 2) |
| Ist der Wartebereich ein Hebel? (3 Etagen, Kapazität 3, Treppe 2, Halt 1, eine Kabine, Anteil 20 %, Mittel über 30 Zufalls-Seeds, Q = 2) | Verlängerung gegen unbegrenzte Plätze: 2 Plätze 0,03, 1 Platz 0,13, 0 Plätze **0,47** (11 von 30 Zufalls-Seeds betroffen); mit Q = 1 0,97 (17 von 30), mit Q = 4 0,37 (9 von 30). Die zweite Kabine bringt bei 30 % und 0 Plätzen im Mittel 3,83 Zeitschritte (12,17 auf 8,33), bei unbegrenzten Plätzen 4,20 (11,67 auf 7,47) |

## Befunde und Korrekturen (Neumessung gegen die Vormessung)

Die Vormessung (V2, Planungsordner der Website) ist eine Erwartung, keine README-Zahl; die Demo rechnet mit einem eigenen Generator (andere Ableitung der Zufallszahlen aus dem Zufalls-Seed, daher andere Gebäude) und allen Stufen neu. Die Zahlen der Vormessung stehen hier als Messung der Vormessung, nicht im Test.

* **Der Kern stimmt mit dem Kern der Vormessung überein:** auf den Gebäuden der Vormessung (deren Generator, Zufalls-Seeds 1 bis 30) liefert der Kern der Demo in allen 8100 Zeilen der Vormessung alle zwölf Spalten (T\*, kleinste und größte Zahl Freiwilliger, T getrennt, Zahl optimaler Aufteilungen, Schranke, Treppe, Fluss Takt und Rate, die drei Korrekturen) identisch. *Messung dieser README (`tools/gegenprobe_v2.py`), nicht im Test (der Vergleich braucht den Generator der Vormessung).*
* **Fehler des Flusses größer als in der Vormessung:** 1,94 [1,67; 2,23] gegen 1,54 [1,32; 1,76] der Vormessung; eine Kabine 3,26 gegen 2,69, zwei Kabinen 0,63 gegen 0,39. Die Bänder überlappen kaum. Eine Wiederholung mit 300 weiteren Zufalls-Seeds (31 bis 330, Basisraster) gibt 1,77 (eine Kabine 3,03, zwei 0,51; Standardabweichung je Zufalls-Seed 0,75, Standardfehler eines Mittels über 30 Seeds 0,14): beide Zahlen liegen innerhalb von zwei Standardfehlern um 1,77; der Unterschied der beiden 30er-Mittel (0,40) entspricht etwa zwei Standardfehlern der Differenz. Das spricht für Streuung der Stichprobe von 30 Gebäuden, nicht für einen Fehler (zusammen mit der identischen Kernrechnung oben). Die Aussage „der Fluss unterschätzt, wächst mit Anteil und Etagen, fällt mit der zweiten Kabine“ bleibt. *Messung dieser README (`tools/mehr_seeds.py`), nicht im Test.*
* **Kipppunkt bei einer Kabine später:** 15 bis 27,5 % gegen 15 bis 20 % der Vormessung (die Zellen mit 2 Etagen kippen bei 25 bis 27,5 %, nicht bei 20 %). Bei zwei Kabinen unverändert „25 % bis über 40 %“.
* **Faustregel R:** Trefferquote bei wahrer Regel 99,4 % gegen 99,5 %; bei falscher Regel 30,2 % gegen 34 %. Die Struktur bleibt, die Quote bei falscher Regel hängt an den Stufen (11,1 % über alle 96 Kombinationen).
* **Fluss plus Schranke:** 0,07 wie in der Vormessung; exakt in 93,4 % (Vormessung 93 %).
* **Wartebereich:** 0,47 gegen 0,63 der Vormessung (eine Kabine, 20 %, 0 Plätze, Q = 2); Q-Abhängigkeit und zweite Kabine als größerer Hebel bleiben.
* **Orakel-Lauf:** 240 Zufallsinstanzen (Zufalls-Seed 2026118, derselbe Strom wie in der Vormessung, aber alle Prüfungen neu mit dem Kern der Demo): exaktes Modell gegen CP-SAT 240 von 240 (T\* zulässig, T\* − 1 unzulässig, kein Aufruf unentschieden), gegen die Vollaufzählung 201 von 201 (Instanzen bis 10 Menschen), der Prüfer akzeptiert den Plan in 240 von 240, der Takt-Fluss liegt in 124 unter T\* und in keiner darüber, die Schranke in keiner darüber; Wartebereich unbegrenzt gleich T\* und monoton in den Plätzen in 132 von 132 (in 11 wirkt der Rückstau). Die freie Wahl hilft strikt nur in 2 dieser 240 sehr kleinen Instanzen (die Messreihe enthält 2512 solche Zeilen von 25 920). *Messung dieser README (`tools/oracle_lauf.py`), im Repo nur die schnelle Fassung.*

## Ehrliche Grenzen

1. **Mini-Gebäude** (bis 4 Etagen, höchstens 24 Menschen): in dieser Demo ist das gemeinsame Modell nur dort exakt gelöst. Aussagen über größere Gebäude stützt diese Messung nicht; die Vormessung V1 (5 Etagen, 20 bis 60 Menschen je Etage, nicht in dieser Demo) fand bei einer Kabine ebenfalls ein Flussmodell deutlich unter der Aufzugszeit, aber die Zahlen sind nicht vergleichbar.
2. **Alle Parameter sind Annahmen** (Durchsatz, Gehzeit, Kabinen, Kapazität, Halt, Warteplätze, Überlauf); die Kipppunkte hängen an ihnen (siehe Tabelle). Es gilt die Struktur der Aussage (Fluss gegen Maschinenschranke), nicht die einzelne Prozentzahl.
3. Die Wahl der Gehenden ist **ein Plan mit vollständiger Kenntnis** bei Zeitschritt 0, kein Verhalten von Menschen; keine Reaktionszeit, keine Dichteeffekte auf der Treppe, keine Begleitpersonen, kein Ausfall des Aufzugs.
4. **Wartebereich:** Rückstau ist als Ausfall von Durchsatzplätzen der Flucht derselben Etage modelliert; andere Rückstaumodelle (Blockieren der Fluchten darüber, endliche Vorräume) wurden nicht gemessen. Die Tabelle gilt nur für 3 Etagen, Kapazität 3, Treppe 2, Halt 1 und hängt an Q.
5. Der exakte Aufzug (Pareto-DP) ist nur für 1 und 2 Kabinen gebaut und wächst mit Etagen und Menschen; für mehr bräuchte man eine Heuristik oder CP-SAT.
6. Die Faustregel R braucht eine Zahl, die der Fluss nicht liefert: die Aufzugszeit der Pflichtgruppe allein. Ihre Trefferquote bei falscher Regel hängt an den gewählten Stufen.
7. Alle Bänder gelten für die Verteilung der 30 Zufalls-Seeds dieser Gebäudeform, nicht für reale Gebäude. Kipppunkte stehen auf dem 5-%-Raster; „über 40 %“ heißt: im Median der 30 Zufalls-Seeds bis 40 % nicht erreicht (als 45 gezählt); einzelne Zufalls-Seeds kippen früher.

## Verifikation

- **Kern:** Treppe, Fahrtdauer, Aufzug, Aufteilung, Fluss und Schranke gegen die Handrechnung (`tests/test_algorithm.py`, `tests/test_handbeispiel.py`); unabhängiger Prüfer für jeden Plan.
- **Orakel** (`tests/test_oracle_evakuierung_aufzug.py`): Treppenzeit gegen den Maximalfluss im Zeitnetz (networkx und `linprog`: T reicht, T − 1 reicht nicht); Pareto-DP gegen Vollaufzählung aller Fahrtenpläne mit Mehrfachhalt; gemeinsames Modell gegen Vollaufzählung aller Aufteilungen und gegen CP-SAT; Wartebereich gegen CP-SAT; Dinic gegen networkx auf dem Flussnetz.
- **Randfälle:** Anteil 0, nur Aufzug, nur Treppe, eine Etage, Kapazität 1, leere Etagen, ein Mensch bei zwei Kabinen, leeres Gebäude (`tests/test_edge_cases.py`).
- **Messreihe:** Aufbau, Ordnungsketten in jeder der 25 920 Zeilen, Zweigtests (jede Variante weicht irgendwo ab, keine Spalte mit lauter Nullen), exaktes Neu-Rechnen einer Stichprobe, Wartebereich monoton für jeden Zufalls-Seed (`tests/test_results.py`); jede README-Zahl in `tests/test_claims.py`.
- **Presets, Geschichten, Verdikte:** `tests/test_presets.py` (erwartete Verdikt-Art je Preset), `tests/test_stories.py` (jeder Satz der Preset-Geschichten gegen die Analyse), `tests/test_verdicts.py` (Schwellen und jede Zahl im Text).
- **Oberfläche:** AppTest (jeder Button, jeder Regler am Minimum und Maximum, jede Option der Wartebereich-Auswahl, Permalink, Worst Case mit 24 Menschen), Layout und Footer.
- Die Testzahl: 161 Tests in `tests/` (`pytest --collect-only -q tests`).

## Dateistruktur

| Datei | Zweck |
|---|---|
| `.github/workflows/tests.yml` | CI: Push, Pull Request, wöchentlicher Canary |
| `.gitignore` | venv, Caches, Streamlit-Secrets |
| `.streamlit/config.toml` | Streamlit-Einstellungen (keine Nutzungsstatistik) |
| `app.py` | Streamlit-App (Gerüst nach DEMO-PLAYBOOK §2) |
| `evk_algorithm.py` | Kern: Treppe, Aufzug (Pareto-DP), gemeinsames exaktes Modell, Fluss, Schranke, Prüfer |
| `evk_constants.py` | Regler-Grenzen, feste Annahmen, Annahmen-Text, Farben, Presets |
| `evk_evaluation.py` | Analyse einer Einstellung, Räumungskurve, Verdikte |
| `evk_layout.py` | Fester Kopf (Stylesheet) |
| `evk_pdf_export.py` | PDF-Bericht |
| `evk_presets.py` | Permalink (Begrenzen, Einrasten), Presets, Zufalls-Seed-Button |
| `evk_results.py` | Laden und Auswertung der vorgerechneten Messreihen |
| `evk_rng.py` | SplitMix64 (ganzzahlig) |
| `evk_scenario.py` | Mini-Gebäude, geschachtelte Aufzugspflicht |
| `evk_stories.py` | Geschichten der Presets und ihre Prüfungen |
| `evk_visualization.py` | Plotly-Abbildungen (Achsen gesperrt) |
| `data/evk_results.json`, `data/evk_wait.json` | vorgerechnete Messreihen (25 920 Zeilen; Wartebereich 60 Zellen mit je 30 Zeilen) |
| `tools/sweep_evakuierung.py`, `tools/sweep_wartebereich.py` | erzeugen die Messreihen |
| `tools/analyse.py`, `tools/preset_search.py`, `tools/oracle_lauf.py`, `tools/evk_cpsat.py` | Auswertung, Seed-Suche der Presets, großer Orakel-Lauf, CP-SAT (nur Orakel) |
| `tools/gegenprobe_v2.py`, `tools/mehr_seeds.py` | Gegenprobe des Kerns gegen den Kern der Vormessung (braucht den Planungsordner der Website), Wiederholung mit 300 weiteren Zufalls-Seeds |
| `requirements-dev.txt`, `requirements.txt` | Laufzeit (streamlit, numpy, scipy, plotly, fpdf2) plus pytest, networkx, ortools für die Orakel |
| `tests/` | siehe Verifikation |

## Bewusst nicht umgesetzt

- Mehr als zwei Kabinen, Gebäude über 4 Etagen oder über 6 Menschen je Etage im exakten Modell (der Aufzählungsraum wächst mit 7^F).
- Wartebereich als Regler: CP-SAT gehört nicht in die App, und die Tabelle gilt nur für 3 Etagen, Kapazität 3, Treppe 2, Halt 1; ein Regler wäre sonst für andere Einstellungen ein toter Regler.
- Verhalten statt Plan (Wahl nach Wegstrecke, Reaktionszeit, Dichteeffekte auf der Treppe), Begleitpersonen, Tragestuhl, Ausfall des Aufzugs, mehrere Treppenhäuser mit eigenen Wegen.
- Rechtslage, Brandschutz, Verordnungen und reale Zeiten; keine Aussage über reale Gebäude.
- Frühankunftsfluss und Quickest Transshipment als Verfahren (die `zeitfluss-demo` führt sie als nicht umgesetzt; hier löst der exakte Plan den Treppenteil direkt im Zeitnetz).

## Lokal ausführen

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt
streamlit run app.py
```

## Tests ausführen

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

Gebaut mit Streamlit, Plotly, NumPy und SciPy.

---

Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). Mehr zu den Demos: [Interaktive Demos](https://sebastianhanisch.net/demos.html).
