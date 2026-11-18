"""Shared setup for the Rainfish test suite.

Run everything from the repository root with:

    python -m pytest

Tests that need R (and the dplyr package) or a screen for the window are
skipped automatically when those aren't available, so the rest still run.
"""
import json
import os
import shutil
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CODE = os.path.join(ROOT, "files")
sys.path.insert(0, CODE)


# ------------------------------------------------------------------ R
def find_rscript():
    found = shutil.which("Rscript")
    if found:
        return found
    for base in (r"C:\Program Files\R", r"C:\Program Files (x86)\R"):
        if os.path.isdir(base):
            for version in sorted(os.listdir(base), reverse=True):
                candidate = os.path.join(base, version, "bin", "Rscript.exe")
                if os.path.exists(candidate):
                    return candidate
    return None


@pytest.fixture(scope="session")
def rscript():
    path = find_rscript()
    if path is None:
        pytest.skip("R is not installed")
    return path


@pytest.fixture(scope="session")
def rscript_with_dplyr(rscript):
    check = subprocess.run([rscript, "-e", "library(dplyr)"], capture_output=True, text=True)
    if check.returncode != 0:
        pytest.skip("the R package dplyr is not installed")
    return rscript


# ------------------------------------------------------------ profiles
@pytest.fixture
def custom_profile(tmp_path):
    """A small made-up animal: 5 primary landmarks, 22 semilandmarks."""
    import numpy as np
    names = ["snout", "neck", "tail_tip", "belly", "jaw"]
    semis = [4, 6, 6, 4, 2]
    # Default shape: an ellipse-ish loop, in landmark-number order.
    total = len(names) + sum(semis)
    angles = np.linspace(0, 2 * np.pi, total, endpoint=False)
    loop = np.c_[np.cos(angles), 0.35 * np.sin(angles)]
    order = [0]
    number = len(names)
    for segment, how_many in enumerate(semis):
        order += list(range(number, number + how_many))
        number += how_many
        if (segment + 1) % len(names):
            order.append(segment + 1)
    template = np.zeros((total, 2))
    template[order] = loop
    profile = {
        "name": "Test animal (27 landmarks)",
        "fixed_names": names,
        "semis_per_segment": semis,
        "force_body_curve_segments": [],
        "auto_detect": False,
        "facing": {"front": [1], "back": [3]},
        "template": template.round(5).tolist(),
    }
    path = tmp_path / "test_animal.json"
    path.write_text(json.dumps(profile), encoding="utf-8")
    return path


@pytest.fixture
def landmarker():
    """find_animal_landmarks with the fish profile active, restored afterwards
    (apply_profile changes module-wide settings)."""
    import find_animal_landmarks as lm
    lm.apply_profile(lm.DEFAULT_PROFILE)
    lm.NOT_REQUIRED.clear()
    yield lm
    lm.apply_profile(lm.DEFAULT_PROFILE)
    lm.NOT_REQUIRED.clear()
