"""The R steps, run for real on a small synthetic project with a known
answer: one video that gets steadily lighter, one that gets steadily
darker, and one that stays the same.

Colormesh itself (step 6's first half) needs real frames and landmarks and
takes minutes per frame, so here it's only checked to parse; the
synthetic data stands in for its output (colormap_calib.csv)."""
import csv
import os
import subprocess

import numpy as np
import pytest

import rainfish_gui as gui
from conftest import CODE

PIPELINE_SCRIPTS = ["Colormesh_extraction.R", "CIE_conversion.R", "plasticity_rates.R"]
POINTS = 25                 # sampling points per frame (Colormesh gives ~1,500)
FRAMES = 8                  # per video, 30 s apart
VIDEOS = {"lighter.mp4": +0.04, "darker.mp4": -0.04, "steady.mp4": 0.0}   # grey change per frame


def r_string(path):
    return path.replace("\\", "/")


@pytest.mark.parametrize("script", sorted(
    f for f in os.listdir(CODE) if f.endswith(".R")))
def test_r_script_parses(rscript, script):
    path = r_string(os.path.join(CODE, script))
    run = subprocess.run([rscript, "-e", f"invisible(parse('{path}'))"],
                         capture_output=True, text=True)
    assert run.returncode == 0, run.stderr


def srgb_to_lightness(value):
    """CIE L* of a grey with the given 0-1 sRGB value (D65), independently
    of the R code, to check CIE_conversion.R's rgb2lab()."""
    linear = value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
    y = linear                                   # grey: Y equals the linear value
    f = y ** (1 / 3) if y > 0.008856 else 7.787 * y + 16 / 116
    return 116 * f - 16


@pytest.fixture(scope="module")
def synthetic_project(tmp_path_factory):
    project = tmp_path_factory.mktemp("synthetic_project")
    (project / "frames").mkdir()
    (project / "colormaps").mkdir()
    rng = np.random.default_rng(1)
    manifest, colormap = [], []
    for video, change in VIDEOS.items():
        stem = video.split(".")[0]
        for frame in range(FRAMES):
            image = f"{stem}_f{frame + 1:02d}.png"
            seconds = frame * 30
            manifest.append({"image": image, "video": video, "seconds": seconds,
                             "minutes": seconds / 60, "frame_number": frame + 1,
                             "capacity_frame": 0, "background": "white",
                             "video_recorded_at": "2026-06-01 10:00:00",
                             "met_sharpness_threshold": 1})
            grey = 0.45 + change * frame
            values = np.clip(grey + rng.normal(0, 0.003, POINTS), 0, 1)
            row = {"image": image}
            for i, v in enumerate(values, start=1):
                row[f"r_{i}"] = row[f"g_{i}"] = row[f"b_{i}"] = round(float(v), 5)
                row[f"x_{i}"], row[f"y_{i}"] = i, i
            colormap.append(row)
    for name, rows in (("frames/frames_manifest.csv", manifest),
                       ("colormaps/colormap_calib.csv", colormap)):
        with open(project / name, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    written, problems = gui.write_configured_r(
        str(project), {"num_passes": 7, "background": "white"}, str(project / "_generated"))
    assert problems == []
    return project


def run_r(rscript, project, script):
    generated = project / "_generated"
    run = subprocess.run([rscript, str(generated / script)], cwd=generated,
                         capture_output=True, text=True)
    assert run.returncode == 0, run.stdout + run.stderr
    return run.stdout


def read(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_cie_conversion(rscript_with_dplyr, synthetic_project):
    run_r(rscript_with_dplyr, synthetic_project, "CIE_conversion.R")
    rows = read(synthetic_project / "colormaps" / "LAB_average_white.csv")
    assert len(rows) == FRAMES * len(VIDEOS)
    first = next(r for r in rows if r["image"].startswith("steady_f01"))
    # A grey's L* matches the textbook formula; a and b are ~0 for grey.
    assert float(first["L_mean"]) == pytest.approx(srgb_to_lightness(0.45), abs=0.3)
    assert abs(float(first["a_mean"])) < 0.5 and abs(float(first["b_mean"])) < 0.5
    assert all(r["seconds"] != "" for r in rows)            # timing joined from the manifest


def test_rates_recover_the_direction_of_change(rscript_with_dplyr, synthetic_project):
    if not (synthetic_project / "colormaps" / "LAB_average_white.csv").exists():
        run_r(rscript_with_dplyr, synthetic_project, "CIE_conversion.R")
    gui.write_configured_r(str(synthetic_project), {"num_passes": 7, "background": "white"},
                           str(synthetic_project / "_generated"))
    run_r(rscript_with_dplyr, synthetic_project, "plasticity_rates.R")
    results = {r["video"]: r for r in read(synthetic_project / "results" /
                                           "plasticity_by_video.csv")}
    assert set(results) == set(VIDEOS)
    slope = {v: float(results[v]["slope_Lstar_per_min"]) for v in VIDEOS}
    assert slope["lighter.mp4"] > 1
    assert slope["darker.mp4"] < -1
    assert abs(slope["steady.mp4"]) < 0.5
    # The lightening is clearly real; no change is not.
    assert float(results["lighter.mp4"]["slope_p"]) < 0.001
    assert float(results["steady.mp4"]["slope_p"]) > 0.001
