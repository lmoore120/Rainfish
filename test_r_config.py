"""The configured copies of the R scripts that Rainfish writes into
<project>/_generated: paths, settings, and the landmark layout."""
import os
import re

import rainfish_gui as gui

SETTINGS = {"num_passes": 7, "background": "white"}


def generate(project, profile=None):
    out = os.path.join(project, "_generated")
    written, problems = gui.write_configured_r(project, SETTINGS, out, profile)
    assert problems == []
    return {os.path.basename(p): open(p, encoding="utf-8").read() for p in written}


def setting(text, name):
    """Every value assigned to `name` at the start of a line."""
    return re.findall(rf"^{re.escape(name)}\s*<-\s*(.+)$", text, flags=re.M)


def test_all_three_scripts_are_configured(tmp_path):
    scripts = generate(str(tmp_path))
    assert set(scripts) == {"Colormesh_extraction.R", "CIE_conversion.R", "plasticity_rates.R"}
    project = str(tmp_path).replace("\\", "/")
    code = gui.HERE.replace("\\", "/")
    for text in scripts.values():
        # Nothing left pointing at the original author's folders: every
        # path is in the project, or (the color card values) beside the code.
        for line in text.splitlines():
            if re.match(r'^\w+_(dir|file|csv)\s*<-\s*"([A-Za-z]:/|/)', line):
                assert project in line or code + "/RGB_calib_val.csv" in line, line


def test_color_card_values_prefer_the_projects_copy(tmp_path):
    text = generate(str(tmp_path))["Colormesh_extraction.R"]
    values = setting(text, "calib_values_file")
    assert len(values) == 2 and all("RGB_calib_val.csv" in v for v in values)
    assert all(gui.HERE.replace("\\", "/") in v for v in values)
    (tmp_path / "RGB_calib_val.csv").write_text("patch,R,G,B\n")
    text = generate(str(tmp_path))["Colormesh_extraction.R"]
    assert all(str(tmp_path).replace("\\", "/") in v
               for v in setting(text, "calib_values_file"))


def test_fish_layout_matches_the_original_script(tmp_path):
    text = generate(str(tmp_path), gui.load_profile(gui.FISH_PROFILE))["Colormesh_extraction.R"]
    perimeter = setting(text, "perimeter.map")[0]
    numbers = [int(n) for n in re.findall(r"\d+", perimeter)]
    from test_landmarks import FISH_PERIMETER
    assert numbers == FISH_PERIMETER
    assert "main.lms = 1:7" in setting(text, "sliders1")[0]
    assert "lm[c(4, 5), 1]" in setting(text, "facing_right")[0]


def test_custom_animal_layout(tmp_path, custom_profile):
    import json
    profile = json.loads(custom_profile.read_text())
    text = generate(str(tmp_path), profile)["Colormesh_extraction.R"]
    numbers = [int(n) for n in re.findall(r"\d+", setting(text, "perimeter.map")[0])]
    assert sorted(numbers) == list(range(1, 28))
    assert "main.lms = 1:5" in setting(text, "sliders1")[0]
    assert "lm[c(3), 1]" in setting(text, "facing_right")[0]


def test_background_setting_reaches_the_cie_step(tmp_path):
    """Regression: with no white/black folder in the path, the CIE step used
    to fall back to "unknown" and write LAB_average_unknown.csv."""
    text = generate(str(tmp_path))["CIE_conversion.R"]
    assert setting(text, "background") == ['"white"', '"white"']


def test_rates_step_reads_the_lab_file_that_exists(tmp_path):
    colormaps = tmp_path / "colormaps"
    colormaps.mkdir()
    # Before the CIE step has run: the expected name.
    assert gui.find_lab_average(str(tmp_path), "white").endswith("LAB_average_white.csv")
    # Only an "unknown" file from an older run: use that one.
    (colormaps / "LAB_average_unknown.csv").write_text("x\n")
    text = generate(str(tmp_path))["plasticity_rates.R"]
    assert "LAB_average_unknown.csv" in setting(text, "lab_file")[0]
    # Once the right one exists, it wins.
    (colormaps / "LAB_average_white.csv").write_text("x\n")
    text = generate(str(tmp_path))["plasticity_rates.R"]
    assert "LAB_average_white.csv" in setting(text, "lab_file")[0]


def test_originals_are_never_changed(tmp_path):
    before = {name: open(gui.script_path(name), encoding="utf-8").read()
              for name in gui.R_STEPS.values()}
    generate(str(tmp_path))
    after = {name: open(gui.script_path(name), encoding="utf-8").read()
             for name in gui.R_STEPS.values()}
    assert before == after
