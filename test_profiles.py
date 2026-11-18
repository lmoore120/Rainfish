"""Animal profiles: the bundled killifish preset, how the Rainfish window
reads profiles, and the geometry used by the "Create your own" shape maker."""
import json
import os

import numpy as np
import pytest

import make_animal_profile as maker
import rainfish_gui as gui

from test_landmarks import FISH_PERIMETER


def test_killifish_preset_is_valid():
    path = os.path.join(gui.PROFILE_DIR, gui.FISH_PROFILE)
    profile = json.load(open(path, encoding="utf-8"))
    assert len(profile["fixed_names"]) == 7
    assert sum(profile["semis_per_segment"]) == 36
    template = np.array(profile["template"])
    assert template.shape == (43, 2)
    # Stored centred, at unit size, facing right.
    np.testing.assert_allclose(template.mean(axis=0), 0, atol=1e-3)
    assert np.sqrt((template ** 2).sum()) == pytest.approx(1, abs=1e-3)
    assert template[0, 0] > template[3:5, 0].mean()


def test_gui_perimeter_order_matches_protocol():
    assert gui.perimeter_order(gui.load_profile(gui.FISH_PROFILE)) == FISH_PERIMETER


def test_missing_profile_falls_back_to_fish():
    profile = gui.load_profile("no_such_animal.json")
    assert gui.profile_counts(profile) == (7, 36, 43)


def test_unreadable_profile_is_ignored(tmp_path, monkeypatch):
    monkeypatch.setattr(gui, "PROFILE_DIR", str(tmp_path))
    (tmp_path / "broken.json").write_text("{not json")
    (tmp_path / "short.json").write_text('{"fixed_names": ["a"], "semis_per_segment": [1]}')
    assert gui.read_profile("broken.json") is None
    assert gui.read_profile("short.json") is None
    files = [f for _, f in gui.list_profiles()]
    assert "broken.json" not in files and "short.json" not in files


def test_custom_profiles_are_listed_after_fish(tmp_path, monkeypatch, custom_profile):
    monkeypatch.setattr(gui, "PROFILE_DIR", str(custom_profile.parent))
    listed = gui.list_profiles()
    assert listed[0][1] == gui.FISH_PROFILE
    assert ("Test animal (27 landmarks)", "test_animal.json") in listed


# ------------------------------------------------------- shape maker
def test_semilandmarks_are_evenly_spaced_between_primaries():
    square = [(0, 0), (100, 0), (100, 100), (0, 100)]
    semis = maker.semis_along_curve(square, [3, 0, 1, 2])
    assert semis.shape == (6, 2)
    # The three between corner 1 and 2 sit in order along the top edge.
    xs = semis[:3, 0]
    assert list(xs) == sorted(xs) and 0 < xs[0] < xs[-1] < 100


def test_shape_maker_perimeter_order():
    assert maker.perimeter_order(7, [9, 1, 2, 9, 1, 3, 11]) == [i - 1 for i in FISH_PERIMETER]


def test_crossing_count():
    box = np.array([(0, 0), (1, 0), (1, 1), (0, 1)], float)
    bow_tie = np.array([(0, 0), (1, 1), (1, 0), (0, 1)], float)
    assert maker.count_crossings(box) == 0
    assert maker.count_crossings(bow_tie) == 1


def test_shape_drawn_facing_left_is_mirrored_not_flipped():
    # Snout at the left, back on top (smaller y), belly below.
    drawn = np.array([(0, 50), (60, 20), (100, 50), (60, 80)], float)
    shape, back = maker.normalise_shape(drawn, 4)
    assert back == 2                                   # the tail is furthest from the snout
    assert shape[0, 0] > 0                             # now faces right
    assert shape[1, 1] < shape[3, 1]                   # back still above belly
    assert np.sqrt((shape ** 2).sum()) == pytest.approx(1)
