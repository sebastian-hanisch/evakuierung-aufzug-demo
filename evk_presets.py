"""Permalink (Begrenzen, Einrasten), Presets und Zufalls-Seed-Button (Standardmuster aus dem Demo-Portfolio)."""

import random
from dataclasses import dataclass

import streamlit as st

import evk_constants as C


@dataclass(frozen=True)
class SettingSpec:
    url_param: str
    caster: type
    default: object
    lo: float | None = None
    hi: float | None = None
    step: int = 1


SETTING_SPECS = {
    "floors_slider": SettingSpec("floors", int, C.DEFAULT_FLOORS, C.FLOORS_MIN, C.FLOORS_MAX),
    "cabins_slider": SettingSpec("cabins", int, C.DEFAULT_CABINS, C.CABINS_MIN, C.CABINS_MAX),
    "capacity_slider": SettingSpec("capacity", int, C.DEFAULT_CAPACITY, C.CAPACITY_MIN, C.CAPACITY_MAX),
    "halt_slider": SettingSpec("halt", int, C.DEFAULT_HALT, C.HALT_MIN, C.HALT_MAX),
    "stairs_slider": SettingSpec("stairs", int, C.DEFAULT_STAIRS, C.STAIRS_MIN, C.STAIRS_MAX),
    "share_slider": SettingSpec("share", int, C.DEFAULT_SHARE, C.SHARE_MIN, C.SHARE_MAX, C.SHARE_STEP),
    "seed_input": SettingSpec("seed", int, C.DEFAULT_SEED, C.SEED_MIN, C.SEED_MAX),
}
PRESET_KEYS = {"floors": "floors_slider", "cabins": "cabins_slider", "capacity": "capacity_slider", "halt": "halt_slider", "stairs": "stairs_slider",
               "share": "share_slider", "seed": "seed_input"}


def init_session_state_defaults():
    for state_key, spec in SETTING_SPECS.items():
        if state_key not in st.session_state:
            st.session_state[state_key] = spec.default


def bounds(state_key):
    spec = SETTING_SPECS[state_key]
    return spec.lo, spec.hi


def clamp(spec: SettingSpec, value: int) -> int:
    """Auf die Reglergrenzen begrenzen und auf die Schrittweite einrasten (der Anteil nur in 5-%-Schritten: nur diese Stufen sind vorgerechnet)."""
    value = max(spec.lo, min(spec.hi, value))
    if spec.step > 1:
        value = spec.lo + round((value - spec.lo) / spec.step) * spec.step
        value = min(spec.hi, value)
    return int(value)


def load_permalink_settings():
    """Einmal je Sitzung: Werte aus der Adresszeile übernehmen, auf die Reglergrenzen begrenzt und eingerastet."""
    if "permalink_loaded" in st.session_state:
        return
    qp = st.query_params
    for state_key, spec in SETTING_SPECS.items():
        if spec.url_param in qp:
            try:
                value = spec.caster(qp[spec.url_param])
            except (ValueError, TypeError):
                continue
            st.session_state[state_key] = clamp(spec, value)
    st.session_state["permalink_loaded"] = True


def sync_query_params(values):
    """`values`: {state_key: aktueller Wert}; die Adresszeile spiegelt die Konfiguration."""
    try:
        for state_key, value in values.items():
            st.query_params[SETTING_SPECS[state_key].url_param] = str(value)
    except Exception:
        pass


def apply_preset(name):
    for key, state_key in PRESET_KEYS.items():
        if key in C.PRESETS[name]:
            st.session_state[state_key] = C.PRESETS[name][key]


def aktives_preset():
    """Name des Presets, dessen Werte GENAU den aktuellen Einstellungen entsprechen, sonst None.

    Zustandslos: verglichen wird jeder Regler aus SETTING_SPECS (ein Preset ohne Eintrag für einen Regler meint dessen Standardwert) mit dem Session State.
    Ein später ergänzter Regler braucht nur seinen Eintrag in SETTING_SPECS, dann hebt auch seine Änderung die Markierung auf (tests/test_layout.py prüft das)."""
    preset_key_of = {state_key: key for key, state_key in PRESET_KEYS.items()}
    for name, preset in C.PRESETS.items():
        if all(
            st.session_state.get(state_key, spec.default) == preset.get(preset_key_of.get(state_key), spec.default)
            for state_key, spec in SETTING_SPECS.items()
        ):
            return name
    return None


def sidebar_presets():
    """Schnellstart oben in der Seitenleiste; das aktive Preset ist hervorgehoben (`type="primary"`)."""
    if not C.PRESETS:
        return
    st.header("🎯 Schnellstart")
    st.caption("Ein Beispielszenario laden (setzt jeden Regler):")
    aktiv = aktives_preset()
    for name in C.PRESETS:
        st.button(
            name, width="stretch", on_click=apply_preset, args=(name,), help=C.PRESET_HELP.get(name, ""), key=f"preset_{name}",
            type="primary" if aktiv == name else "secondary",
        )


def randomize_seed():
    st.session_state["seed_input"] = random.randint(C.SEED_MIN, C.SEED_MAX)
