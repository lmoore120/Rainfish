r"""
build_killifish_profile.py - make profiles\killifish.json, the built-in
"Fish" preset for find_animal_landmarks.py.

It holds the 43-landmark killifish scheme (7 primary landmarks with
9,1,2,9,1,3,11 semilandmarks between them) and a default shape: the
average of every usable landmarked frame in a landmarks.csv, lined up
(centred, scaled, rotated, all facing right) so it can be dropped onto a
frame where the outline can't be found.

    python build_killifish_profile.py trial_run\landmarks\landmarks.csv

Only needs re-running if you want the default shape rebuilt from more data.
"""
import argparse
import csv
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))

FIXED_NAMES = ["anterior", "anterior_dorsal_fin", "posterior_dorsal_fin",
               "dorsal_caudal_fin", "ventral_caudal_fin", "posterior_anal_fin",
               "anterior_anal_fin"]
SEMIS = [9, 1, 2, 9, 1, 3, 11]
TOTAL = len(FIXED_NAMES) + sum(SEMIS)


def normalise(points, front, back):
    """Centre on the centroid, unit centroid size, landmark 1 pointing right
    along +x. y runs down, as in the images."""
    points = points - points.mean(axis=0)
    points = points / np.sqrt((points ** 2).sum())
    axis = points[front].mean(axis=0) - points[back].mean(axis=0)
    angle = np.arctan2(axis[1], axis[0])
    c, s = np.cos(-angle), np.sin(-angle)
    return points @ np.array([[c, -s], [s, c]]).T


def mirrored_if_belly_up(points, dorsal, ventral):
    """After rotating to face right, the back should be above the belly
    (smaller y). A frame that came in facing left ends up upside down."""
    if points[dorsal, 1].mean() > points[ventral, 1].mean():
        points = points.copy()
        points[:, 1] = -points[:, 1]
    return points


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("landmarks_csv")
    parser.add_argument("--out", default=os.path.join(HERE, "profiles", "killifish.json"))
    options = parser.parse_args()

    shapes = []
    with open(options.landmarks_csv, newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            if str(row.get("usable", "1")) != "1":
                continue
            try:
                pts = np.array([[float(row[f"lm{i}_x"]), float(row[f"lm{i}_y"])]
                                for i in range(1, TOTAL + 1)])
            except (KeyError, ValueError):
                continue
            shape = normalise(pts, front=[0], back=[3, 4])
            shape = mirrored_if_belly_up(shape, dorsal=[1, 2], ventral=[5, 6])
            shapes.append(shape)
    if not shapes:
        raise SystemExit("No usable 43-landmark rows found.")

    # A few rounds of aligning to the running mean (simple Procrustes).
    mean = np.median(shapes, axis=0)
    for _ in range(5):
        aligned = []
        for shape in shapes:
            u, _, vt = np.linalg.svd(shape.T @ mean)
            rotation = u @ vt
            if np.linalg.det(rotation) < 0:     # never reflect here
                continue
            aligned.append(shape @ rotation)
        mean = np.median(aligned, axis=0)
        mean = normalise(mean, front=[0], back=[3, 4])

    profile = {
        "name": "Fish (killifish, 43 landmarks)",
        "fixed_names": FIXED_NAMES,
        "semis_per_segment": SEMIS,
        "force_body_curve_segments": [1, 5],
        "auto_detect": True,
        "facing": {"front": [1], "back": [4, 5]},
        "template": [[round(float(x), 5), round(float(y), 5)] for x, y in mean],
        "template_source": f"median of {len(aligned)} frames in "
                           f"{os.path.basename(options.landmarks_csv)}",
    }
    os.makedirs(os.path.dirname(options.out), exist_ok=True)
    with open(options.out, "w", encoding="utf-8") as handle:
        json.dump(profile, handle, indent=1)
    print(f"Wrote {options.out} from {len(aligned)} frames.")


if __name__ == "__main__":
    main()
