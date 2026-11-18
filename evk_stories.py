"""Geschichten der Presets: ein Satz je Preset, der unter dem Titel steht, solange das Preset aktiv ist.

Jeder Satz ist eine Behauptung über das Gebäude des Presets; `STORY_CHECKS` prüft sie (tests/test_stories.py) gegen die Analyse, damit kein Satz mehr sagt als die Rechnung."""

import evk_constants as C
import evk_evaluation as ev


def settings_of(name: str, **override) -> ev.Settings:
    preset = dict(C.PRESETS[name])
    preset.update(override)
    return ev.Settings(preset["floors"], preset["cabins"], preset["capacity"], preset["halt"], preset["stairs"], preset["share"], preset["seed"])


STORIES = {
    "Standardfall (Voreinstellung)": "Die Pflichtgruppe im Aufzug bestimmt die Räumungszeit, und der Fluss liegt darunter.",
    "Wenig Aufzugspflicht: Fluss reicht": "Mit wenigen Menschen mit Aufzugspflicht gilt die Faustregel, und der Fluss trifft die exakte Räumungszeit.",
    "Viel Aufzugspflicht, eine Kabine": "Eine Kabine und viele Menschen mit Aufzugspflicht: der Fluss liegt um mehr als die Hälfte unter der exakten Räumungszeit.",
    "Zweite Kabine": "Dasselbe Gebäude mit zwei Kabinen: die Räumung ist kürzer, und der Fluss liegt höchstens einen Zeitschritt daneben.",
    "Nur freiwillig (Anteil 0)": "Ohne Aufzugspflicht verkürzt es die Räumung, wenn einige Gehende freiwillig den Aufzug nehmen.",
    "Langer Halt, schnelle Treppe": "Längerer Halt, schnellere Treppe: die Pflichtgruppe im Aufzug bestimmt die Räumungszeit, der Fluss liegt mindestens 3 Zeitschritte darunter.",
    "Ohne Bündeln (Kapazität 1)": "Mit Kapazität 1 fährt jede Person einzeln: die Räumung dauert mindestens 4 Zeitschritte länger als mit Kapazität 3 im selben Gebäude.",
}


def _check_standard(an):
    a = an(settings_of("Standardfall (Voreinstellung)"))
    return a.barrier == a.exact and a.gap >= 1


def _check_rule(an):
    a = an(settings_of("Wenig Aufzugspflicht: Fluss reicht"))
    return a.rule_holds and a.gap == 0 and a.n_mandatory >= 1


def _check_much(an):
    a = an(settings_of("Viel Aufzugspflicht, eine Kabine"))
    return 2 * a.gap > a.exact


def _check_second(an):
    one, two = an(settings_of("Viel Aufzugspflicht, eine Kabine")), an(settings_of("Zweite Kabine"))
    return two.exact < one.exact and two.gap <= 1


def _check_voluntary(an):
    a = an(settings_of("Nur freiwillig (Anteil 0)"))
    return a.n_mandatory == 0 and a.exact < a.joint.time_stairs_only


def _check_halt(an):
    a = an(settings_of("Langer Halt, schnelle Treppe"))
    return a.barrier == a.exact and a.gap >= 3


def _check_k1(an):
    one, three = an(settings_of("Ohne Bündeln (Kapazität 1)")), an(settings_of("Ohne Bündeln (Kapazität 1)", capacity=3))
    return one.exact >= three.exact + 4


STORY_CHECKS = {
    "Standardfall (Voreinstellung)": _check_standard,
    "Wenig Aufzugspflicht: Fluss reicht": _check_rule,
    "Viel Aufzugspflicht, eine Kabine": _check_much,
    "Zweite Kabine": _check_second,
    "Nur freiwillig (Anteil 0)": _check_voluntary,
    "Langer Halt, schnelle Treppe": _check_halt,
    "Ohne Bündeln (Kapazität 1)": _check_k1,
}
