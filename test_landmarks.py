"""Landmark placement in find_animal_landmarks.py: the 43-point killifish
scheme, custom animal profiles, the default shape, and the checks that stop
a half-finished frame being accepted."""
import numpy as np
import pytest

# The killifish outline order, written out by hand from the protocol
# (and identical to perimeter.map in Colormesh_extraction.R).
FISH_PERIMETER = ([1] + list(range(8, 17)) + [2, 17, 3, 18, 19, 4]
                  + list(range(20, 29)) + [5, 29, 6, 30, 31, 32, 7]
                  + list(range(33, 44)))


def test_fish_scheme_has_43_landmarks(landmarker):
    assert len(landmarker.FIXED_LANDMARK_NAMES) == 7
    assert landmarker.SEMILANDMARKS_PER_SEGMENT == [9, 1, 2, 9, 1, 3, 11]
    assert landmarker.TOTAL_LANDMARKS == 43


def test_fish_perimeter_order_matches_protocol(landmarker):
    assert [i + 1 for i in landmarker.PERIMETER_ORDER] == FISH_PERIMETER
    assert sorted(landmarker.PERIMETER_ORDER) == list(range(43))


def test_fish_profile_has_default_shape(landmarker):
    assert landmarker.TEMPLATE is not None
    assert landmarker.TEMPLATE.shape == (43, 2)
    assert landmarker.AUTO_DETECT is True


def test_landmarks_from_primary_points_keeps_clicks_and_fills_in(landmarker):
    seven = landmarker.TEMPLATE[:7] * 400 + 500        # a fish-sized, fish-shaped set
    landmarks, _ = landmarker.landmarks_from_seven_points(seven, None, follow="spline")
    assert landmarks.shape == (43, 2)
    np.testing.assert_allclose(landmarks[:7], seven)   # your clicks are kept exactly
    crosses, _ = landmarker.shape_self_intersects(landmarks)
    assert not crosses


def test_semilandmarks_follow_a_detected_outline(landmarker):
    # Use the default shape itself as the "detected outline".
    outline = landmarker.TEMPLATE[landmarker.PERIMETER_ORDER] * 400 + 500
    dense = landmarker.resample_closed_curve(outline, 400)
    seven = landmarker.TEMPLATE[:7] * 400 + 500
    landmarks, _ = landmarker.landmarks_from_seven_points(seven, dense, follow="outline")
    distance = [np.min(np.linalg.norm(dense - p, axis=1)) for p in landmarks]
    # Body-curve segments (under the fins) may cut inside; most points ride the outline.
    assert np.median(distance) < 2.0


def test_crossed_outline_is_detected(landmarker):
    seven = landmarker.TEMPLATE[:7] * 400 + 500
    landmarks, _ = landmarker.landmarks_from_seven_points(seven, None, follow="spline")
    tangled = landmarks.copy()
    tangled[[10, 35]] = tangled[[35, 10]]               # swap a top and a bottom point
    crosses, count = landmarker.shape_self_intersects(tangled)
    assert crosses and count > 0


def test_custom_profile_changes_the_scheme(landmarker, custom_profile):
    landmarker.apply_profile(str(custom_profile))
    assert landmarker.FIXED_LANDMARK_NAMES == ["snout", "neck", "tail_tip", "belly", "jaw"]
    assert landmarker.TOTAL_LANDMARKS == 27
    assert landmarker.AUTO_DETECT is False
    assert len(landmarker.csv_header()) == 18 + 2 * 27 + 5 * 6
    # The toolbar labels name this animal's counts, not the fish's.
    labels = {action: label for label, _, action in landmarker.TOOLBAR_BUTTONS}
    assert labels["clear"] == "Clear 5"
    assert labels["manual_all"] == "Place all 27"

    five = landmarker.TEMPLATE[:5] * 300 + 400
    landmarks, _ = landmarker.landmarks_from_seven_points(five, None, follow="spline")
    assert landmarks.shape == (27, 2)
    assert not landmarker.shape_self_intersects(landmarks)[0]


def test_bad_profile_is_rejected(landmarker, tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text('{"fixed_names": ["a", "b", "c"], "semis_per_segment": [1, 2]}')
    with pytest.raises(ValueError):
        landmarker.apply_profile(str(bad))


def test_default_shape_is_placed_over_the_outline(landmarker):
    outline = np.array([[100, 200], [500, 200], [500, 300], [100, 300]], float)
    placed = landmarker.place_template((600, 800, 3), outline=outline)
    assert placed.shape == (43, 2)
    # Same width as the outline, centred on it.
    assert np.ptp(placed[:, 0]) == pytest.approx(400, rel=0.01)
    np.testing.assert_allclose((placed.min(0) + placed.max(0)) / 2, [300, 250], atol=1)
    # Arrives facing right: landmark 1 (snout) is the right-most point.
    assert placed[0, 0] == pytest.approx(placed[:, 0].max(), abs=1)


def test_default_shape_without_an_outline_goes_mid_frame(landmarker):
    placed = landmarker.place_template((600, 800, 3))
    centre = (placed.min(0) + placed.max(0)) / 2
    np.testing.assert_allclose(centre, [400, 300], atol=1)


def test_frame_needs_everything_by_default(landmarker):
    empty = {"colour_standard": None, "label": "", "scale_bar": None, "landmarks": None}
    assert landmarker.outstanding_items(empty) == ["color standard", "label", "scale",
                                                   "landmarks"]


def test_unticked_extras_are_not_required(landmarker):
    landmarker.NOT_REQUIRED.update({"label", "colour_standard", "scale"})
    result = {"colour_standard": None, "label": "", "scale_bar": None,
              "landmarks": np.zeros((43, 2))}
    assert landmarker.outstanding_items(result) == []


def test_original_fish_script_still_imports():
    """find_fish_and_landmarks.py is kept unchanged for the existing workflow."""
    import find_fish_and_landmarks as original
    assert original.TOTAL_LANDMARKS == 43
