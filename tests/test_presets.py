"""Presets: Vollständigkeit, gültige Werte auf dem Reglerraster, Standard-Preset = Standardeinstellungen, erwartete Verdikt-Zeile je Preset (DEMO-PLAYBOOK §11a Punkt 7)."""

import pytest

import evk_constants as C
import evk_evaluation as ev
import evk_presets as P
import evk_results as R
import evk_stories as stories

# erwartete Art der Verdikte (Fluss-Fehler, Faustregel, Freiwillige) je Preset, von Hand aus der Analyse gelesen und im Test festgehalten
EXPECTED = {
    "Standardfall (Voreinstellung)": ("warning", "warning", "info"),
    "Wenig Aufzugspflicht: Fluss reicht": ("success", "success", "info"),
    "Viel Aufzugspflicht, eine Kabine": ("warning", "warning", "info"),
    "Zweite Kabine": ("info", "warning", "info"),
    "Nur freiwillig (Anteil 0)": ("success", "success", "success"),
    "Langer Halt, schnelle Treppe": ("warning", "warning", "info"),
    "Ohne Bündeln (Kapazität 1)": ("warning", "warning", "info"),
}


def test_every_preset_has_help_and_all_keys():
    assert set(C.PRESETS) == set(C.PRESET_HELP) == set(EXPECTED)
    for name, preset in C.PRESETS.items():
        assert set(preset) == set(P.PRESET_KEYS), name
        assert C.PRESET_HELP[name]


def test_preset_values_are_inside_the_slider_bounds_and_on_the_grid():
    for name, preset in C.PRESETS.items():
        for key, state_key in P.PRESET_KEYS.items():
            spec = P.SETTING_SPECS[state_key]
            assert spec.lo <= preset[key] <= spec.hi, (name, key)
            assert P.clamp(spec, preset[key]) == preset[key], (name, key)        # auf dem Raster der Messreihe (Anteil in 5-%-Schritten)
        assert preset["seed"] > 30                                                # außerhalb der Messreihen-Stichprobe 1 bis 30


def test_default_preset_equals_the_default_settings():
    assert ev.Settings(**C.PRESETS["Standardfall (Voreinstellung)"]) == ev.Settings()


def test_setting_specs_cover_every_preset_key():
    assert set(P.PRESET_KEYS.values()) == set(P.SETTING_SPECS)


def test_all_presets_are_distinct_and_every_slider_value_has_a_precomputed_cell():
    assert len({tuple(sorted(p.items())) for p in C.PRESETS.values()}) == len(C.PRESETS)
    for preset in C.PRESETS.values():
        assert ev.Settings(**preset).cell in set(R.all_cells())


def test_clamp_snaps_the_share_to_five_percent_steps():
    spec = P.SETTING_SPECS["share_slider"]
    assert [P.clamp(spec, v) for v in (-3, 0, 2, 3, 7, 8, 38, 41, 99)] == [0, 0, 0, 5, 5, 10, 40, 40, 40]


@pytest.mark.parametrize("name", list(EXPECTED))
def test_each_preset_shows_the_expected_verdicts(name):
    a = ev.analyse(stories.settings_of(name))
    flow = ev.verdict_flow_error(a.exact, a.flow_takt)[0]
    counts = R.rule_counts(R.all_cells())
    rule = ev.verdict_rule(a.rule_holds, a.barrier, a.flow_takt, a.exact, (counts["true_hit"], counts["true"]), (counts["false_hit"], counts["false"]))[0]
    vol = ev.verdict_volunteers(a.exact, a.joint.time_stairs_only, a.joint.a_min, a.joint.a_max, a.n_walkers, a.barrier)[0]
    assert (flow, rule, vol) == EXPECTED[name]
