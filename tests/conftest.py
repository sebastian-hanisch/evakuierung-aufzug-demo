"""Gemeinsame Fixtures: das Handbeispiel (DEMO-PLAYBOOK §1b), an dem jede Einheit von Hand geprüft wird."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import evk_algorithm as A  # noqa: E402


@pytest.fixture
def hand():
    """Handbeispiel (docs/planung/barrierefreiheit-planung/handbeispiel_02.py): 2 Etagen, Pflicht (1, 1), Gehende (2, 1), 1 Kabine für 3, Halt 1, Treppe 2.
    Von Hand: Aufzugszeit der Pflichtgruppe 6 (eine Fahrt mit zwei Halten), Treppe 4, T* = 6, Fluss (Takt) 5."""
    return {"mandatory": (1, 1), "free": (2, 1), "params": A.Params(cabins=1, capacity=3, halt=1, stairs=2)}
