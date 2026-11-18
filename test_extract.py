"""Frame extraction (extract_frames.py) on a small made-up video, so the
test needs no real data: evenly spaced frames, the manifest, and the
optional extra frame."""
import csv
import os
import subprocess
import sys

import cv2
import numpy as np
import pytest

from conftest import CODE

FPS = 10
SECONDS = 8


@pytest.fixture(scope="module")
def video_folder(tmp_path_factory):
    """An 8-second, 10 fps video of sharp random texture, in a folder called
    'white' (extract_frames.py reads the background from the folder name)."""
    folder = tmp_path_factory.mktemp("project") / "white" / "videos"
    folder.mkdir(parents=True)
    path = str(folder / "test_clip.avi")
    writer = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"MJPG"), FPS, (320, 240))
    if not writer.isOpened():
        pytest.skip("this OpenCV build can't write test videos")
    rng = np.random.default_rng(0)
    for _ in range(FPS * SECONDS):
        writer.write(rng.integers(0, 256, (240, 320, 3), dtype=np.uint8))
    writer.release()
    return folder


def extract(video_folder, out, *extra):
    command = [sys.executable, os.path.join(CODE, "extract_frames.py"), str(video_folder),
               "--out", str(out), "--frames", "4", "--seconds", "6", *extra]
    run = subprocess.run(command, capture_output=True, text=True, cwd=CODE)
    assert run.returncode == 0, run.stdout + run.stderr
    with open(os.path.join(out, "frames_manifest.csv"), newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_evenly_spaced_frames(video_folder, tmp_path):
    rows = extract(video_folder, tmp_path / "frames", "--capacity-at", "0")
    assert len(rows) == 4
    seconds = [float(r["seconds"]) for r in rows]
    assert seconds == sorted(seconds)
    assert seconds[0] == pytest.approx(0, abs=0.6)
    assert seconds[-1] == pytest.approx(6, abs=0.6)
    for row in rows:
        assert os.path.exists(tmp_path / "frames" / row["image"])
        assert row["capacity_frame"] == "0"
        assert row["background"] == "white"
        assert row["video"] == "test_clip.avi"


def test_optional_extra_frame(video_folder, tmp_path):
    rows = extract(video_folder, tmp_path / "frames", "--capacity-at", "7.5")
    assert len(rows) == 5
    extra = [r for r in rows if r["capacity_frame"] == "1"]
    assert len(extra) == 1
    assert float(extra[0]["seconds"]) == pytest.approx(7.5, abs=0.6)


def test_extra_frame_past_the_end_is_skipped(video_folder, tmp_path):
    rows = extract(video_folder, tmp_path / "frames", "--capacity-at", "60")
    assert len(rows) == 4
    assert all(r["capacity_frame"] == "0" for r in rows)


def test_colormesh_specimen_factors_written(video_folder, tmp_path):
    extract(video_folder, tmp_path / "frames", "--capacity-at", "0")
    with open(tmp_path / "frames" / "specimen_factors.csv", newline="") as handle:
        factors = list(csv.DictReader(handle))
    assert len(factors) == 4
    assert list(factors[0])[0] == "image"          # Colormesh needs the image name first
