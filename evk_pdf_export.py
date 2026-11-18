"""Bericht zur gewählten Einstellung als PDF (fpdf2, Kernschrift Helvetica: Umlaute gehen, Gedankenstrich, Pfeile, Kleiner-gleich und Emoji nicht)."""
from __future__ import annotations

from fpdf import FPDF

_REPLACE = {"–": "-", "—": "-", "−": "-", "≤": "<=", "≥": ">=", "→": "->", "…": "...", "·": ".", "„": '"', "“": '"', "′": "'"}


def _clean(text: str) -> str:
    for a, b in _REPLACE.items():
        text = text.replace(a, b)
    return text.encode("latin-1", "replace").decode("latin-1")


def generate_report_pdf(title: str, summary_lines: list[str], trip_rows: list[tuple[str, int, int, int, str]]) -> bytes:
    """Kennzahlen der Einstellung und die Fahrten des optimalen Plans (Zeilen: Kabine, Start, Ankunft am Ausgang, frei ab, Personen je Etage)."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.multi_cell(0, 9, _clean(title), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    for line in summary_lines:
        pdf.multi_cell(0, 5, _clean(line), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    heads = [("Kabine", 24), ("Start", 18), ("Ankunft", 22), ("frei ab", 20), ("Personen je Etage", 90)]
    pdf.set_font("Helvetica", "B", 9)
    for h, w in heads:
        pdf.cell(w, 6, _clean(h), border=1)
    pdf.ln()
    pdf.set_font("Helvetica", "", 9)
    for cab, start, arrival, end, load in trip_rows:
        for c, (_, w) in zip((cab, str(start), str(arrival), str(end), load), heads):
            pdf.cell(w, 6, _clean(c), border=1)
        pdf.ln()
    return bytes(pdf.output())
