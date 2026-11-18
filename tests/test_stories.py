"""Geschichten der Presets: jeder Satz ist eine Behauptung über das Gebäude des Presets und wird gegen die Analyse geprüft."""

import pytest

import evk_constants as C
import evk_evaluation as ev
import evk_stories as stories


def test_there_is_one_story_and_one_check_per_preset():
    assert set(stories.STORIES) == set(C.PRESETS) == set(stories.STORY_CHECKS)


@pytest.mark.parametrize("name", list(C.PRESETS))
def test_story_holds(name):
    assert stories.STORY_CHECKS[name](ev.analyse), name


def test_the_numbers_named_in_the_stories_match_the_checks():
    # „mindestens 3 Zeitschritte darunter“ und „mindestens 4 Zeitschritte länger“ stehen als Zahl im Text und als Schwelle im Check
    assert "mindestens 3 Zeitschritte" in stories.STORIES["Langer Halt, schnelle Treppe"]
    assert ev.analyse(stories.settings_of("Langer Halt, schnelle Treppe")).gap >= 3
    assert "mindestens 4 Zeitschritte" in stories.STORIES["Ohne Bündeln (Kapazität 1)"]
    one = ev.analyse(stories.settings_of("Ohne Bündeln (Kapazität 1)"))
    three = ev.analyse(stories.settings_of("Ohne Bündeln (Kapazität 1)", capacity=3))
    assert one.exact - three.exact >= 4


def test_second_cabin_story_compares_the_same_building():
    one, two = stories.settings_of("Viel Aufzugspflicht, eine Kabine"), stories.settings_of("Zweite Kabine")
    assert (one.floors, one.seed, one.share, one.capacity) == (two.floors, two.seed, two.share, two.capacity) and (one.cabins, two.cabins) == (1, 2)
