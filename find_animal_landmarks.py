r"""
find_animal_landmarks.py
------------------------------------
A copy of find_fish_and_landmarks.py that works for any animal, using an
"animal profile" (a small JSON file in the profiles folder) to say how many
primary landmarks there are, what they're called, how many semilandmarks
go between each pair, and what the default shape looks like.

    python find_animal_landmarks.py frames --out landmarks --profile profiles\killifish.json

With no --profile it uses profiles\killifish.json, i.e. exactly the old
43-landmark killifish scheme, plus the default shape (G in the review
window, or scroll left in Previous). Profiles other than the killifish
one don't try to find the primary landmarks automatically (that detector
is tuned to killifish fins), so you click the primary landmarks or drop in
the default shape and drag it into place.

Make a new profile with make_animal_profile.py (or "Create your own..." in
the Rainfish window).

The original description of find_fish_and_landmarks.py follows.
------------------------------------
Finds the fish in an image or video frame (as the largest blob that looks
different from the background), samples the background color in a ring
immediately surrounding it, and then AUTOMATICALLY PLACES THE 43 LANDMARKS
that the ImageJ protocol asks you to place by hand - plus the scale bar
measurement and the 6 colour-standard points.

This is the original find_fish_and_local_background.py with the landmarking
workflow built on top. Everything the original script did, it still does.

--------------------------------------------------------------------------
WHAT WAS ALREADY HERE (unchanged)
--------------------------------------------------------------------------
Handles the "lightbox" vignette: depending on camera position/zoom, the
video sometimes shows the circular edge of the lightbox around the tank,
with everything outside that circle being irrelevant (dark table, room,
etc. - not part of the actual experiment). When that circle is visible,
this detects it and restricts ALL analysis (background color, fish
detection) to inside it. When no circle is visible (camera zoomed in
tighter), it just uses the whole frame - no assumption either way is
hard-coded, it's detected per frame.

  1. Tries to find a circular edge (the lightbox boundary) in the frame.
  2. Figures out the background color (white or black) by looking at the
     most common brightness WITHIN the relevant area.
  3. Finds every blob of pixels that looks meaningfully different from
     that background.
  4. Ignores blobs touching the very edge of the relevant area.
  5. Picks the single largest remaining blob and calls that the fish.
  6. Draws a ring a set distance around the fish's outline and samples
     the color WITHIN that ring (excluding the fish itself).

--------------------------------------------------------------------------
WHAT IS NEW - THE IMAGEJ PROTOCOL, AUTOMATED
--------------------------------------------------------------------------
Step (b)/(c) - scale bar:
     Looks for a long thin solid bar (the 10 mm scale bar) in the image,
     measures its length in pixels, and writes that number into the
     results spreadsheet - this is the number the protocol tells you to
     paste into the 5th column of Excel. Also converts it to px/mm.
     If auto-detection is wrong or misses, you can click the two ends
     yourself, or pass --scale-px if you already know the number.

Step (d) - the 43 fish landmarks:
     The fish outline found in step 5 above is resampled into a smooth,
     evenly-spaced closed curve. The 7 FIXED landmarks are then found
     from the shape itself:
         1. Anterior            - the tip of the snout (the far end of
                                  the long body axis, away from the tail)
         2. Anterior dorsal fin - the front notch where the dorsal fin
                                  meets the back (a concave corner)
         3. Posterior dorsal fin- the rear notch of the dorsal fin
         4. Dorsal caudal fin   - the upper corner of the tail fin
         5. Ventral caudal fin  - the lower corner of the tail fin
         6. Posterior anal fin  - the rear notch of the anal fin
         7. Anterior anal fin   - the front notch of the anal fin
     The remaining 36 are then placed as equally-spaced SEMILANDMARKS
     along the outline between consecutive fixed landmarks, in exactly
     the counts the protocol specifies:
         1 -> 2 : landmarks 8-16   (9 points)
         2 -> 3 : landmark  17     (1 point)
         3 -> 4 : landmarks 18-19  (2 points)
         4 -> 5 : landmarks 20-28  (9 points)
         5 -> 6 : landmark  29     (1 point)
         6 -> 7 : landmarks 30-32  (3 points)
         7 -> 1 : landmarks 33-43  (11 points)
     Total: 7 + 36 = 43, numbered and ordered the same way you would
     have clicked them with the multi-point tool.

Step (e) - the 6 colour-standard landmarks:
     Finds the red, green and blue patches by colour, fits a line through
     them, and extrapolates back along that line to the mid grey, light
     grey and white patches (this assumes the 6 patches are in a straight
     evenly-spaced row, which is how colour standards are printed). They
     come out in protocol order: white, light grey, mid grey, red, green,
     blue - i.e. points 44-49 if you think of them as continuing the same
     multi-point series. The actual measured colour of each patch is also
     written to the spreadsheet so you can colour-correct with it later.
     If auto-detection fails you can click the 6 patches yourself, and
     with --colour-standard-from-first you only have to do it once for a
     whole folder.

--------------------------------------------------------------------------
IMPORTANT - PLEASE READ
--------------------------------------------------------------------------
Automatic placement of fin-insertion landmarks is a genuinely hard problem
and this WILL get some frames wrong - a torn fin, an overlapping pectoral
fin, a fish curled towards the camera, or a fin held flat against the body
can all move a notch or hide it. Treat the output as a first pass, not as
finished data.

That is what the built-in review window is for. Unless you pass
--no-review, each image opens in a window where you can drag any landmark
to where it belongs before it is saved. Landmark 1 is always the snout,
so if the whole ring looks rotated, fix landmark 1 first and press R to
re-flow the semilandmarks around it.

--------------------------------------------------------------------------
HOW TO RUN IT
--------------------------------------------------------------------------
  # a folder of stills (the usual case for landmarking)
  python find_fish_and_landmarks.py "path\to\your\image_folder"

  # a single image
  python find_fish_and_landmarks.py "path\to\image.jpg"

  # a video, exactly like the original script
  python find_fish_and_landmarks.py "path\to\your\video.mp4"

  # click the colour standard once and reuse it for the whole folder
  python find_fish_and_landmarks.py "folder" --colour-standard-from-first

  # no windows at all (headless / batch)
  python find_fish_and_landmarks.py "folder" --no-review

REVIEW WINDOW CONTROLS
  left-click + drag  move the nearest landmark
  R                  re-flow semilandmarks from the current 7 fixed points
  S                  switch to scale-bar mode, then click its two ends
  C                  switch to colour-standard mode, then click the 6
                     patches in order (white, light grey, mid grey,
                     red, green, blue)
  F                  back to fish-landmark mode
  U                  undo the last drag
  ENTER / N          accept this image and move on
  Q / ESC            quit

OUTPUTS (all in the folder given by --out, default "landmark_output")
  landmarks.csv                     one row per image: scale bar in
                                    pixels, px/mm, all 43 fish landmarks,
                                    all 6 colour-standard points and
                                    their measured colours, and the
                                    original local-background readings
  <image>_landmarks.tps             the 43 fish landmarks, TPS format
                                    (opens in tpsDig / geomorph / MorphoJ)
  <image>_landmarks_with_std.tps    all 49 points, matching the manual
                                    ImageJ multi-point series
  <image>_points.txt                plain XY list, same format ImageJ's
                                    Measure gives you
  debug_frames/<image>.png          annotated picture so you can see
                                    exactly what was found
"""

import os
import re
import sys
import csv
import glob
import json
import argparse

import cv2
import numpy as np

DEBUG_FOLDER = "debug_frames"

# How different (in grayscale brightness, 0-255) a pixel needs to be from
# the background to count as "not background."
DIFFERENCE_THRESHOLD = 40

# Caudal, anal and dorsal fins are often nearly transparent against a white
# lightbox, so they fall below DIFFERENCE_THRESHOLD and get chopped off the
# outline - which then makes it impossible to landmark the tail. After the
# solid body is found, the script does a second, much more sensitive pass
# and adds back any faint pixels that are CONNECTED to that body. Requiring
# a connection is what stops the low threshold from also dragging in
# water marks, scratches and shadows elsewhere in the frame.
# Measured on the hand-landmarked reference photo, sweeping this value and
# comparing the 7 detected landmarks against the manual ones (as a % of
# body length):
#     core only (no recovery)  mean 4.0%  worst  9.8%
#     30                       mean 2.9%  worst  5.0%   <- best
#     22                       mean 5.0%  worst 10.8%
#     12                       mean 5.5%  worst  8.6%
# Too sensitive is actively WORSE than not trying at all: on a mottled or
# textured background the outline balloons past the fish and every landmark
# rides out with it. 30 is the default because it captured the translucent
# fins on the reference photo without leaking. If your background is
# cleaner you can lower it to pick up fainter fin edges - check the debug
# image and make sure the outline still hugs the fish.
FAINT_FIN_THRESHOLD = 30

# Safety catch: if the sensitive pass balloons the fish to more than this
# multiple of the solid body's area, it has clearly leaked into the
# background, so the solid body is kept instead.
FAINT_FIN_MAX_GROWTH = 6.0

# How many pixels wide the sampling ring around the fish should be. This
# controls the actual background-colour MEASUREMENT and is unrelated to
# how thick it's drawn on the debug image (see RING_DISPLAY_WIDTH below).
RING_WIDTH = 15

# How many pixels wide to DRAW the ring outline on the annotated debug
# image. This is just for visibility, so it defaults to something much
# thinner than the sampling ring itself - a thin outline is easy to see
# without obscuring the fish. Set to 0, or pass --no-ring-overlay, to
# leave it off entirely.
RING_DISPLAY_WIDTH = 0

# How close to the relevant area's edge (in pixels) counts as "touching
# the border" and gets excluded as a likely lightbox-rim/light-source
# artifact rather than the fish itself.
BORDER_MARGIN = 5

# ---------------------------------------------------------------------
# Landmark protocol settings
# ---------------------------------------------------------------------

# The 7 fixed landmarks, in the order the protocol lists them.
FIXED_LANDMARK_NAMES = [
    "anterior",
    "anterior_dorsal_fin",
    "posterior_dorsal_fin",
    "dorsal_caudal_fin",
    "ventral_caudal_fin",
    "posterior_anal_fin",
    "anterior_anal_fin",
]

# How many evenly-spaced semilandmarks go between each consecutive pair of
# fixed landmarks. Index 0 is the stretch from landmark 1 to landmark 2,
# and the last entry wraps from landmark 7 back round to landmark 1.
#   1->2 : 9  (numbers 8-16)     4->5 : 9  (numbers 20-28)
#   2->3 : 1  (number  17)       5->6 : 1  (number  29)
#   3->4 : 2  (numbers 18-19)    6->7 : 3  (numbers 30-32)
#                                7->1 : 11 (numbers 33-43)
SEMILANDMARKS_PER_SEGMENT = [9, 1, 2, 9, 1, 3, 11]

# Segments that must always cut across the body under the fin base rather
# than trace the fin's own outer margin: 2->3 (landmark 17) and 6->7
# (landmarks 30-32). 0-indexed.
FORCE_BODY_CURVE_SEGMENTS = {1, 5}


def _perimeter_order():
    """The order the landmarks run in AROUND THE FISH, which is not their
    numerical order.

    Numbering goes 1-7 for the fixed anatomical points and 8-43 for the
    semilandmarks between them, so walking the outline actually goes
    1, 8..16, 2, 17, 3, 18, 19, 4, 20..28, 5, 29, 6, 30..32, 7, 33..43.
    This is the same sequence as perimeter.map in the R script.

    Anything that treats the landmarks as a SHAPE - drawing the outline,
    checking whether it crosses itself - has to use this order. Joining
    them 1,2,3,... instead draws lines that jump back and forth across the
    body, which looks like a tangled mess even when the data is perfectly
    correct.

    Returned as 0-based indices into the landmark array."""
    order = [0]                                    # landmark 1
    number = len(FIXED_LANDMARK_NAMES)             # semilandmarks start at 8
    for segment, how_many in enumerate(SEMILANDMARKS_PER_SEGMENT):
        for _ in range(how_many):
            order.append(number)
            number += 1
        # then the fixed landmark that ends this segment
        end_landmark = (segment + 1) % len(FIXED_LANDMARK_NAMES)
        if end_landmark != 0:
            order.append(end_landmark)
    return order


PERIMETER_ORDER = _perimeter_order()
TOTAL_LANDMARKS = len(FIXED_LANDMARK_NAMES) + sum(SEMILANDMARKS_PER_SEGMENT)  # 43

# The colour standard, in the order the protocol lists it.
COLOUR_STANDARD_NAMES = ["white", "light_grey", "mid_grey", "red", "green", "blue"]

# Roughly what the three chromatic patches should look like in BGR. Only
# used to recognise them - the script reports whatever colour it actually
# measures, it never assumes these values are correct.
CHROMATIC_REFERENCE_BGR = {"red": (40, 40, 190), "green": (60, 160, 60), "blue": (180, 80, 40)}

# The scale bar is 11.5 mm.
SCALE_BAR_MM = 11.5

# Fallback for videos with no scale bar in frame: the known real-world
# WIDTH of a single colour-standard square (the printed edge length of one
# patch). Used to derive px/mm by detecting the squares around your 6
# colour-standard points, when no scale bar has been set for that image.
# This does not have to match SCALE_BAR_MM - they are different physical
# things that happen to be the same size here.
COLOUR_STANDARD_SQUARE_MM = 11.5

# How many points the fish outline gets resampled to before landmarking.
# Higher = smoother and more precise, slower. 720 is plenty.
CONTOUR_RESAMPLE_POINTS = 720

# How much to smooth the outline before looking for fin notches, as a
# fraction of the outline's total length. Too little and pixel jaggies
# look like notches; too much and real notches get rounded away.
CONTOUR_SMOOTH_FRACTION = 0.012

# The dorsal and anal fins are found as places where the outline bulges
# away from the smooth line of the body - NOT as sharp corners. Fin bases
# are often soft, while heads and gill covers have sharper dents that
# would otherwise win a "sharpest corner" contest and drag landmark 2 far
# too far forward.
FIN_PROFILE_BINS = 240
FIN_BASELINE_WINDOW_FRACTION = 0.30   # wider than a fin base, narrower than the body arch
FIN_MIN_EXCESS_FRACTION = 0.06        # bulge must exceed 6% of body depth to count as a fin
FIN_NOTCH_SNAP_FRACTION = 0.05        # then snap to the nearest real crease within 5% of body length

# ---------------------------------------------------------------------
# WHERE THE FINS ACTUALLY ARE ON THIS SPECIES
# ---------------------------------------------------------------------
# Measured directly off the hand-landmarked reference image, as a fraction
# of body length back from the snout, where body length runs from the snout
# (landmark 1) to the caudal fin insertion (the midline between landmarks
# 4 and 5). The caudal fin fan extends BEYOND 1.0 - landmarks 4 and 5 sit
# where the fin meets the body, not out at the corners of the fan, and
# semilandmarks 20-28 wrap around the fan outside them.
#
# Without these, fin bases get found by looking for the strongest feature
# anywhere along the body, and on this species that loses: the nape and
# gill cover make sharper, stronger features than the dorsal fin origin,
# which sits unusually far back at 0.80. Searching only near the expected
# position fixes that.
FIN_PRIORS = {
    "anterior_dorsal_fin": 0.798,
    "posterior_dorsal_fin": 0.879,
    "posterior_anal_fin": 0.849,
    "anterior_anal_fin": 0.649,
}

# How far either side of the expected position to search, as a fraction of
# body length. Wide enough to absorb real between-fish variation and a
# bent body; narrow enough to exclude the head features that were winning
# before. Raise it if your fish vary more than this one suggests.
FIN_PRIOR_TOLERANCE = 0.11

# Set False to ignore the priors and go back to picking the strongest
# feature anywhere along the body (useful if you switch species).
USE_FIN_PRIORS = True

IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp")
VIDEO_EXTENSIONS = (".mp4", ".avi", ".mov", ".mkv", ".m4v", ".wmv", ".mpg", ".mpeg")


# =====================================================================
# ORIGINAL FUNCTIONS - unchanged
# =====================================================================

def find_vignette_circle(frame):
    """Look for a circular edge (the lightbox boundary) in the frame.
    Returns (center_x, center_y, radius) in full-resolution coordinates,
    or None if no confident circle was found - which is expected and
    fine for footage where the camera is zoomed in past the lightbox
    edge."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape

    scale = 600 / max(h, w)  # work on a smaller image for speed/stability
    small = cv2.resize(gray, None, fx=scale, fy=scale)
    blurred = cv2.medianBlur(small, 9)

    circles = cv2.HoughCircles(
        blurred, cv2.HOUGH_GRADIENT, dp=1.5, minDist=300,
        param1=80, param2=60,
        minRadius=int(min(small.shape) * 0.3),
        maxRadius=int(min(small.shape) * 0.7),
    )

    if circles is None:
        return None

    x, y, r = circles[0][0]
    return (x / scale, y / scale, r / scale)


def get_relevant_mask(frame, circle):
    """A mask of which pixels actually matter - everything, if there's no
    lightbox circle in this frame, or just the inside of the circle
    (slightly inset from its edge) if there is one."""
    h, w = frame.shape[:2]
    if circle is None:
        return np.full((h, w), 255, dtype=np.uint8)

    cx, cy, r = circle
    mask = np.zeros((h, w), dtype=np.uint8)
    # Inset slightly so the bright rim itself isn't treated as part of
    # the scene to analyze.
    cv2.circle(mask, (int(cx), int(cy)), int(r * 0.92), 255, thickness=cv2.FILLED)
    return mask


def most_common_brightness(frame, relevant_mask, bin_size=8):
    """Find the most common grayscale brightness within the relevant
    area only - almost always the background, since it fills most of
    that area."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    pixels = gray[relevant_mask == 255]
    if len(pixels) == 0:
        return 128  # shouldn't happen, but don't crash if it does
    histogram, _ = np.histogram(pixels, bins=256 // bin_size, range=(0, 256))
    most_common_bin = np.argmax(histogram)
    return most_common_bin * bin_size + bin_size // 2


def touches_border(x, y, w, h, relevant_mask, margin=BORDER_MARGIN):
    """True if this box touches the edge of the relevant area - either
    the frame's own edge, or the edge of the lightbox circle mask."""
    frame_h, frame_w = relevant_mask.shape
    if x <= margin or y <= margin or x + w >= frame_w - margin or y + h >= frame_h - margin:
        return True
    # Also check against the mask's own boundary (the circle edge, if
    # there is one) by seeing if the box's border sits on mask pixels
    # that are right next to "outside the mask."
    eroded = cv2.erode(relevant_mask, np.ones((margin * 2 + 1, margin * 2 + 1), np.uint8))
    box_edge_ring = np.zeros_like(relevant_mask)
    cv2.rectangle(box_edge_ring, (x, y), (x + w, y + h), 255, thickness=margin)
    return bool(np.any((box_edge_ring == 255) & (eroded == 0) & (relevant_mask == 255)))


def find_fish(frame, background_brightness, relevant_mask, near_points=None):
    """Return (contour, bounding_box) for the fish, or (None, None) if
    nothing fish-like was found in this frame.

    near_points, when given, is where the fish was in the previous frame.
    Between frames 25 seconds apart the fish moves, but not usually far,
    and certainly not from the bottom of the tank to the top. Blobs near
    the previous position are therefore strongly preferred, which stops
    the detector latching onto clips, reflections and the tank rim at the
    top of the frame when the fish is sitting at the bottom."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    diff = cv2.absdiff(gray, np.full_like(gray, background_brightness))
    _, mask = cv2.threshold(diff, DIFFERENCE_THRESHOLD, 255, cv2.THRESH_BINARY)
    mask = cv2.bitwise_and(mask, relevant_mask)  # ignore anything outside the relevant area

    # Clean up small speckles (sensor noise, compression artifacts) so
    # they don't get treated as tiny separate blobs.
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None, None

    candidates = []
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        if touches_border(x, y, w, h, relevant_mask):
            continue  # likely a lightbox rim/light source, not the fish
        area = cv2.contourArea(c)
        if area < 20:
            continue  # too small to be the fish - just noise
        candidates.append((area, c, (x, y, w, h)))

    if not candidates:
        return None, None

    if near_points is not None and len(near_points) >= 2:
        near_points = np.asarray(near_points, dtype=np.float64)
        previous_centre = near_points.mean(axis=0)
        previous_size = max(np.ptp(near_points[:, 0]), np.ptp(near_points[:, 1]), 1.0)

        scored = []
        for area, contour, box in candidates:
            x, y, w, h = box
            centre = np.array([x + w / 2.0, y + h / 2.0])
            distance = float(np.linalg.norm(centre - previous_centre))
            # Within about a body length of where it was is unremarkable;
            # several body lengths away is almost certainly a different
            # object, so it gets heavily penalised rather than excluded
            # outright (a fish can dart).
            closeness = 1.0 / (1.0 + (distance / previous_size) ** 2)
            scored.append((area * (0.05 + closeness), contour, box))
        scored.sort(key=lambda item: item[0], reverse=True)
        _, best_contour, best_box = scored[0]
        return best_contour, best_box

    candidates.sort(key=lambda item: item[0], reverse=True)
    _, best_contour, best_box = candidates[0]
    return best_contour, best_box


def recover_faint_fins(frame, background_brightness, relevant_mask, core_contour,
                       faint_threshold=FAINT_FIN_THRESHOLD):
    """Grow the fish outline to include translucent fins.

    find_fish() uses a fairly high contrast threshold, which is right for
    locating the solid body but throws away the caudal and anal fins when
    they're near-transparent against a white lightbox. That's fatal for
    landmarking, because landmarks 4, 5 and everything between them live
    on the tail - if the tail isn't in the outline, nothing can put points
    on it.

    So: run the difference test again at a much more sensitive threshold,
    then keep only the parts that are physically CONNECTED to the solid
    body already found. Faint marks elsewhere in the frame are discarded
    because they don't touch the fish.

    Returns a new contour, or the original one if the sensitive pass
    didn't work out."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    core_mask = np.zeros(gray.shape, dtype=np.uint8)
    cv2.drawContours(core_mask, [core_contour], -1, 255, thickness=cv2.FILLED)
    core_area = float(np.count_nonzero(core_mask))
    if core_area == 0:
        return core_contour

    diff = cv2.absdiff(gray, np.full_like(gray, background_brightness))
    _, faint = cv2.threshold(diff, faint_threshold, 255, cv2.THRESH_BINARY)
    faint = cv2.bitwise_and(faint, relevant_mask)

    # Close small gaps so a fin that fades in and out still joins up with
    # the body instead of breaking into disconnected flecks.
    faint = cv2.morphologyEx(faint, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    combined = cv2.bitwise_or(faint, core_mask)

    # Keep only blobs that include part of the solid body.
    count, labels = cv2.connectedComponents(combined)
    touching_body = np.unique(labels[core_mask == 255])
    touching_body = touching_body[touching_body > 0]
    if len(touching_body) == 0:
        return core_contour
    grown = np.isin(labels, touching_body).astype(np.uint8) * 255

    if np.count_nonzero(grown) > FAINT_FIN_MAX_GROWTH * core_area:
        return core_contour  # leaked into the background - don't trust it

    grown = cv2.morphologyEx(grown, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    contours, _ = cv2.findContours(grown, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return core_contour
    return max(contours, key=cv2.contourArea)


def detect_outline_near_points(frame, points, background_brightness=None,
                               margin_fraction=0.25, threshold=None):
    """Find the fish's real outline in the neighbourhood of some points.

    Whole-frame detection picks the biggest blob that differs from the
    background, and on this footage that is regularly something at the top
    of the frame - a clip, a reflection, the tank rim - rather than the
    fish. But once you have told it roughly where the fish is (by clicking
    the 7 landmarks, or from where the fish was in the previous frame),
    the search can be restricted to that neighbourhood, where the fish is
    by far the most likely thing to be.

    Returns a contour in FULL-FRAME coordinates, or None."""
    if points is None or len(points) < 2:
        return None
    points = np.asarray(points, dtype=np.float64)

    height, width = frame.shape[:2]
    x0, y0 = points[:, 0].min(), points[:, 1].min()
    x1, y1 = points[:, 0].max(), points[:, 1].max()
    pad_x = max(20.0, (x1 - x0) * margin_fraction)
    pad_y = max(20.0, (y1 - y0) * margin_fraction)
    left = int(max(0, x0 - pad_x))
    top = int(max(0, y0 - pad_y))
    right = int(min(width, x1 + pad_x))
    bottom = int(min(height, y1 + pad_y))
    if right - left < 10 or bottom - top < 10:
        return None

    crop = frame[top:bottom, left:right]
    mask = np.full(crop.shape[:2], 255, dtype=np.uint8)
    if background_brightness is None:
        background_brightness = most_common_brightness(crop, mask)

    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    diff = cv2.absdiff(gray, np.full_like(gray, int(background_brightness)))

    # Try the normal threshold first, then more sensitive ones - inside a
    # crop centred on the fish there is little else to pick up, so a lower
    # threshold is much safer here than it would be frame-wide.
    for attempt in ([threshold] if threshold else
                    [DIFFERENCE_THRESHOLD, DIFFERENCE_THRESHOLD * 0.6,
                     DIFFERENCE_THRESHOLD * 0.35]):
        _, binary = cv2.threshold(diff, int(attempt), 255, cv2.THRESH_BINARY)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            continue

        # The right blob is the one that actually covers the points you
        # gave, not simply the largest.
        local_points = points - np.array([left, top])
        best, best_score = None, -1.0
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < 50:
                continue
            inside = sum(1 for p in local_points
                         if cv2.pointPolygonTest(contour, (float(p[0]), float(p[1])),
                                                 True) > -0.05 * max(crop.shape))
            score = inside + min(1.0, area / (crop.shape[0] * crop.shape[1]))
            if score > best_score:
                best, best_score = contour, score
        # Require it to sit under at least half the points, otherwise it's
        # some other object that happened to be in the crop.
        if best is not None and best_score >= len(local_points) * 0.5:
            return best + np.array([[left, top]])

    return None


def sample_ring_around_fish(frame, fish_contour, fish_box, relevant_mask):
    """Sample the color in a ring around (but not touching) the fish,
    staying within the relevant area."""
    fish_mask = np.zeros(frame.shape[:2], dtype=np.uint8)
    cv2.drawContours(fish_mask, [fish_contour], -1, 255, thickness=cv2.FILLED)

    kernel = np.ones((RING_WIDTH * 2 + 1, RING_WIDTH * 2 + 1), np.uint8)
    expanded_mask = cv2.dilate(fish_mask, kernel)
    ring_mask = cv2.subtract(expanded_mask, fish_mask)
    ring_mask = cv2.bitwise_and(ring_mask, relevant_mask)

    ring_pixels_bgr = frame[ring_mask == 255]
    if len(ring_pixels_bgr) == 0:
        return None

    median_bgr = np.median(ring_pixels_bgr, axis=0)
    median_gray = cv2.cvtColor(np.uint8([[median_bgr]]), cv2.COLOR_BGR2GRAY)[0][0]
    return {
        "bgr": tuple(int(v) for v in median_bgr),
        "brightness": int(median_gray),
        "ring_mask": ring_mask,
    }


def get_sample_frames(video_path, how_many=10):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise IOError(f"Could not open video file: {video_path}")

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frames = []
    if total_frames <= 0:
        count = 0
        while True:
            success, frame = cap.read()
            if not success:
                break
            if count % 30 == 0:
                frames.append(frame)
            count += 1
    else:
        step = max(1, total_frames // how_many)
        for frame_index in range(0, total_frames, step):
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
            success, frame = cap.read()
            if success:
                frames.append(frame)
            if len(frames) >= how_many:
                break

    cap.release()
    return frames[:how_many]


# =====================================================================
# NEW - OUTLINE GEOMETRY HELPERS
# =====================================================================

def contour_to_points(contour):
    """OpenCV contour -> a plain Nx2 float array of (x, y)."""
    return contour.reshape(-1, 2).astype(np.float64)


def resample_closed_curve(points, n_points):
    """Respace a closed outline so its points are evenly spread along its
    length. This matters because OpenCV contour points are packed densely
    on curves and sparsely on straight runs - evenly spaced points make
    'put a semilandmark a third of the way along' mean what you'd expect."""
    loop = np.vstack([points, points[:1]])
    segment_lengths = np.linalg.norm(np.diff(loop, axis=0), axis=1)
    distance_along = np.concatenate([[0.0], np.cumsum(segment_lengths)])
    total_length = distance_along[-1]
    if total_length <= 0:
        raise ValueError("Outline has zero length.")

    wanted = np.linspace(0.0, total_length, n_points, endpoint=False)
    x = np.interp(wanted, distance_along, loop[:, 0])
    y = np.interp(wanted, distance_along, loop[:, 1])
    return np.column_stack([x, y])


def smooth_closed_curve(points, window):
    """Circular moving average - rounds off pixel-level jaggies so that
    only real shape features survive."""
    window = max(3, int(window) | 1)  # force odd, at least 3
    half = window // 2
    padded = np.vstack([points[-half:], points, points[:half]])
    kernel = np.ones(window) / window
    x = np.convolve(padded[:, 0], kernel, mode="valid")
    y = np.convolve(padded[:, 1], kernel, mode="valid")
    return np.column_stack([x, y])


def point_at_fractional_index(points, fractional_index):
    """Position part-way between two outline points, wrapping round the
    end of the array."""
    n = len(points)
    f = fractional_index % n
    i0 = int(np.floor(f)) % n
    i1 = (i0 + 1) % n
    blend = f - np.floor(f)
    return points[i0] * (1.0 - blend) + points[i1] * blend


def signed_turn_angle(points, step):
    """How sharply the outline turns at each point, and which way. Positive
    and negative mean opposite directions of turn; which one is 'into the
    body' depends on whether the outline runs clockwise or anticlockwise,
    so callers should use concavity() below rather than this directly."""
    previous = np.roll(points, step, axis=0)
    following = np.roll(points, -step, axis=0)
    incoming = points - previous
    outgoing = following - points
    cross = incoming[:, 0] * outgoing[:, 1] - incoming[:, 1] * outgoing[:, 0]
    magnitude = np.linalg.norm(incoming, axis=1) * np.linalg.norm(outgoing, axis=1) + 1e-9
    return np.arcsin(np.clip(cross / magnitude, -1.0, 1.0))


def concavity(points, step):
    """Positive where the outline dents INWARDS (a notch, like the crease
    where a fin meets the body), near zero on flat stretches, negative on
    outward corners like a fin tip. Works out the outline's winding
    direction on the fly, so it doesn't matter which way round it runs."""
    turn = signed_turn_angle(points, step)
    winding = np.sign(np.sum(turn)) or 1.0
    return -winding * turn


def find_local_peaks(values, min_separation, how_many):
    """Pick the strongest peaks, refusing to pick two that sit almost on
    top of each other (which would otherwise return the same notch twice)."""
    order = np.argsort(values)[::-1]
    chosen = []
    n = len(values)
    for index in order:
        if values[index] <= 0:
            break
        too_close = False
        for already in chosen:
            gap = abs(index - already)
            gap = min(gap, n - gap)  # it's a loop, so wrap round
            if gap < min_separation:
                too_close = True
                break
        if not too_close:
            chosen.append(int(index))
        if len(chosen) >= how_many:
            break
    return chosen


def _grey_open(values, window):
    """Morphological opening of a 1-D profile: a sliding minimum followed
    by a sliding maximum. Removes any bump narrower than `window` while
    leaving broad shape alone - so it strips the fin off the profile and
    leaves the body's own back/belly line behind."""
    n = len(values)
    half = max(1, window // 2)
    eroded = np.empty(n)
    for i in range(n):
        eroded[i] = values[max(0, i - half):min(n, i + half + 1)].min()
    opened = np.empty(n)
    for i in range(n):
        opened[i] = eroded[max(0, i - half):min(n, i + half + 1)].max()
    return opened


def find_fin_base(along, height, on_this_side, body_depth, prefer_posterior=False):
    """Find where a fin joins the body, by looking for where the outline
    bulges out past the body's own smooth profile.

    along            - position of each outline point down the body axis
    height           - how far each point sticks out on the side of interest
    on_this_side     - which points are eligible (right side, not the tail)
    prefer_posterior - for the anal fin: break ties towards the rear, so a
                       pelvic fin doesn't get mistaken for the anal fin

    Returns (along_at_front_of_fin, along_at_back_of_fin), or None if no
    part of the outline stands clearly proud of the body."""
    if np.count_nonzero(on_this_side) < 10:
        return None

    lo, hi = along.min(), along.max()
    edges = np.linspace(lo, hi, FIN_PROFILE_BINS + 1)
    which = np.clip(np.digitize(along, edges) - 1, 0, FIN_PROFILE_BINS - 1)

    # How far the outline reaches on this side, at each point down the body.
    profile = np.full(FIN_PROFILE_BINS, np.nan)
    for b in range(FIN_PROFILE_BINS):
        selected = height[on_this_side & (which == b)]
        if len(selected):
            profile[b] = selected.max()
    filled = np.isfinite(profile)
    if filled.sum() < 10:
        return None
    profile = np.interp(np.arange(FIN_PROFILE_BINS), np.where(filled)[0], profile[filled])

    # Strip the fin off to recover the body line, then find where the real
    # outline rises above it.
    baseline = _grey_open(profile, int(FIN_PROFILE_BINS * FIN_BASELINE_WINDOW_FRACTION))
    excess = profile - baseline
    over = excess > (FIN_MIN_EXCESS_FRACTION * body_depth)
    if not np.any(over):
        return None

    runs, start = [], None
    for b in range(FIN_PROFILE_BINS):
        if over[b] and start is None:
            start = b
        elif not over[b] and start is not None:
            runs.append((start, b - 1))
            start = None
    if start is not None:
        runs.append((start, FIN_PROFILE_BINS - 1))
    if not runs:
        return None

    scored = [(excess[a:b + 1].sum(), a, b) for a, b in runs]
    best_score = max(s for s, _, _ in scored)
    if prefer_posterior:
        # Among bulges that are genuinely substantial, take the rearmost -
        # that's the anal fin, not the pelvics.
        good = [r for r in scored if r[0] >= 0.6 * best_score]
        _, a, b = max(good, key=lambda r: r[2])
    else:
        _, a, b = max(scored, key=lambda r: r[0])

    return float(edges[a]), float(edges[b + 1])


def catmull_rom_closed(points, samples_per_segment=120):
    """A smooth closed curve passing exactly through every one of the given
    points. Used when you place the 7 fixed landmarks by hand and the
    detected outline can't be trusted to carry the semilandmarks - the
    curve then follows your own points instead."""
    points = np.asarray(points, dtype=np.float64)
    n = len(points)
    curve = []
    for i in range(n):
        p0, p1 = points[(i - 1) % n], points[i]
        p2, p3 = points[(i + 1) % n], points[(i + 2) % n]
        for s in range(samples_per_segment):
            t = s / samples_per_segment
            t2, t3 = t * t, t * t * t
            curve.append(0.5 * ((2 * p1)
                                + (-p0 + p2) * t
                                + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                                + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    return np.array(curve)


def body_axis(points):
    """The fish's long axis, found by principal component analysis of its
    outline. Returns the centre, the along-body direction, and the
    across-body direction."""
    centre = points.mean(axis=0)
    centred = points - centre
    _, _, vectors = np.linalg.svd(centred, full_matrices=False)
    along = vectors[0] / np.linalg.norm(vectors[0])
    across = np.array([-along[1], along[0]])
    return centre, along, across


def width_profile(along_axis, across_axis, n_bins=44):
    """How tall the fish is at each point down its length. The dip in this
    profile near one end is the caudal peduncle - the narrow wrist just
    before the tail fin flares back out - which is how the script works out
    which end is the head."""
    edges = np.linspace(along_axis.min(), along_axis.max(), n_bins + 1)
    which_bin = np.clip(np.digitize(along_axis, edges) - 1, 0, n_bins - 1)
    widths = np.zeros(n_bins)
    for b in range(n_bins):
        selected = across_axis[which_bin == b]
        if len(selected) > 1:
            widths[b] = selected.max() - selected.min()
    return edges, widths


def _tail_likelihood(widths_from_centre_outwards):
    """Score how tail-like one end of the fish is. A tail narrows to the
    peduncle and then flares back out into the caudal fin, so the width
    profile goes down-then-up. A snout just narrows to a point and stops.
    Also rewards a blunt, wide extreme tip (two caudal fin corners) over a
    pointed one (a snout)."""
    widths = widths_from_centre_outwards
    positive = widths[widths > 0]
    if len(positive) < 4:
        return 0.0

    flare = 0.0
    for i in range(1, len(positive) - 1):
        waist = positive[i]
        if waist <= 0:
            continue
        widest_beyond = positive[i + 1:].max()
        flare = max(flare, widest_beyond / waist)

    tip_bluntness = positive[-max(1, len(positive) // 12):].mean() / (positive.max() + 1e-9)
    return flare + 2.0 * tip_bluntness


def head_is_at_low_end(along_axis, across_axis):
    """True if the snout sits at the low end of the body axis."""
    _, widths = width_profile(along_axis, across_axis)
    middle = len(widths) // 2
    low_end = widths[:middle][::-1]   # ordered from the middle outwards
    high_end = widths[middle:]
    return _tail_likelihood(high_end) >= _tail_likelihood(low_end)


def find_peduncle_position(along_axis, across_axis, tail_at_high_end=True):
    """Where along the body the caudal peduncle (the narrow wrist before
    the tail fin) sits. Everything past it counts as tail for the purpose
    of finding the two caudal-fin corners."""
    edges, widths = width_profile(along_axis, across_axis)
    centres = 0.5 * (edges[:-1] + edges[1:])
    span = along_axis.max() - along_axis.min()
    position = (centres - along_axis.min()) / (span + 1e-9)

    if tail_at_high_end:
        window = (position >= 0.55) & (position <= 0.93) & (widths > 0)
        fallback = along_axis.min() + 0.78 * span
    else:
        window = (position >= 0.07) & (position <= 0.45) & (widths > 0)
        fallback = along_axis.min() + 0.22 * span

    if not np.any(window):
        return fallback
    candidates = np.where(window)[0]
    return float(centres[candidates[np.argmin(widths[candidates])]])


# =====================================================================
# NEW - THE 7 FIXED LANDMARKS
# =====================================================================

def find_fixed_landmarks(outline, dorsal_side="up"):
    """Work out where the 7 fixed landmarks sit on a resampled fish outline.

    Returns a list of 7 indices into `outline`, in protocol order:
      anterior, anterior dorsal fin, posterior dorsal fin, dorsal caudal
      fin, ventral caudal fin, posterior anal fin, anterior anal fin.

    dorsal_side:
      "up"   - the fish's back points towards the top of the image (the
               usual arrangement for a lateral photo). This is the default
               because it's by far the most reliable when your photos are
               taken consistently.
      "down" - the fish's back points towards the bottom of the image.
      "auto" - guess, using the fact that in most fishes the dorsal fin
               base sits further forward than the anal fin base.
    """
    n = len(outline)
    smoothing_window = max(5, int(n * CONTOUR_SMOOTH_FRACTION))
    smoothed = smooth_closed_curve(outline, smoothing_window)

    centre, along_direction, across_direction = body_axis(smoothed)
    relative = smoothed - centre
    along = relative @ along_direction
    across = relative @ across_direction

    # Point the along-axis from head to tail, so "further along" always
    # means "closer to the tail".
    if not head_is_at_low_end(along, across):
        along_direction = -along_direction
        across_direction = np.array([-along_direction[1], along_direction[0]])
        along = relative @ along_direction
        across = relative @ across_direction

    # 1. ANTERIOR - the point furthest towards the head end.
    anterior_index = int(np.argmin(along))

    # 4 & 5. THE CAUDAL FIN INSERTIONS - where the tail fin joins the body,
    # i.e. the narrowest point of the caudal peduncle, taken on the dorsal
    # and ventral edges. NOT the outer corners of the tail fan: on the
    # reference fish, landmarks 4 and 5 sit at the insertion and
    # semilandmarks 20-28 wrap around the fan outside them.
    peduncle_along = find_peduncle_position(along, across, tail_at_high_end=True)

    # The waist itself: take a narrow slice at the peduncle and use its
    # dorsal-most and ventral-most points.
    slice_width = 0.02 * np.ptp(along)
    at_waist = np.abs(along - peduncle_along) < slice_width
    while np.count_nonzero(at_waist) < 4 and slice_width < 0.2 * np.ptp(along):
        slice_width *= 1.6
        at_waist = np.abs(along - peduncle_along) < slice_width

    if dorsal_side == "up":
        dorsal_is_positive_across = across_direction[1] < 0
    elif dorsal_side == "down":
        dorsal_is_positive_across = across_direction[1] > 0
    else:
        dorsal_is_positive_across = _guess_dorsal_side(smoothed, along, across)
    dorsal = across if dorsal_is_positive_across else -across

    if np.any(at_waist):
        dorsal_caudal_index = int(np.argmax(np.where(at_waist, dorsal, -np.inf)))
        ventral_caudal_index = int(np.argmin(np.where(at_waist, dorsal, np.inf)))
    else:  # shouldn't happen on a real outline
        dorsal_caudal_index = int(np.argmax(dorsal))
        ventral_caudal_index = int(np.argmin(dorsal))

    # Body length for the fin priors: snout to the caudal insertion.
    snout_along = along[anterior_index]
    body_length = max(1e-6, peduncle_along - snout_along)

    # 2, 3, 6, 7. THE FOUR FIN-BASE NOTCHES - the sharpest inward dents in
    # the outline, looked for only along the stretch of body between the
    # head and the peduncle, and only on the correct side of the axis.
    notch_step = max(3, int(n * 0.02))
    inward = concavity(smoothed, notch_step)
    body_span = np.ptp(along)
    body_depth = np.ptp(dorsal)
    searchable = along < peduncle_along + 0.02 * body_span
    snap = FIN_NOTCH_SNAP_FRACTION * body_span
    min_gap = max(4, int(n * 0.04))

    def landmark_at(target_along, want_dorsal):
        """Take a fin edge found from the bulge profile and snap it onto
        the nearest genuine crease in the outline, so the landmark sits in
        the notch rather than on an arbitrary bin boundary."""
        side = (dorsal > 0) if want_dorsal else (dorsal < 0)
        near = side & searchable & (np.abs(along - target_along) < snap)
        if not np.any(near):
            near = side & (np.abs(along - target_along) < 2 * snap)
        if not np.any(near):
            return int(np.argmin(np.where(side, np.abs(along - target_along), np.inf)))
        return int(np.argmax(np.where(near, inward, -np.inf)))

    def fin_pair(want_dorsal, prefer_posterior):
        side = (dorsal > 0) if want_dorsal else (dorsal < 0)
        height = dorsal if want_dorsal else -dorsal

        if USE_FIN_PRIORS:
            # Look only near where this species actually carries the fin.
            if want_dorsal:
                front_prior = FIN_PRIORS["anterior_dorsal_fin"]
                back_prior = FIN_PRIORS["posterior_dorsal_fin"]
            else:
                front_prior = FIN_PRIORS["anterior_anal_fin"]
                back_prior = FIN_PRIORS["posterior_anal_fin"]
            front = _best_notch_near(snout_along + front_prior * body_length,
                                     along, inward, side, body_length)
            back = _best_notch_near(snout_along + back_prior * body_length,
                                    along, inward, side, body_length)
            pair = [front, back]
            pair.sort(key=lambda i: along[i])
            return pair

        span = find_fin_base(along, height, side & searchable, body_depth,
                             prefer_posterior=prefer_posterior)
        if span is None:
            scores = np.where(side & searchable & (along > along.min() + 0.12 * body_span),
                              inward, 0.0)
            pair = _ensure_two_notches(find_local_peaks(scores, min_gap, 2),
                                       scores, along, min_gap)
            pair.sort(key=lambda i: along[i])
            return pair
        front, back = span
        pair = [landmark_at(front, want_dorsal), landmark_at(back, want_dorsal)]
        pair.sort(key=lambda i: along[i])
        return pair

    anterior_dorsal_index, posterior_dorsal_index = fin_pair(True, prefer_posterior=False)
    anterior_anal_index, posterior_anal_index = fin_pair(False, prefer_posterior=True)

    return [
        anterior_index,
        anterior_dorsal_index,
        posterior_dorsal_index,
        dorsal_caudal_index,
        ventral_caudal_index,
        posterior_anal_index,
        anterior_anal_index,
    ]


def _guess_dorsal_side(smoothed, along, across):
    """Decide which side of the axis is the back, by comparing where the
    two strongest notch-pairs sit: the dorsal fin base is usually further
    forward than the anal fin base. Less reliable than just telling the
    script which way up your photos are."""
    n = len(smoothed)
    inward = concavity(smoothed, max(3, int(n * 0.02)))
    stretch = (along > along.min() + 0.12 * np.ptp(along)) & (along < along.min() + 0.85 * np.ptp(along))
    min_gap = max(4, int(n * 0.04))

    positive = find_local_peaks(np.where(stretch & (across > 0), inward, 0.0), min_gap, 2)
    negative = find_local_peaks(np.where(stretch & (across < 0), inward, 0.0), min_gap, 2)
    if not positive or not negative:
        return True
    return float(np.mean(along[positive])) < float(np.mean(along[negative]))


def _ensure_two_notches(found, scores, along, min_gap):
    """If a fin notch was too soft to be detected (a fin folded flat, or a
    fin base that blends smoothly into the body), fall back to sensible
    positions rather than crashing. Anything that comes out of this
    fallback is exactly the kind of thing the review window is for."""
    found = list(found)
    if len(found) >= 2:
        return found[:2]

    ranked = np.argsort(scores)[::-1]
    for index in ranked:
        if len(found) >= 2:
            break
        if all(min(abs(index - f), len(scores) - abs(index - f)) >= min_gap for f in found):
            found.append(int(index))

    while len(found) < 2:  # last resort - shouldn't happen on a real outline
        found.append(int(np.argmax(scores)))
    return found[:2]


# =====================================================================
# NEW - THE FULL 43-POINT SERIES
# =====================================================================

def place_all_landmarks(outline, fixed_indices):
    """Given the outline and the 7 fixed landmark positions on it, fill in
    the 36 semilandmarks between them and return all 43 in protocol order.

    Returns (landmarks, fixed_indices) where landmarks is a 43x2 array
    numbered 1-43 the way the protocol numbers them, and fixed_indices is
    the (possibly reordered) list of the 7 fixed positions."""
    n = len(outline)
    fixed_indices = list(fixed_indices)

    # Make the outline run the way the protocol counts: starting at the
    # snout and going along the back first (snout -> dorsal fin -> tail
    # -> anal fin -> back to the snout). If it happens to run the other
    # way, flip it.
    start = fixed_indices[0]
    forward_gap = lambda i: (i - start) % n
    if forward_gap(fixed_indices[1]) > forward_gap(fixed_indices[-1]):
        outline = outline[::-1].copy()
        fixed_indices = [(n - 1 - i) for i in fixed_indices]

    landmarks = np.zeros((TOTAL_LANDMARKS, 2), dtype=np.float64)
    for position, index in enumerate(fixed_indices):
        landmarks[position] = outline[index]

    next_number = len(FIXED_LANDMARK_NAMES)  # landmark 8 lives at array slot 7
    for segment, how_many in enumerate(SEMILANDMARKS_PER_SEGMENT):
        start_index = fixed_indices[segment]
        end_index = fixed_indices[(segment + 1) % len(fixed_indices)]
        arc = (end_index - start_index) % n
        if arc == 0:
            arc = n
        for step in range(1, how_many + 1):
            fraction = step / (how_many + 1)
            landmarks[next_number] = point_at_fractional_index(outline, start_index + fraction * arc)
            next_number += 1

    return landmarks, fixed_indices, outline


def _best_notch_near(expected_along, along, inward, on_side, body_length):
    """Pick the outline point that best looks like a fin base, searching only
    within FIN_PRIOR_TOLERANCE of where this species is known to carry it.

    Within the window, preference goes to genuine creases in the outline,
    but a point close to the expected position is favoured over a slightly
    sharper one further away - otherwise a scale edge or a nick in the fin
    can still pull the landmark off by a body-length fraction."""
    tolerance = FIN_PRIOR_TOLERANCE * body_length
    distance = np.abs(along - expected_along)
    in_window = on_side & (distance < tolerance)
    if not np.any(in_window):
        in_window = on_side & (distance < 2 * tolerance)
    if not np.any(in_window):
        return int(np.argmin(np.where(on_side, distance, np.inf)))

    # Score creases, then discount them by how far they are from expected.
    crease = np.maximum(inward, 0.0)
    crease = crease / (crease[in_window].max() + 1e-9)
    closeness = 1.0 - (distance / (tolerance + 1e-9))
    score = np.where(in_window, crease + 1.2 * closeness, -np.inf)
    return int(np.argmax(score))


def _segment_polyline(clicked, outline, off_outline, segment, force_body_curve):
    """The path that segment's semilandmarks are placed along - either the
    stretch of detected outline between its two fixed points, or the local
    body curve where the outline can't be used. Returns an ordered array of
    points running from the segment's start landmark to its end landmark."""
    n_fixed = len(FIXED_LANDMARK_NAMES)
    start_point = clicked[segment]
    end_point = clicked[(segment + 1) % n_fixed]

    on_outline = (outline is not None
                  and not off_outline[segment]
                  and not off_outline[(segment + 1) % n_fixed]
                  and segment not in force_body_curve)

    if on_outline:
        n_outline = len(outline)
        indices = [int(np.argmin(np.linalg.norm(outline - p, axis=1))) for p in clicked]
        forward = (indices[1] - indices[0]) % n_outline
        backward = (indices[-1] - indices[0]) % n_outline
        if forward > backward:
            outline = outline[::-1].copy()
            indices = [(n_outline - 1 - i) for i in indices]
        start_index = indices[segment]
        end_index = indices[(segment + 1) % n_fixed]
        arc = (end_index - start_index) % n_outline or n_outline
        steps = np.linspace(0.0, float(arc), max(40, int(arc)))
        return np.array([point_at_fractional_index(outline, start_index + s) for s in steps])

    before = clicked[(segment - 1) % n_fixed]
    after = clicked[(segment + 2) % n_fixed]
    local = catmull_rom_closed(
        np.array([before, start_point, end_point, after]), samples_per_segment=200)
    return local[200:400]


def _position_along(path, point):
    """How far along a path a point sits, as a fraction from 0 to 1, using
    the nearest point on the path. Used to tell whether a hand-moved
    semilandmark is still inside its own segment and still in sequence."""
    distances = np.linalg.norm(path - np.asarray(point, float), axis=1)
    nearest = int(np.argmin(distances))
    return nearest / max(1, len(path) - 1), float(distances[nearest])


def reconcile_semilandmarks(landmarks, even_landmarks, moved_indices, clicked,
                            outline, force_body_curve):
    """Keep hand-moved semilandmarks where you put them, but put any that
    have drifted out of sequence back into the right order.

    A semilandmark belongs to a particular stretch of the fish - landmark
    17 lives between landmarks 2 and 3, for instance. If you drag one
    somewhere that isn't in its own stretch, or past its own neighbours,
    the numbering no longer runs in order round the fish, which is exactly
    what the protocol relies on.

    So for each segment: work out how far along that segment each moved
    point sits, keep the ones that are inside their stretch AND still in
    increasing order, and re-place the rest evenly in the gaps left over.
    Points you never touched are left at their even positions."""
    landmarks = landmarks.copy()
    n_fixed = len(FIXED_LANDMARK_NAMES)

    if outline is not None:
        fish_size = max(np.ptp(clicked[:, 0]), np.ptp(clicked[:, 1])) + 1e-9
        off_outline = [np.min(np.linalg.norm(outline - p, axis=1)) > 0.05 * fish_size
                       for p in clicked]
    else:
        off_outline = [True] * n_fixed

    number = n_fixed
    for segment, how_many in enumerate(SEMILANDMARKS_PER_SEGMENT):
        indices = list(range(number, number + how_many))
        number += how_many
        if not any(i in moved_indices for i in indices):
            continue

        path = _segment_polyline(clicked, outline, off_outline, segment, force_body_curve)
        span = float(np.sum(np.linalg.norm(np.diff(path, axis=0), axis=1))) or 1.0

        # Where each moved point sits along this segment, and how far off
        # the path it is. A point sitting a long way off the path has been
        # dragged out of this stretch entirely.
        placed = {}
        for i in indices:
            if i not in moved_indices:
                continue
            fraction, distance = _position_along(path, landmarks[i])
            in_stretch = (distance < 0.25 * span) and (0.0 < fraction < 1.0)
            if in_stretch:
                placed[i] = fraction

        # Drop any that break increasing order, keeping the longest run
        # that IS in order so one stray point doesn't discard the rest.
        ordered = sorted(placed.items())
        keep = {}
        last = 0.0
        for i, fraction in ordered:
            if fraction > last:
                keep[i] = fraction
                last = fraction

        # Anything not kept goes back to an even position, spread through
        # whatever gaps the kept points leave.
        for position, i in enumerate(indices):
            if i in keep:
                continue
            lower = max([f for j, f in keep.items() if j < i], default=0.0)
            upper = min([f for j, f in keep.items() if j > i], default=1.0)
            unresolved = [j for j in indices
                          if j not in keep
                          and (max([f for k, f in keep.items() if k < j], default=0.0) == lower)
                          and (min([f for k, f in keep.items() if k > j], default=1.0) == upper)]
            slot = unresolved.index(i) + 1
            fraction = lower + (upper - lower) * slot / (len(unresolved) + 1)
            landmarks[i] = path[int(round(fraction * (len(path) - 1)))]

    return landmarks


def landmarks_from_seven_points(clicked, outline=None, follow="auto"):
    """Take the 7 fixed landmarks you placed by hand and fill in the 36
    semilandmarks between them, following the fish's curve.

    clicked  - your 7 points, in protocol order (anterior, anterior dorsal
               fin, posterior dorsal fin, dorsal caudal fin, ventral caudal
               fin, posterior anal fin, anterior anal fin)
    outline  - the detected fish outline, if there is one
    follow   - which curve the semilandmarks should run along:
                 "outline" always ride the detected outline. Most faithful
                           to the real fish edge, but only as good as the
                           segmentation - if a translucent fin was missed,
                           points get dragged off the fin.
                 "spline"  ignore the outline and run a smooth closed curve
                           through your 7 points instead. Always well
                           behaved, but it can't see detail you didn't
                           click, so it cuts corners on a fanned tail.
                 "auto"    (default) use the outline where it genuinely
                           passes near your clicks, and the spline where it
                           doesn't. This is the one you want: it follows
                           the real fin edge where the fin was detected,
                           and behaves sensibly where it wasn't.

    Returns (landmarks, curve) - 43 points in protocol order, plus the
    curve they were placed along, so it can be redrawn or re-flowed."""
    clicked = np.asarray(clicked, dtype=np.float64)
    if len(clicked) != len(FIXED_LANDMARK_NAMES):
        raise ValueError(f"Need exactly {len(FIXED_LANDMARK_NAMES)} points, got {len(clicked)}.")

    # (see module-level FORCE_BODY_CURVE_SEGMENTS)
    # Segments 2->3 (semilandmark 17) and 6->7 (semilandmarks 30-32) must
    # always cut across the body under the dorsal/anal fin bases, not trace
    # the fin's own outer margin - even though the fin margin IS the real
    # detected outline there, and even when every clicked point sits
    # squarely on that outline. So these two segments are always forced
    # onto the local body curve, regardless of the follow mode.


    spline = resample_closed_curve(catmull_rom_closed(clicked), CONTOUR_RESAMPLE_POINTS)

    use_outline = outline is not None and len(outline) >= len(FIXED_LANDMARK_NAMES) * 2
    if use_outline and follow != "spline":
        # How far each hand-placed point sits from the detected outline,
        # measured against the size of the fish so it works at any zoom.
        fish_size = max(np.ptp(clicked[:, 0]), np.ptp(clicked[:, 1])) + 1e-9
        distances = [np.min(np.linalg.norm(outline - point, axis=1)) for point in clicked]
        off_outline = [d > 0.05 * fish_size for d in distances]

        if follow == "outline" or not any(off_outline):
            # Ride the outline for every segment EXCEPT the two forced onto
            # the body curve - this used to be a separate fast path that
            # rode the raw outline everywhere, which is exactly what
            # traced the fin's outer edge instead of its base.
            landmarks = _blended_landmarks(clicked, outline, off_outline,
                                           force_body_curve=FORCE_BODY_CURVE_SEGMENTS)
            return landmarks, landmarks

        if follow == "auto" and not all(off_outline):
            # Mixed: ride the outline between clicks that both sit on it,
            # and bow along a local curve where the outline can't be trusted.
            landmarks = _blended_landmarks(clicked, outline, off_outline,
                                           force_body_curve=FORCE_BODY_CURVE_SEGMENTS)
            return landmarks, landmarks

    indices = [int(np.argmin(np.linalg.norm(spline - p, axis=1))) for p in clicked]
    landmarks, _, curve = place_all_landmarks(spline, indices)
    landmarks[:len(clicked)] = clicked  # keep your clicks exactly as placed
    return landmarks, landmarks


def _blended_landmarks(clicked, outline, off_outline, force_body_curve=()):
    """Place semilandmarks segment by segment: ride the detected outline
    for stretches where both end points sit on it, and interpolate along a
    smooth local curve for stretches where they don't (a fin the
    segmentation missed, typically the tail) - or where force_body_curve
    says to always cut across rather than trace the outline, regardless of
    how close the outline is (the dorsal and anal fin margins: segments
    2->3 and 6->7 must follow the body's own back/belly line under the fin,
    not the fin's outer edge, which is what the true silhouette outline
    actually traces there)."""
    n_fixed = len(FIXED_LANDMARK_NAMES)
    landmarks = np.zeros((TOTAL_LANDMARKS, 2), dtype=np.float64)
    landmarks[:n_fixed] = clicked

    outline_indices = [int(np.argmin(np.linalg.norm(outline - p, axis=1))) for p in clicked]
    n_outline = len(outline)

    # Work out which way round the outline runs relative to protocol order.
    forward = (outline_indices[1] - outline_indices[0]) % n_outline
    backward = (outline_indices[-1] - outline_indices[0]) % n_outline
    reversed_outline = forward > backward
    if reversed_outline:
        outline = outline[::-1].copy()
        outline_indices = [(n_outline - 1 - i) for i in outline_indices]

    number = n_fixed
    for segment, how_many in enumerate(SEMILANDMARKS_PER_SEGMENT):
        start_point = clicked[segment]
        end_point = clicked[(segment + 1) % n_fixed]
        both_on_outline = (not off_outline[segment]
                          and not off_outline[(segment + 1) % n_fixed]
                          and segment not in force_body_curve)

        if both_on_outline:
            start_index = outline_indices[segment]
            end_index = outline_indices[(segment + 1) % n_fixed]
            arc = (end_index - start_index) % n_outline or n_outline
            for step in range(1, how_many + 1):
                fraction = step / (how_many + 1)
                landmarks[number] = point_at_fractional_index(
                    outline, start_index + fraction * arc)
                number += 1
        else:
            # No trustworthy outline here - bow the points gently along a
            # local curve through the neighbouring fixed landmarks rather
            # than cutting a hard straight line.
            before = clicked[(segment - 1) % n_fixed]
            after = clicked[(segment + 2) % n_fixed]
            local = catmull_rom_closed(
                np.array([before, start_point, end_point, after]), samples_per_segment=200)
            piece = local[200:400]  # the stretch between start_point and end_point

            # Space these by ARC LENGTH along the curve, not by curve
            # parameter. A Catmull-Rom's parameter runs faster where the
            # curve bends, so indexing it directly bunches points up around
            # corners - measured 133% spacing spread on the 2->3 segment
            # before this. The protocol wants them evenly spaced.
            steps = np.linalg.norm(np.diff(piece, axis=0), axis=1)
            along = np.concatenate([[0.0], np.cumsum(steps)])
            total = along[-1]
            for step in range(1, how_many + 1):
                fraction = step / (how_many + 1)
                if total <= 0:
                    landmarks[number] = piece[int(fraction * (len(piece) - 1))]
                else:
                    target = fraction * total
                    landmarks[number] = np.array([
                        np.interp(target, along, piece[:, 0]),
                        np.interp(target, along, piece[:, 1]),
                    ])
                number += 1

    return landmarks


def _segments_cross(a1, a2, b1, b2):
    """Do the two line segments a1-a2 and b1-b2 cross?"""
    def side(p, q, r):
        return ((q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0]))
    d1, d2 = side(b1, b2, a1), side(b1, b2, a2)
    d3, d4 = side(a1, a2, b1), side(a1, a2, b2)
    return ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0))


def shape_self_intersects(points):
    """True if joining the landmarks 1,2,3...43,1 produces a line that
    crosses itself.

    A correct landmark set traces the fish's outline once round, so it
    never crosses. A shape that does cross means the points are out of
    order - the numbering is jumping back and forth across the body rather
    than running round it - and Colormesh would then warp the fish using a
    tangled correspondence. Worth catching before that happens.

    Returns (crosses, number_of_crossings)."""
    points = np.asarray(points, dtype=np.float64)
    if len(points) == TOTAL_LANDMARKS:
        points = points[PERIMETER_ORDER]      # walk the outline, not 1,2,3...
    n = len(points)
    if n < 4:
        return False, 0
    crossings = 0
    for i in range(n):
        a1, a2 = points[i], points[(i + 1) % n]
        # Skip neighbours: they legitimately share an end point.
        for j in range(i + 2, n):
            if i == 0 and j == n - 1:
                continue
            b1, b2 = points[j], points[(j + 1) % n]
            if _segments_cross(a1, a2, b1, b2):
                crossings += 1
    return crossings > 0, crossings


def transform_landmarks(points, offset=None, flip=False, angle=0.0, scale=1.0):
    """Move, mirror, turn or resize a whole landmark set as one rigid shape.

    Used when reusing a previous frame's landmarks: the fish will have
    moved, and often turned or swum the other way, so the old outline has
    to be lined up before it's any use. Everything happens about the
    shape's own centre so it doesn't wander off while you adjust it.

    flip mirrors left-right, which is what's needed when the fish has
    turned to face the other way - the landmark ORDER is preserved, so
    landmark 1 is still the snout afterwards."""
    points = np.asarray(points, dtype=np.float64).copy()
    centre = points.mean(axis=0)
    local = points - centre

    if flip:
        local[:, 0] = -local[:, 0]
    if scale != 1.0:
        local = local * scale
    if angle:
        radians = np.deg2rad(angle)
        cos_a, sin_a = np.cos(radians), np.sin(radians)
        rotation = np.array([[cos_a, -sin_a], [sin_a, cos_a]])
        local = local @ rotation.T

    moved = local + centre
    if offset is not None:
        moved = moved + np.asarray(offset, dtype=np.float64)
    return moved


def describe_landmark(number):
    """Plain-English description of where landmark `number` goes, for the
    prompt when placing all 43 by hand. Landmarks 1-7 are the named
    anatomical points; the rest are semilandmarks that sit between two of
    them, so the description says which two and how many share that
    stretch."""
    n_fixed = len(FIXED_LANDMARK_NAMES)
    if number <= n_fixed:
        return FIXED_LANDMARK_NAMES[number - 1].replace("_", " ").upper()

    running = n_fixed
    for segment, how_many in enumerate(SEMILANDMARKS_PER_SEGMENT):
        if running < number <= running + how_many:
            start_landmark = segment + 1
            end_landmark = (segment + 1) % n_fixed + 1
            position_in_run = number - running
            first = running + 1
            last = running + how_many
            span = f"{first}-{last}" if how_many > 1 else f"{first}"
            return (f"between {start_landmark} "
                    f"({FIXED_LANDMARK_NAMES[start_landmark - 1].replace('_', ' ')}) "
                    f"and {end_landmark} "
                    f"({FIXED_LANDMARK_NAMES[end_landmark - 1].replace('_', ' ')})"
                    f"  -  point {position_in_run} of {how_many}  [{span}]")
        running += how_many
    return ""


def landmark_numbers_by_segment():
    """Which landmark numbers belong to which stretch of outline - handy
    for printing and for the review window's labels."""
    labels = {}
    for i, name in enumerate(FIXED_LANDMARK_NAMES, start=1):
        labels[i] = name
    number = len(FIXED_LANDMARK_NAMES) + 1
    for segment, how_many in enumerate(SEMILANDMARKS_PER_SEGMENT):
        a = segment + 1
        b = (segment + 1) % len(FIXED_LANDMARK_NAMES) + 1
        for _ in range(how_many):
            labels[number] = f"semilandmark_{a}_to_{b}"
            number += 1
    return labels


LANDMARK_LABELS = landmark_numbers_by_segment()


# ---------------------------------------------------------------------
# Animal profiles
# ---------------------------------------------------------------------
# Everything above describes the killifish scheme. A profile replaces it:
# apply_profile() swaps in another set of primary landmarks, semilandmark
# counts and default shape, and recomputes everything derived from them.
# Every function reads these at call time, so this only has to happen once
# in main(), before the first frame.

PROFILE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "profiles")
DEFAULT_PROFILE = os.path.join(PROFILE_DIR, "killifish.json")
PROFILE_NAME = "Fish (killifish, 43 landmarks) - built in"
AUTO_DETECT = True       # find the primary landmarks from the outline (killifish only)
TEMPLATE = None          # default shape: N x 2, centred, unit size, landmark 1 facing right


def apply_profile(path):
    """Load an animal profile and make it the active landmark scheme."""
    global FIXED_LANDMARK_NAMES, SEMILANDMARKS_PER_SEGMENT, FORCE_BODY_CURVE_SEGMENTS
    global PERIMETER_ORDER, TOTAL_LANDMARKS, LANDMARK_LABELS, TOOLBAR_BUTTONS
    global PROFILE_NAME, AUTO_DETECT, TEMPLATE

    with open(path, encoding="utf-8") as handle:
        profile = json.load(handle)
    names = [str(n).strip().replace(" ", "_") for n in profile["fixed_names"]]
    semis = [int(n) for n in profile["semis_per_segment"]]
    if len(names) < 3:
        raise ValueError(f"{path}: needs at least 3 primary landmarks")
    if len(semis) != len(names):
        raise ValueError(f"{path}: semis_per_segment needs one number per primary "
                         f"landmark ({len(names)}), got {len(semis)}")
    if any(n < 0 for n in semis):
        raise ValueError(f"{path}: semilandmark counts can't be negative")

    FIXED_LANDMARK_NAMES = names
    SEMILANDMARKS_PER_SEGMENT = semis
    FORCE_BODY_CURVE_SEGMENTS = set(profile.get("force_body_curve_segments", []))
    PERIMETER_ORDER = _perimeter_order()
    TOTAL_LANDMARKS = len(names) + sum(semis)
    LANDMARK_LABELS = landmark_numbers_by_segment()
    PROFILE_NAME = profile.get("name", os.path.basename(path))
    AUTO_DETECT = bool(profile.get("auto_detect", False))

    TEMPLATE = None
    template = profile.get("template")
    if template is not None:
        template = np.asarray(template, dtype=np.float64)
        if template.shape == (TOTAL_LANDMARKS, 2):
            TEMPLATE = template
        else:
            print(f"  (the default shape in {os.path.basename(path)} has "
                  f"{len(template)} points but the scheme has {TOTAL_LANDMARKS}; "
                  f"ignoring it)")

    # Toolbar labels that name the counts.
    relabel = {"keepedits": f"Reset all {sum(semis)}",
               "clear": f"Clear {len(names)}",
               "manual_all": f"Place all {TOTAL_LANDMARKS}"}
    TOOLBAR_BUTTONS = [(relabel.get(action, label), key, action)
                       for label, key, action in TOOLBAR_BUTTONS]


def place_template(frame_shape, outline=None, circle=None):
    """The default shape, sized and positioned for this frame.

    Over the detected outline's bounding box if there is one, otherwise in
    the middle of the lightbox circle (or frame) at about 40% of its width.
    It always arrives facing right, back up; F flips it, R/[ ] turn it, and
    -/= resize it, as with any shape from Previous."""
    if TEMPLATE is None:
        return None
    shape = TEMPLATE - TEMPLATE.mean(axis=0)
    width = np.ptp(shape[:, 0]) or 1.0
    if outline is not None and len(outline) >= 3:
        outline = np.asarray(outline, dtype=np.float64)
        target_width = np.ptp(outline[:, 0])
        target_height = np.ptp(outline[:, 1])
        # Fit the longer side, so an animal lying diagonally isn't tiny.
        target = max(target_width, target_height)
        centre = (outline.min(axis=0) + outline.max(axis=0)) / 2
    else:
        image_h, image_w = frame_shape[:2]
        if circle is not None:
            cx, cy, radius = circle[:3]
            centre = np.array([cx, cy], dtype=np.float64)
            target = 0.8 * radius
        else:
            centre = np.array([image_w / 2, image_h / 2], dtype=np.float64)
            target = 0.4 * image_w
    return shape * (target / width) + centre


# =====================================================================
# NEW - SCALE BAR
# =====================================================================

def estimate_scale_from_colour_standard(frame, colour_points,
                                        square_mm=COLOUR_STANDARD_SQUARE_MM):
    """Fallback scale for frames with no scale bar in view: measure the
    WIDTH OF THE COLOUR-STANDARD SQUARES themselves.

    This detects the actual printed square around each of your 6 colour
    points and measures its edge length, rather than measuring the distance
    between the points you clicked. Point-to-point spacing would depend on
    exactly where in each square you happened to click, and on the gaps
    between squares; the square's own edge is a fixed printed dimension, so
    it's the more reliable thing to calibrate against.

    Returns (point_a, point_b, length_px) in the same shape as a clicked
    scale bar - the two points spanning one measured square's width, and
    the MEDIAN width across all squares it managed to detect - or None if
    it couldn't confidently detect any."""
    if colour_points is None or len(colour_points) == 0:
        return None

    patches = find_colour_patches(frame)
    if not patches:
        return None

    widths = []
    best_box = None
    for point in colour_points:
        point = np.asarray(point, float)
        # Find the detected patch whose box actually contains this point,
        # or failing that the nearest patch centre.
        containing = None
        for patch in patches:
            x, y, box_w, box_h = patch["box"]
            if x <= point[0] <= x + box_w and y <= point[1] <= y + box_h:
                containing = patch
                break
        if containing is None:
            distances = [float(np.linalg.norm(p["centre"] - point)) for p in patches]
            nearest = int(np.argmin(distances))
            # Only trust it if the point is plausibly inside that patch.
            if distances[nearest] > max(patches[nearest]["width"],
                                        patches[nearest]["height"]):
                continue
            containing = patches[nearest]

        # Use the square's WIDTH specifically. Measured on real frames from
        # this project, detected widths were far more consistent than
        # heights (88-101 px vs 66-94 px across the same six patches):
        # the card sits at an angle, so a patch's top and bottom edges
        # blend into its neighbours and the detected region comes up short
        # vertically, while the left and right edges stay crisp.
        edge = containing["width"]
        widths.append(edge)
        if best_box is None:
            x, y, box_w, box_h = containing["box"]
            best_box = (np.array([float(x), float(y + box_h / 2.0)]),
                        np.array([float(x + box_w), float(y + box_h / 2.0)]))

    if not widths:
        return None

    # Median rather than mean: one merged or clipped square shouldn't drag
    # the estimate, and a clipped square at the frame edge is common here.
    median_width = float(np.median(widths))

    # How much the measured squares disagree. On a card viewed at an angle
    # this is real perspective distortion, not noise - a wide spread means
    # the single scale figure is a compromise across the card, so it's
    # surfaced rather than hidden.
    spread_percent = (100.0 * (max(widths) - min(widths)) / median_width
                      if median_width else 0.0)

    # Downstream code always divides by SCALE_BAR_MM to get mm/px, so
    # convert to "however many pixels SCALE_BAR_MM would span". That keeps
    # the division correct even if COLOUR_STANDARD_SQUARE_MM is set to
    # something different from SCALE_BAR_MM.
    equivalent_px = median_width * (SCALE_BAR_MM / square_mm)
    a, b = best_box
    return a, b, equivalent_px, len(widths), spread_percent


def detect_scale_bar(frame, exclude_mask=None):
    """Look for the 10 mm scale bar: a long, thin, solid rectangle. Returns
    (point_a, point_b, length_in_pixels) or None.

    This is the number the protocol has you read off ImageJ's Set Scale
    dialog and paste into the 5th column of the spreadsheet."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    height, width = gray.shape
    longest_side = max(height, width)

    best = None
    best_score = 0.0

    # Try it both ways round, since a scale bar may be dark on a light
    # background or light on a dark one.
    for inverted in (False, True):
        working = (255 - gray) if inverted else gray
        _, binary = cv2.threshold(working, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        if exclude_mask is not None:
            binary = cv2.bitwise_and(binary, cv2.bitwise_not(exclude_mask))

        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            rectangle = cv2.minAreaRect(contour)
            (side_a, side_b) = rectangle[1]
            if min(side_a, side_b) < 1.0:
                continue
            long_side, short_side = max(side_a, side_b), min(side_a, side_b)
            aspect = long_side / short_side
            if aspect < 6.0:
                continue
            if not (0.03 * longest_side < long_side < 0.6 * longest_side):
                continue
            solidity = cv2.contourArea(contour) / (long_side * short_side + 1e-9)
            if solidity < 0.7:  # a real bar is a filled rectangle, not a squiggle
                continue

            score = aspect * solidity
            if score > best_score:
                corners = cv2.boxPoints(rectangle)
                ordered = sorted(
                    [(corners[i], corners[(i + 1) % 4]) for i in range(4)],
                    key=lambda pair: np.linalg.norm(pair[0] - pair[1]),
                )
                # The two shortest edges are the bar's ends; their
                # midpoints are the points you'd click in ImageJ.
                end_a = (ordered[0][0] + ordered[0][1]) / 2.0
                end_b = (ordered[1][0] + ordered[1][1]) / 2.0
                best = (end_a, end_b, float(np.linalg.norm(end_a - end_b)))
                best_score = score

    return best


# =====================================================================
# NEW - COLOUR STANDARD
# =====================================================================

def _largest_blob_centre(mask, minimum_area):
    count, labels, stats, centroids = cv2.connectedComponentsWithStats(mask, 8)
    best_index, best_area = None, 0
    for i in range(1, count):
        area = stats[i, cv2.CC_STAT_AREA]
        if area > best_area and area >= minimum_area:
            best_index, best_area = i, area
    if best_index is None:
        return None
    return np.array(centroids[best_index], dtype=np.float64)


def find_colour_patches(frame, min_frac=2e-5, max_frac=4e-3, variation_limit=4.0):
    """Find uniform, roughly square regions - i.e. the cells of a colour
    chart. Works by looking for areas of low local variation, which is what
    a printed patch is and what water, glare and a fish are not."""
    h, w = frame.shape[:2]
    blur = cv2.GaussianBlur(frame, (5, 5), 0)
    gray = cv2.cvtColor(blur, cv2.COLOR_BGR2GRAY).astype(np.float32)

    mean = cv2.boxFilter(gray, -1, (9, 9))
    mean_square = cv2.boxFilter(gray * gray, -1, (9, 9))
    variation = np.sqrt(np.maximum(mean_square - mean * mean, 0))
    flat = (variation < variation_limit).astype(np.uint8) * 255
    flat = cv2.morphologyEx(flat, cv2.MORPH_OPEN, np.ones((7, 7), np.uint8))

    count, labels, stats, centroids = cv2.connectedComponentsWithStats(flat, 8)
    patches = []
    for i in range(1, count):
        x, y, box_w, box_h, area = stats[i]
        if not (min_frac * h * w <= area <= max_frac * h * w):
            continue
        if box_w < 12 or box_h < 12:
            continue
        if not (0.6 <= box_w / box_h <= 1.7):
            continue
        if area / float(box_w * box_h) < 0.6:
            continue
        region = labels[y:y + box_h, x:x + box_w] == i
        pixels = blur[y:y + box_h, x:x + box_w][region]
        if len(pixels) < 40:
            continue
        patches.append({"centre": np.array(centroids[i], float),
                        "bgr": np.median(pixels, axis=0),
                        "width": int(box_w),
                        "height": int(box_h),
                        "box": (int(x), int(y), int(box_w), int(box_h))})
    return patches


def detect_colour_standard(frame, exclude_mask=None):
    """Try progressively looser definitions of 'a flat patch' until the
    chart is found.

    How uniform a printed patch looks depends on the frame: compression,
    focus, glare and the angle of the card all change it. Measured on one
    real frame, a threshold of 2 gave 50 candidate patches, 4 gave 40, 12
    gave 7 and 20 gave just 2 - so any single fixed value will work on some
    frames and fail on others. Rather than pick one, this tries a range and
    keeps the first that yields a complete, plausible set of 6."""
    for variation_limit in (4.0, 2.5, 6.0, 8.0, 1.5, 11.0):
        found = _detect_colour_standard_once(frame, exclude_mask, variation_limit)
        if found is not None:
            return found
    return None


def _detect_colour_standard_once(frame, exclude_mask=None, variation_limit=4.0):
    """Locate the 6 required patches using both their colours AND their
    positions relative to one another.

    The chart is laid out as two columns of three: the strongly coloured
    patches in one column, the greys alongside them in the other, paired
    row by row. Colour alone can't do this reliably - a 24-patch chart has
    several reddish and greenish cells, a white tank is full of flat pale
    areas that look like a white patch, and any patch can be missed if it
    sits at the frame edge or its edges blur into a neighbour.

    So this works out the geometry instead:
      1. Find whichever of red/green/blue can be identified by hue.
      2. From those, derive the row spacing vector, and extrapolate any
         missing one - a patch that couldn't be detected directly still
         has a predictable position.
      3. Find the offset to the grey column from whichever grey patches
         were detected, and place the rest by the same offset.
      4. Name the greys by measured brightness, so they can't be
         swapped even if the rows were read in an odd order.

    Returns 6 points in protocol order (white, light grey, mid grey, red,
    green, blue), or None if the geometry couldn't be established."""
    patches = find_colour_patches(frame, variation_limit=variation_limit)
    if len(patches) < 3:
        return None

    as_hsv = cv2.cvtColor(np.array([[p["bgr"]] for p in patches], np.uint8),
                          cv2.COLOR_BGR2HSV).reshape(-1, 3)
    kept = []
    for patch, hsv in zip(patches, as_hsv):
        patch["hue"], patch["sat"], patch["val"] = int(hsv[0]), int(hsv[1]), int(hsv[2])
        if exclude_mask is not None:
            x, y = int(patch["centre"][0]), int(patch["centre"][1])
            if (0 <= y < exclude_mask.shape[0] and 0 <= x < exclude_mask.shape[1]
                    and exclude_mask[y, x] == 255):
                continue        # that's the fish, not a colour patch
        kept.append(patch)
    patches = kept

    height, width = frame.shape[:2]

    def hue_gap(patch, target):
        return min(abs(patch["hue"] - target), 180 - abs(patch["hue"] - target))

    # --- 1. the chromatic column, by hue -----------------------------
    chromatic = [p for p in patches if p["sat"] > 60 and p["val"] > 45]
    targets = {"red": 5, "green": 45, "blue": 120}
    found = {}
    for name, target in targets.items():
        candidates = [p for p in chromatic if hue_gap(p, target) < 22]
        if candidates:
            found[name] = min(candidates, key=lambda p: hue_gap(p, target))["centre"]

    if len(found) < 2:
        return None   # can't establish the geometry from one point

    # --- 2. fill in a missing chromatic patch by row spacing ----------
    # Rows run red -> green -> blue, evenly spaced down the column.
    order = ["red", "green", "blue"]
    known = [(i, found[n]) for i, n in enumerate(order) if n in found]
    if len(known) >= 2:
        (i0, p0), (i1, p1) = known[0], known[-1]
        row_vector = (np.asarray(p1, float) - np.asarray(p0, float)) / max(1, (i1 - i0))
        for i, name in enumerate(order):
            if name not in found:
                found[name] = np.asarray(p0, float) + row_vector * (i - i0)

    chromatic_points = [np.asarray(found[n], float) for n in order]
    for point in chromatic_points:
        if not (-width * 0.1 <= point[0] <= width * 1.1
                and -height * 0.1 <= point[1] <= height * 1.1):
            return None   # extrapolated somewhere impossible

    # --- 3. the grey column, by its offset from the chromatic one -----
    # Only greys that are the same SIZE as a chart cell count. Without this
    # the frame's own flat pale areas - water marks, reflections, bits of
    # the tank - swamp the real patches: on a test frame there were 34 grey
    # candidates and only 5 were actually on the card, which dragged the
    # median offset onto the wrong row.
    chromatic_patches = [p for p in patches if p["sat"] > 60 and p["val"] > 45
                         and p["width"] > 20]
    if chromatic_patches:
        cell_size = float(np.median([p["width"] for p in chromatic_patches]))
    else:
        cell_size = 0.0

    greys = [p for p in patches if p["sat"] < 45 and p["val"] > 60]
    if cell_size > 0:
        greys = [g for g in greys
                 if 0.5 * cell_size < g["width"] < 1.8 * cell_size
                 and 0.4 * cell_size < g["height"] < 1.8 * cell_size]
    if not greys:
        return None

    offsets = []
    for grey in greys:
        for point in chromatic_points:
            offset = np.asarray(grey["centre"], float) - point
            # Greys sit beside their row, not far above or below it.
            if abs(offset[1]) < 0.45 * max(1.0, abs(np.ptp([p[1] for p in chromatic_points]))) \
                    and 10 < abs(offset[0]) < 0.5 * width:
                offsets.append(offset)
    if not offsets:
        return None

    offsets = np.array(offsets)
    # Median offset: individual greys may be missed or slightly off, but
    # the column as a whole sits at one consistent distance.
    column_offset = np.array([float(np.median(offsets[:, 0])),
                              float(np.median(offsets[:, 1]))])
    grey_points = [point + column_offset for point in chromatic_points]

    for point in grey_points:
        if not (0 <= point[0] < width and 0 <= point[1] < height):
            return None

    # Snap each predicted grey onto a real detected grey patch when there
    # is one close by, so the sample sits in the middle of the cell rather
    # than wherever the offset happened to land.
    snapped = []
    for point in grey_points:
        near = [g for g in greys
                if np.linalg.norm(np.asarray(g["centre"], float) - point)
                < 0.6 * max(g["width"], g["height"])]
        if near:
            best = min(near, key=lambda g: np.linalg.norm(
                np.asarray(g["centre"], float) - point))
            snapped.append(np.asarray(best["centre"], float))
        else:
            snapped.append(point)
    grey_points = snapped

    # --- 4. name the greys by measured brightness --------------------
    measured = sample_patch_colours(frame, grey_points)
    brightness = [float(np.mean(bgr)) for bgr in measured]
    by_brightness = np.argsort(brightness)[::-1]      # brightest first
    white = grey_points[by_brightness[0]]
    light_grey = grey_points[by_brightness[1]]
    mid_grey = grey_points[by_brightness[2]]

    red, green, blue = chromatic_points
    points = [white, light_grey, mid_grey, red, green, blue]

    # Check what was actually found looks like the chart before accepting
    # it: the three greys must really be grey, and red/green/blue must
    # really be those hues. A looser threshold that produced a plausible
    # geometry but the wrong cells gets rejected here rather than silently
    # calibrating against the wrong colours.
    measured = sample_patch_colours(frame, points)
    as_hsv = cv2.cvtColor(np.array([[c] for c in measured], np.uint8),
                          cv2.COLOR_BGR2HSV).reshape(-1, 3)
    greys_ok = all(int(h[1]) < 60 for h in as_hsv[:3])
    chroma_ok = all(int(h[1]) > 55 for h in as_hsv[3:])
    brightness_ordered = (np.mean(measured[0]) >= np.mean(measured[1]) - 3
                          >= np.mean(measured[2]) - 8)
    if not (greys_ok and chroma_ok and brightness_ordered):
        return None

    # Geometry check. The chart is two parallel columns of three, paired
    # row by row, so the step from each chromatic patch to its grey
    # partner should be about the same vector for all three rows. Colour
    # checks alone are not enough: on a darkened frame the saturation
    # tests still passed while the points had landed on entirely the wrong
    # cells, 670px from where they belonged. Requiring the shape to hold
    # catches that.
    pairs = [(np.asarray(points[5], float), np.asarray(points[0], float)),   # blue  - white
             (np.asarray(points[4], float), np.asarray(points[1], float)),   # green - light grey
             (np.asarray(points[3], float), np.asarray(points[2], float))]   # red   - mid grey
    offsets = np.array([grey - chromatic for chromatic, grey in pairs])
    typical = float(np.median(np.linalg.norm(offsets, axis=1)))
    if typical < 5:
        return None
    spread = float(np.max(np.linalg.norm(offsets - offsets.mean(axis=0), axis=1)))
    if spread > 0.45 * typical:
        return None

    # Rows should be evenly spaced down each column, too.
    for column in (points[:3], points[3:]):
        steps = [float(np.linalg.norm(np.asarray(column[i + 1], float)
                                      - np.asarray(column[i], float)))
                 for i in range(2)]
        if min(steps) < 5 or max(steps) > 2.2 * min(steps):
            return None

    return points


# ------------------------------------------------------------------
# Teach once, then track. The reliable path on a fixed rig.
# ------------------------------------------------------------------

# ------------------------------------------------------------------
# The tank label
# ------------------------------------------------------------------
# OCR was removed. It read the ECKO/APHP prefix reliably but kept
# misreading the suffix that identifies the individual fish - y1y5 as
# y1y9 - and a wrong suffix silently attributes one fish's data to
# another. Typing it once per video is quick and correct.

LABEL_PREFIXES = ["ECKO", "ECHP", "APKO", "APHP"]


def _clean_label_word(word):
    return re.sub(r"[^A-Za-z0-9]", "", str(word)).upper()


def label_matches_known_prefix(text):
    """True if this looks like one of the expected codes, allowing a
    single wrong character - just a typo check on what you type."""
    cleaned = _clean_label_word(text)
    for prefix in LABEL_PREFIXES:
        if len(cleaned) < len(prefix):
            continue
        if sum(a != b for a, b in zip(cleaned[:len(prefix)], prefix)) <= 1:
            return True
    return False


COLOUR_STANDARD_FILE = "colour_standard.json"
COLOUR_STANDARD_PATCH = "colour_standard_reference.png"


def save_colour_standard(out_folder, frame, points):
    """Remember where the 6 patches are, plus a small picture of the chart
    area so later frames can be matched against it. The rig is fixed, so
    teaching this once covers everything shot in the same setup - including
    later runs, since it's written to disk."""
    import json
    points = [np.asarray(p, float) for p in points]
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    pad = 60
    x0 = max(0, int(min(xs) - pad))
    y0 = max(0, int(min(ys) - pad))
    x1 = min(frame.shape[1], int(max(xs) + pad))
    y1 = min(frame.shape[0], int(max(ys) + pad))
    if x1 - x0 < 20 or y1 - y0 < 20:
        return
    os.makedirs(out_folder, exist_ok=True)
    cv2.imwrite(os.path.join(out_folder, COLOUR_STANDARD_PATCH), frame[y0:y1, x0:x1])
    with open(os.path.join(out_folder, COLOUR_STANDARD_FILE), "w", encoding="utf-8") as handle:
        json.dump({"points": [[float(p[0]), float(p[1])] for p in points],
                   "crop": [x0, y0, x1, y1],
                   "names": COLOUR_STANDARD_NAMES}, handle, indent=2)


def load_colour_standard(out_folder):
    import json
    path = os.path.join(out_folder, COLOUR_STANDARD_FILE)
    crop_path = os.path.join(out_folder, COLOUR_STANDARD_PATCH)
    if not (os.path.exists(path) and os.path.exists(crop_path)):
        return None
    # A run interrupted mid-write leaves an empty or truncated file behind.
    # That shouldn't stop the next run dead - just treat it as "nothing
    # taught yet" and let it be taught again.
    try:
        with open(path, encoding="utf-8") as handle:
            saved = json.load(handle)
        reference = cv2.imread(crop_path)
        if reference is None or not saved.get("points"):
            raise ValueError("incomplete color standard")
    except Exception as error:
        print(f"  (ignoring unreadable color standard at {path}: {error})")
        return None
    saved["reference"] = reference
    return saved


def track_colour_standard(frame, saved, search=45):
    """Re-locate the taught patches in a new frame.

    The rig is bolted down, so the chart barely moves - but a camera can
    drift a pixel or two over a session, and that drift is enough to put a
    sample point on a grid line instead of a patch. This finds the chart's
    picture in the new frame and shifts all 6 points by however far it
    moved. If it can't find it confidently, nothing is moved."""
    points = [np.array(p, float) for p in saved["points"]]
    reference = saved.get("reference")
    if reference is None:
        return points

    x0, y0, x1, y1 = saved["crop"]
    ref_h, ref_w = reference.shape[:2]
    sx0, sy0 = max(0, x0 - search), max(0, y0 - search)
    sx1 = min(frame.shape[1], x1 + search)
    sy1 = min(frame.shape[0], y1 + search)
    window = frame[sy0:sy1, sx0:sx1]
    if window.shape[0] < ref_h or window.shape[1] < ref_w:
        return points

    match = cv2.matchTemplate(window, reference, cv2.TM_CCOEFF_NORMED)
    _, quality, _, location = cv2.minMaxLoc(match)
    if quality < 0.5:
        return points
    shift = np.array([sx0 + location[0] - x0, sy0 + location[1] - y0], float)
    return [p + shift for p in points]


def sample_patch_colours(frame, points, radius=6):
    """The actual measured colour at each colour-standard point - median of
    a small disc, so a single dusty pixel can't skew it."""
    height, width = frame.shape[:2]
    colours = []
    for point in points:
        x, y = int(round(point[0])), int(round(point[1]))
        x0, x1 = max(0, x - radius), min(width, x + radius + 1)
        y0, y1 = max(0, y - radius), min(height, y + radius + 1)
        patch = frame[y0:y1, x0:x1].reshape(-1, 3)
        if len(patch) == 0:
            colours.append((0, 0, 0))
        else:
            colours.append(tuple(int(v) for v in np.median(patch, axis=0)))
    return colours


# =====================================================================
# NEW - DRAWING
# =====================================================================

def annotate(frame, result):
    """Draw everything found onto a copy of the image so you can check it
    at a glance."""
    canvas = frame.copy()
    height, width = canvas.shape[:2]
    text_scale = max(0.32, min(width, height) / 1600.0)
    dot = max(2, int(min(width, height) / 400))

    if result.get("circle") is not None:
        cx, cy, r = result["circle"]
        cv2.circle(canvas, (int(cx), int(cy)), int(r), (255, 0, 0), 2)

    ring_width = result.get("ring_display_width", RING_DISPLAY_WIDTH)
    if result.get("ring_mask") is not None and ring_width > 0:
        # Draw just the ring's own boundary lines, not a solid fill, so the
        # fish underneath stays visible. contours of the ring mask give the
        # inner edge (against the fish) and outer edge in one pass.
        ring_contours, _ = cv2.findContours(result["ring_mask"], cv2.RETR_LIST,
                                            cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(canvas, ring_contours, -1, (0, 255, 0), ring_width)

    if result.get("fish_contour") is not None:
        cv2.drawContours(canvas, [result["fish_contour"]], -1, (0, 0, 255), 1)

    if result.get("scale_bar") is not None:
        a, b, length = result["scale_bar"]
        cv2.line(canvas, tuple(np.int32(a)), tuple(np.int32(b)), (255, 0, 255), 2)
        cv2.putText(canvas, f"{length:.1f}px = {SCALE_BAR_MM:.0f}mm",
                    (int(a[0]), max(14, int(a[1]) - 8)), cv2.FONT_HERSHEY_SIMPLEX,
                    text_scale * 1.2, (255, 0, 255), 1, cv2.LINE_AA)

    landmarks = result.get("landmarks")
    if landmarks is not None:
        if len(landmarks) == TOTAL_LANDMARKS:
            loop = np.int32([landmarks[i] for i in PERIMETER_ORDER])
            cv2.polylines(canvas, [loop], True, (150, 150, 150), 1, cv2.LINE_AA)
        outline = np.int32(landmarks[len(FIXED_LANDMARK_NAMES):])
        for point in outline:
            cv2.circle(canvas, tuple(point), dot, (0, 200, 255), -1)
        for number, point in enumerate(landmarks, start=1):
            x, y = int(round(point[0])), int(round(point[1]))
            is_fixed = number <= len(FIXED_LANDMARK_NAMES)
            colour = (0, 0, 255) if is_fixed else (0, 200, 255)
            if is_fixed:
                cv2.circle(canvas, (x, y), dot + 2, colour, -1)
                cv2.circle(canvas, (x, y), dot + 4, (255, 255, 255), 1)
            cv2.putText(canvas, str(number), (x + dot + 3, y - dot - 2),
                        cv2.FONT_HERSHEY_SIMPLEX, text_scale, colour, 1, cv2.LINE_AA)

    standard = result.get("colour_standard")
    if standard is not None:
        for offset, point in enumerate(standard):
            x, y = int(round(point[0])), int(round(point[1]))
            cv2.circle(canvas, (x, y), dot + 3, (255, 255, 0), 2)
            cv2.putText(canvas, f"{TOTAL_LANDMARKS + 1 + offset} {COLOUR_STANDARD_NAMES[offset]}",
                        (x + dot + 4, y - dot - 3), cv2.FONT_HERSHEY_SIMPLEX,
                        text_scale, (255, 255, 0), 1, cv2.LINE_AA)

    return canvas


# =====================================================================
# NEW - REVIEW WINDOW
# =====================================================================



REVIEW_HELP_LINES = [
    "wheel / + - = zoom at cursor    right-drag or arrows = pan    0 = fit to window",
    "left-click = place a point    drag a point to move it    U = undo    Q = quit",
]

# The buttons drawn along the top of the review window. Each is
# (label, keyboard shortcut, action name).
TOOLBAR_BUTTONS = [
    ("Fill in points", "SPACE", "fill"),
    ("Undo", "U", "undo"),
    ("Reset all 36", "E", "keepedits"),
    ("Clear 7", "C", "clear"),
    ("Scale bar", "S", "scale"),
    ("Color std", "K", "colour"),
    ("Prev std", "J", "prevstd"),
    ("Type label", "T", "typelabel"),
    ("Place all 43", "A", "manual_all"),
    ("Previous", "P", "history"),
    ("Default shape", "G", "template"),
    ("Move shape", "M", "move"),
    ("Back", "B", "back"),
    ("Skip frame", "X", "skip"),
    ("Zoom +", "+", "zoomin"),
    ("Zoom -", "-", "zoomout"),
    ("Fit", "0", "fit"),
    ("Next image", "ENTER", "next"),
]

# Arrow-key codes differ by platform: Windows sends 2424832 etc through
# waitKeyEx, GTK/Linux sends 65361 etc, and some builds report 81-84.
ARROW_LEFT = (2424832, 65361, 81)
ARROW_UP = (2490368, 65362, 82)
ARROW_RIGHT = (2555904, 65363, 83)
ARROW_DOWN = (2621440, 65364, 84)

TOOLBAR_HEIGHT = 172
VIEW_WIDTH = 1500
VIEW_HEIGHT = 950


def _wheel_delta(flags):
    """Which way the mouse wheel turned.

    OpenCV packs the wheel movement into the HIGH 16 bits of flags as a
    signed value, and leaves the low bits for modifier keys. Testing
    flags > 0 therefore gets the direction wrong: on Windows a scroll in
    either direction often arrives as a large number whose sign has
    nothing to do with which way the wheel went. cv2.getMouseWheelDelta
    does this properly but isn't present in every build, so unpack it by
    hand when it's missing."""
    if hasattr(cv2, "getMouseWheelDelta"):
        try:
            return cv2.getMouseWheelDelta(flags)
        except Exception:
            pass
    high = (int(flags) >> 16) & 0xFFFF
    if high > 32767:            # it's a signed 16-bit value
        high -= 65536
    if high != 0:
        return high
    return 1 if flags > 0 else -1


def review_window(frame, result, window_name="review", start_mode="place",
                  view_state=None, options_allow_incomplete=False):
    """Place and check landmarks, with zoom and pan.

    The workflow is deliberately two-stage so nothing is committed before
    you've looked at it:

      1. You click the 7 fixed landmarks, one at a time. Nothing else is
         drawn yet. You can drag them, or press Clear 7 to start over.
      2. Press "Fill in points" and the other 36 appear along the curve.
         You can then drag any of the 43.
      3. Only "Next image" moves on, and it refuses to until the points
         have actually been filled in - so an image can't be skipped by a
         stray keypress.

    Returns "ok" or "quit"."""
    image_h, image_w = frame.shape[:2]
    view_h = VIEW_HEIGHT - TOOLBAR_HEIGHT

    state = {
        "mode": start_mode,          # place | review | scale | colour
        "clicks": [],                # the 7 being placed
        "dragging": None,            # index of landmark being dragged
        "history": [],
        "zoom": 1.0,
        "pan": np.array([0.0, 0.0]),  # image coord shown at top-left of the view
        "message": "",
        "box_start": None,          # label box being dragged
        "history_index": 0,         # which previous landmarking is shown
        "history_offset": np.zeros(2),   # dragging the preview into position
        "history_flip": False,           # mirrored to match a fish facing the other way
        "history_angle": 0.0,            # degrees, to match a fish lying at an angle
        "history_scale": 1.0,            # for a fish nearer or further from the camera
        "move_from": None,          # anchor while dragging the whole shape
        "go_back": False,           # returning to the previous frame
        "typing": False,            # editing the label text by hand
        "filled": result.get("landmarks") is not None,
        "quit": False,
        "done": False,
    }

    def fit_to_window():
        state["zoom"] = min(VIEW_WIDTH / image_w, view_h / image_h)
        state["pan"] = np.array([
            (image_w - VIEW_WIDTH / state["zoom"]) / 2.0,
            (image_h - view_h / state["zoom"]) / 2.0,
        ])

    # Carry the zoom and pan over from the previous image, so you stay
    # zoomed in on the fish instead of re-zooming every time. Only fit to
    # the window if nothing has been set yet, or the image size changed.
    if view_state and view_state.get("zoom") and view_state.get("shape") == (image_h, image_w):
        state["zoom"] = view_state["zoom"]
        state["pan"] = np.array(view_state["pan"], float)
    else:
        fit_to_window()

    if state["filled"]:
        state["mode"] = "review"

    def to_image(display_x, display_y):
        """Window pixel -> original image pixel. Everything stored anywhere
        goes through this, so landmark coordinates stay in true image space
        no matter how far you've zoomed in."""
        return np.array([display_x / state["zoom"] + state["pan"][0],
                         (display_y - TOOLBAR_HEIGHT) / state["zoom"] + state["pan"][1]])

    def to_display(point):
        return (int(round((point[0] - state["pan"][0]) * state["zoom"])),
                int(round((point[1] - state["pan"][1]) * state["zoom"] + TOOLBAR_HEIGHT)))

    def to_view(point):
        """Same as to_display but relative to the image area alone, since
        the overlay is drawn on that region before the toolbar is added on
        top. Keeping these separate is what stops the markers being drawn
        one toolbar-height away from where they actually are."""
        return (int(round((point[0] - state["pan"][0]) * state["zoom"])),
                int(round((point[1] - state["pan"][1]) * state["zoom"])))

    def zoom_by(factor, at_x, at_y):
        """Zoom keeping whatever is under the cursor stationary."""
        anchor = to_image(at_x, at_y)
        state["zoom"] = float(np.clip(state["zoom"] * factor, 0.05, 40.0))
        state["pan"] = np.array([
            anchor[0] - at_x / state["zoom"],
            anchor[1] - (at_y - TOOLBAR_HEIGHT) / state["zoom"],
        ])

    def snapshot():
        state["history"].append((
            None if result.get("landmarks") is None else result["landmarks"].copy(),
            [c.copy() for c in state["clicks"]],
            state["filled"],
            result.get("scale_bar"),
            None if result.get("colour_standard") is None
            else [p.copy() for p in result["colour_standard"]],
            dict(result.get("locked_semilandmarks", {})),
            # The drawn curve has to be saved too. Without it, undo put the
            # points back but left the outline showing the previous shape.
            None if result.get("outline") is None else np.array(result["outline"]).copy(),
        ))
        state["history"] = state["history"][-60:]

    def button_rects():
        """Lay the buttons out, wrapping onto a second row when they no
        longer fit across the window. With thirteen of them a single row
        ran 155px past the edge and the last two were unreachable."""
        rects, x, row = {}, 12, 0
        for label, shortcut, action in TOOLBAR_BUTTONS:
            if action == "keepedits":
                label = f"Reset all {sum(SEMILANDMARKS_PER_SEGMENT)}: ON" if result.get("reset_all_edits") \
                    else f"Reset all {sum(SEMILANDMARKS_PER_SEGMENT)}: OFF"
            # Sized for a fingertip, not a mouse pointer: roughly 44px
            # tall, which is the usual minimum for a reliable touch target.
            width = 44 + 10 * len(label)
            if x + width > VIEW_WIDTH - 12:
                row += 1
                x = 12
            top = 60 + row * 52
            rects[action] = (x, top, x + width, top + 44, label, shortcut)
            x += width + 10
        return rects

    def current_seven():
        """The 7 fixed landmarks as they stand right now - either the ones
        you've just clicked, or the ones already on screen that you've been
        dragging. This is what lets you nudge the existing red points and
        press ENTER, instead of having to place all 7 from scratch."""
        if len(state["clicks"]) == len(FIXED_LANDMARK_NAMES):
            return [c.copy() for c in state["clicks"]]
        if result.get("landmarks") is not None:
            return [result["landmarks"][i].copy() for i in range(len(FIXED_LANDMARK_NAMES))]
        return None

    def do_fill():
        # Points placed by hand are treated exactly like points you dragged:
        # SPACE re-flows from the 7 fixed ones and puts any semilandmark
        # that's out of sequence back in order, keeping the rest where you
        # put them. Hand-placing all 43 shouldn't opt you out of the tidying
        # that makes the numbering run correctly round the fish.
        if result.get("all_manual") and result.get("landmarks") is not None:
            result["locked_semilandmarks"] = {
                i: result["landmarks"][i].copy()
                for i in range(len(FIXED_LANDMARK_NAMES), TOTAL_LANDMARKS)
            }
            result["all_manual"] = False
        seven = current_seven()
        if seven is None:
            have = len(state["clicks"])
            state["message"] = (f"Place all {len(FIXED_LANDMARK_NAMES)} points first "
                                f"({have} so far).")
            return
        snapshot()
        # Always re-flow against the REAL detected fish outline
        # (result["raw_outline"]), never against whatever curve got drawn
        # last time. Earlier this used result["outline"], but that gets
        # overwritten below with the drawing curve - which is a synthetic
        # spline whenever any point falls off the real outline. Once that
        # happened once, every later fill silently re-flowed against the
        # spline instead of the fish's actual edge, so dragging a point
        # and pressing SPACE again looked like it did nothing.
        landmarks, curve = landmarks_from_seven_points(
            seven, result.get("raw_outline"), follow=result.get("follow", "auto"))

        # SPACE keeps the yellow points you've moved, but puts any that
        # have drifted out of numerical order back into sequence - a point
        # dragged outside its own stretch of the fish gets re-placed
        # between the correct neighbours. "Reset all" (E) instead throws
        # every manual edit away and re-places all 36 evenly.
        moved = result.get("locked_semilandmarks", {})
        if moved and not result.get("reset_all_edits"):
            with_edits = landmarks.copy()
            for index, point in moved.items():
                if index < len(with_edits):
                    with_edits[index] = point
            landmarks = reconcile_semilandmarks(
                with_edits, landmarks, set(moved.keys()), np.asarray(seven, float),
                result.get("raw_outline"), FORCE_BODY_CURVE_SEGMENTS)
            curve = landmarks
        else:
            result["locked_semilandmarks"] = {}

        crosses, crossings = shape_self_intersects(landmarks)
        result["shape_self_intersects"] = int(crosses)
        if crosses:
            state["message"] = (f"WARNING: the outline crosses itself in "
                                f"{crossings} place(s) - some points are out of "
                                f"order. Check before moving on.")

        result["landmarks"] = landmarks
        result["outline"] = curve      # for drawing only - see raw_outline above
        result["hand_placed"] = True
        state["clicks"] = []
        state["filled"] = True
        state["mode"] = "review"
        n_moved = len(moved)
        if n_moved and not result.get("reset_all_edits"):
            state["message"] = (f"Re-flowed, keeping {n_moved} moved "
                                f"point{'s' if n_moved != 1 else ''} and fixing any "
                                f"out of order.")
        else:
            state["message"] = (f"All {sum(SEMILANDMARKS_PER_SEGMENT)} re-placed along the curve between the {len(FIXED_LANDMARK_NAMES)}. "
                                "Check, then Next image.")

    def do_keepedits():
        """Toggle whether manual nudges to yellow points survive a SPACE
        re-flow. Off by default: the protocol places the 36 semilandmarks
        evenly between the 7 fixed points, so a re-flow should normally put
        a mis-dragged point back where it belongs."""
        result["reset_all_edits"] = not result.get("reset_all_edits")
        if result["reset_all_edits"]:
            state["message"] = "Reset mode ON - SPACE discards all manual edits."
        else:
            state["message"] = "Reset mode OFF - SPACE keeps your edits and fixes their order."

    def do_prev_standard():
        """Copy the colour standard from an earlier frame of this video.

        For frames where the chart is glared out, blurred or blocked by
        the fish. The rig doesn't move within a video, so the previous
        frame's positions are still right - but the frame is marked in the
        CSV as having borrowed them, so these can be excluded later if the
        borrowed calibration turns out to matter."""
        previous = result.get("previous_colour_standard")
        if previous is None:
            state["message"] = ("No earlier color standard for this video - "
                                "place it with K on this frame.")
            return
        snapshot()
        result["colour_standard"] = [np.asarray(p, float).copy() for p in previous]
        result["colour_standard_source"] = "borrowed-from-previous-frame"
        state["message"] = ("Using the previous frame's color standard - "
                            "recorded in the CSV as borrowed.")

    def start_typing():
        snapshot()
        state["typing"] = True
        state["label_before_typing"] = result.get("label", "")
        state["message"] = "Type the label - ENTER to confirm, ESC to cancel."

    def do_undo():
        """Step back one action. Shared by the U key and the Undo button, so
        the two can't drift apart.

        While you're part-way through clicking a sequence - the 7 points,
        all 43, the colour standard, the scale bar - undo removes just the
        LAST POINT you placed, not the whole sequence. Undoing ten careful
        clicks because the eleventh was slightly off is not useful."""
        if state["clicks"] and state["mode"] in ("place", "manual_all",
                                                 "colour", "scale"):
            removed = state["clicks"].pop()
            state["message"] = (f"Removed point {len(state['clicks']) + 1}. "
                                f"{len(state['clicks'])} placed.")
            return

        if not state["history"]:
            state["message"] = "Nothing to undo."
            return
        landmarks, clicks, filled, scale_bar, standard, locked, outline = state["history"].pop()
        result["landmarks"] = landmarks
        state["clicks"] = clicks
        state["filled"] = filled
        state["mode"] = "review" if filled else "place"
        result["scale_bar"] = scale_bar
        result["colour_standard"] = standard
        result["locked_semilandmarks"] = locked
        result["outline"] = outline
        state["message"] = f"Undone. {len(state['history'])} step(s) left."

    def do_clear():
        snapshot()
        state["clicks"] = []
        result["landmarks"] = None
        result["locked_semilandmarks"] = {}
        state["filled"] = False
        state["mode"] = "place"
        state["message"] = f"Cleared - place the {len(FIXED_LANDMARK_NAMES)} points again."

    def do_history():
        """Scroll back through landmarks already accepted for this fish and
        reuse one. When the fish has barely moved between frames, copying
        the previous frame's 43 points and nudging them into place is much
        faster than starting again - and it's the obvious fallback when
        automatic detection has failed."""
        history = result.get("landmark_history") or []
        if not history:
            state["message"] = ("No earlier landmarks for this video yet - "
                                "this is the first frame.")
            return
        state["mode"] = "history"
        state["history_index"] = len(history) - 1
        reset_history_transform()
        state["message"] = ("Left/right arrows to scroll, ENTER to use it, "
                            "ESC to cancel.")

    def do_template():
        """Drop the profile's default shape onto the frame, ready to drag,
        flip, turn and resize into place. It is the first entry in the
        Previous list, so this just jumps straight to it."""
        history = result.get("landmark_history") or []
        if not history or not history[0].get("is_template"):
            state["message"] = ("This animal profile has no default shape. "
                                "Make one with 'Create your own' in Rainfish.")
            return
        state["mode"] = "history"
        state["history_index"] = 0
        reset_history_transform()
        state["message"] = ("DEFAULT SHAPE: drag to move, F flip, [ ] turn, - = size, "
                            "ENTER to use it, ESC to cancel.")

    def preview_points():
        """The chosen previous shape with the current move/flip/turn/size
        adjustments applied."""
        history = result.get("landmark_history") or []
        if not history:
            return None
        chosen = history[min(state["history_index"], len(history) - 1)]
        return transform_landmarks(chosen["landmarks"],
                                   offset=state.get("history_offset"),
                                   flip=state.get("history_flip", False),
                                   angle=state.get("history_angle", 0.0),
                                   scale=state.get("history_scale", 1.0))

    def reset_history_transform():
        state["history_offset"] = np.zeros(2)
        state["history_flip"] = False
        state["history_angle"] = 0.0
        state["history_scale"] = 1.0

    def apply_history():
        history = result.get("landmark_history") or []
        if not history:
            return
        chosen = history[state["history_index"]]
        snapshot()
        result["landmarks"] = preview_points()
        result["outline"] = result["landmarks"]
        result["locked_semilandmarks"] = {}
        result["hand_placed"] = True
        state["filled"] = True
        state["clicks"] = []
        state["mode"] = "review"
        state["message"] = (f"Copied from {chosen['name']}. Press M to drag the "
                            f"whole shape onto this animal, then adjust points.")

    def do_move():
        """Drag all 43 points together, keeping their shape. Use after
        copying a previous frame's landmarks: line the shape up with where
        the fish is now, then fix individual points."""
        if result.get("landmarks") is None:
            state["message"] = "Nothing to move yet."
            return
        state["mode"] = "move"
        state["message"] = f"Drag anywhere to move all {TOTAL_LANDMARKS} points together."

    def do_manual_all():
        """Place all 43 points by hand, in protocol order.

        For frames where the automatic placement is too far out to be worth
        correcting. If the 7 fixed points are already placed they're kept
        as the first 7 clicks, so you only click the 36 semilandmarks; the
        prompt names each one and says which stretch it belongs to."""
        snapshot()
        seven = current_seven()
        if seven is not None:
            state["clicks"] = [np.asarray(p, float).copy() for p in seven]
            state["message"] = (f"Keeping your {len(FIXED_LANDMARK_NAMES)} fixed points - now click the {sum(SEMILANDMARKS_PER_SEGMENT)} "
                                "semilandmarks in order.")
        else:
            state["clicks"] = []
            state["message"] = f"Click all {TOTAL_LANDMARKS} in order, starting with landmark 1."
        result["landmarks"] = None
        state["filled"] = False
        state["mode"] = "manual_all"

    def do_back():
        """Return to the previous frame to redo it.

        For when you press ENTER a moment too early. The previous frame's
        saved result is discarded so it comes up fresh, and you land back
        on it rather than having to restart the whole folder."""
        state["go_back"] = True
        state["done"] = True

    def do_skip():
        """Mark this frame unusable and move on.

        For frames where no honest landmarking is possible: the fish is
        turned away from the camera rather than lateral, part of it is
        outside the frame, or it's obscured. Landmarking those anyway
        would feed Colormesh a fish warped from the wrong pose, which
        produces colour readings that look fine but aren't comparable.
        Skipping records the frame and the reason in the CSV, writes no
        TPS file (so Colormesh never sees it), and moves on."""
        result["skipped"] = True
        result["landmarks"] = None
        if not result.get("skip_reason"):
            result["skip_reason"] = "marked unusable"
        state["done"] = True

    def do_next():
        if not state["filled"] or result.get("landmarks") is None:
            state["message"] = "Nothing to save yet - press 'Fill in points' first."
            return

        # Don't let a half-finished frame through. A frame missing its
        # colour standard can't be calibrated and fails silently later in
        # Colormesh - that's what produced the 18 dropped frames in the
        # pilot. Skip (X) is the deliberate way past an unusable frame.
        missing = outstanding_items(result)
        if missing and not options_allow_incomplete:
            state["message"] = ("Still to do: " + ", ".join(missing)
                                + ".  Press X to skip this frame instead, or "
                                  "run with --allow-incomplete.")
            return
        state["done"] = True

    def on_mouse(event, x, y, flags, _):
        # --- toolbar ---
        if y < TOOLBAR_HEIGHT:
            if event == cv2.EVENT_LBUTTONDOWN:
                for action, (x0, y0, x1, y1, _, _) in button_rects().items():
                    if x0 <= x <= x1 and y0 <= y <= y1:
                        {"fill": do_fill, "clear": do_clear, "next": do_next,
                         "skip": do_skip, "manual_all": do_manual_all,
                         "back": do_back,
                         "history": do_history, "move": do_move,
                         "template": do_template,
                         "undo": do_undo, "keepedits": do_keepedits,
                         "fit": fit_to_window,
                         "zoomin": lambda: zoom_by(
                             1.3, VIEW_WIDTH // 2, TOOLBAR_HEIGHT + view_h // 2),
                         "zoomout": lambda: zoom_by(
                             1 / 1.3, VIEW_WIDTH // 2, TOOLBAR_HEIGHT + view_h // 2),
                         "scale": lambda: state.update(mode="scale", clicks=[]),
                         "typelabel": lambda: start_typing(),
                         "prevstd": do_prev_standard,
                         "colour": lambda: state.update(mode="colour", clicks=[]),
                         }[action]()
                        return
            return

        point = to_image(x, y)

        # --- pan with the right button, at any time ---
        if event == cv2.EVENT_RBUTTONDOWN:
            state["pan_from"] = (x, y, state["pan"].copy())
            return
        if event == cv2.EVENT_MOUSEMOVE and state.get("pan_from") and (flags & cv2.EVENT_FLAG_RBUTTON):
            x0, y0, pan0 = state["pan_from"]
            state["pan"] = pan0 - np.array([(x - x0) / state["zoom"], (y - y0) / state["zoom"]])
            return
        if event == cv2.EVENT_RBUTTONUP:
            state["pan_from"] = None
            return

        # --- zoom on the wheel ---
        if event == cv2.EVENT_MOUSEWHEEL:
            # The wheel's direction lives in the HIGH 16 bits of flags, not
            # in its sign - testing flags > 0 gets the direction wrong on
            # Windows, where flags is often a large negative number for a
            # scroll in either direction. getMouseWheelDelta reads it
            # properly. Steps are also finer now (1.15x rather than 1.25x)
            # so you can settle on a zoom level instead of overshooting.
            delta = _wheel_delta(flags)
            zoom_by(1.15 if delta > 0 else 1.0 / 1.15, x, y)
            return

        # --- placing the 7 ---
        if state["mode"] == "place":
            if event == cv2.EVENT_LBUTTONDOWN:
                if len(state["clicks"]) < len(FIXED_LANDMARK_NAMES):
                    snapshot()
                    state["clicks"].append(point)
                    if len(state["clicks"]) == len(FIXED_LANDMARK_NAMES):
                        state["message"] = (f"All {len(FIXED_LANDMARK_NAMES)} placed. Drag any that are off, "
                                            "then press 'Fill in points'.")
                else:
                    # all 7 down - clicking now grabs the nearest to adjust
                    distances = [np.linalg.norm(c - point) for c in state["clicks"]]
                    snapshot()
                    state["dragging"] = int(np.argmin(distances))
            elif event == cv2.EVENT_MOUSEMOVE and state["dragging"] is not None:
                state["clicks"][state["dragging"]] = point
            elif event == cv2.EVENT_LBUTTONUP:
                state["dragging"] = None

        # --- adjusting the filled-in 43 ---
        elif state["mode"] == "review":
            if event == cv2.EVENT_LBUTTONDOWN:
                # Grab whichever is nearer: a fish landmark or one of the 6
                # colour-standard points. That way a mis-detected patch can
                # be nudged onto the right cell without redoing all six.
                best, best_distance, best_kind = None, np.inf, None
                if result.get("landmarks") is not None:
                    d = np.linalg.norm(result["landmarks"] - point, axis=1)
                    best, best_distance, best_kind = int(np.argmin(d)), float(d.min()), "lm"
                if result.get("colour_standard") is not None:
                    d = [float(np.linalg.norm(np.asarray(p) - point))
                         for p in result["colour_standard"]]
                    if min(d) < best_distance:
                        best, best_distance, best_kind = int(np.argmin(d)), min(d), "cs"
                if best is not None:
                    snapshot()
                    state["dragging"] = best
                    state["drag_kind"] = best_kind
            elif event == cv2.EVENT_MOUSEMOVE and state["dragging"] is not None:
                if state.get("drag_kind") == "cs":
                    result["colour_standard"][state["dragging"]] = point
                else:
                    result["landmarks"][state["dragging"]] = point
                    if state["dragging"] >= len(FIXED_LANDMARK_NAMES):
                        # A manually-moved yellow (semilandmark) point should
                        # survive the next SPACE re-flow instead of being
                        # silently recomputed away - do_fill() checks this
                        # dict and reapplies it after recomputing the 36.
                        # Dragging one of the first 7 (red) points doesn't
                        # need this: those are always exactly what you
                        # clicked, by construction.
                        result.setdefault("locked_semilandmarks",
                                          {})[state["dragging"]] = point.copy()
            elif event == cv2.EVENT_LBUTTONUP:
                state["dragging"] = None

        elif state["mode"] == "scale" and event == cv2.EVENT_LBUTTONDOWN:
            state["clicks"].append(point)
            if len(state["clicks"]) == 2:
                snapshot()
                a, b = state["clicks"]
                result["scale_bar"] = (a, b, float(np.linalg.norm(a - b)))
                state["clicks"] = []
                state["mode"] = "review" if state["filled"] else "place"
                state["message"] = f"Scale bar set: {result['scale_bar'][2]:.1f} px."

        elif state["mode"] == "history":
            # Drag the previewed shape into position BEFORE applying it,
            # which is the point of previewing: line the old outline up
            # with where the fish is now, then press ENTER.
            if event == cv2.EVENT_LBUTTONDOWN:
                state["move_from"] = point.copy()
            elif event == cv2.EVENT_MOUSEMOVE and state.get("move_from") is not None:
                state["history_offset"] = (state.get("history_offset", np.zeros(2))
                                           + (point - state["move_from"]))
                state["move_from"] = point.copy()
            elif event == cv2.EVENT_LBUTTONUP:
                state["move_from"] = None

        elif state["mode"] == "move":
            if event == cv2.EVENT_LBUTTONDOWN:
                snapshot()
                state["move_from"] = point.copy()
            elif event == cv2.EVENT_MOUSEMOVE and state.get("move_from") is not None:
                shift = point - state["move_from"]
                result["landmarks"] = result["landmarks"] + shift
                if result.get("outline") is not None:
                    result["outline"] = result["landmarks"]
                state["move_from"] = point.copy()
            elif event == cv2.EVENT_LBUTTONUP:
                state["move_from"] = None

        elif state["mode"] == "manual_all" and event == cv2.EVENT_LBUTTONDOWN:
            if len(state["clicks"]) < TOTAL_LANDMARKS:
                state["clicks"].append(point)
                if len(state["clicks"]) == TOTAL_LANDMARKS:
                    snapshot()
                    result["landmarks"] = np.array(state["clicks"], dtype=np.float64)
                    result["outline"] = result["landmarks"]
                    result["hand_placed"] = True
                    result["all_manual"] = True
                    result["locked_semilandmarks"] = {}
                    state["clicks"] = []
                    state["filled"] = True
                    state["mode"] = "review"
                    state["message"] = (f"All {TOTAL_LANDMARKS} placed by hand. SPACE will NOT "
                                        "re-flow them - press ENTER when happy.")

        elif state["mode"] == "colour" and event == cv2.EVENT_LBUTTONDOWN:
            state["clicks"].append(point)
            if len(state["clicks"]) == len(COLOUR_STANDARD_NAMES):
                snapshot()
                result["colour_standard"] = list(state["clicks"])
                result["colour_standard_source"] = "clicked"
                state["clicks"] = []
                state["mode"] = "review" if state["filled"] else "place"
                state["message"] = "Color standard set."

    cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)
    cv2.setMouseCallback(window_name, on_mouse)

    while not state["done"] and not state["quit"]:
        # --- the photo, zoomed and panned ---
        transform = np.float32([
            [state["zoom"], 0, -state["pan"][0] * state["zoom"]],
            [0, state["zoom"], -state["pan"][1] * state["zoom"]],
        ])
        view = cv2.warpAffine(frame, transform, (VIEW_WIDTH, view_h),
                              flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT,
                              borderValue=(35, 35, 35))

        _draw_overlay(view, result, state, to_view)

        # --- toolbar ---
        canvas = np.zeros((VIEW_HEIGHT, VIEW_WIDTH, 3), np.uint8)
        canvas[TOOLBAR_HEIGHT:] = view
        canvas[:TOOLBAR_HEIGHT] = (28, 28, 28)

        for action, (x0, y0, x1, y1, label, shortcut) in button_rects().items():
            enabled = not (action == "next" and not state["filled"]) \
                      and not (action == "undo" and not state["history"])
            fill_colour = (58, 58, 58) if enabled else (38, 38, 38)
            text_colour = (255, 255, 255) if enabled else (110, 110, 110)
            if action == "keepedits":
                fill_colour = (30, 60, 140) if result.get("reset_all_edits") else (48, 48, 48)
            if action == "fill" and current_seven() is not None:
                fill_colour = (40, 130, 40)  # ready to press
            if action == "next" and state["filled"]:
                fill_colour = (120, 80, 20)
            cv2.rectangle(canvas, (x0, y0), (x1, y1), fill_colour, -1)
            cv2.rectangle(canvas, (x0, y0), (x1, y1), (95, 95, 95), 1)
            cv2.putText(canvas, label, (x0 + 14, y0 + 28),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, text_colour, 1, cv2.LINE_AA)
            # Shortcut goes INSIDE the button, bottom-right. Above the
            # button it overlapped the progress bar, and it also makes the
            # whole rectangle one touch target rather than having text
            # floating outside it.
            cv2.putText(canvas, shortcut,
                        (x1 - 12 - 7 * len(shortcut), y1 - 6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.32, (135, 135, 135), 1,
                        cv2.LINE_AA)

        _draw_progress_header(canvas, result)
        _draw_checklist(canvas, result, state, len(state["clicks"]))

        # --- status line ---
        if state["typing"]:
            status = f"TYPE LABEL:  {result.get('label','')}_"
            status_colour = (120, 230, 255)
        elif state["mode"] == "history":
            history = result.get("landmark_history") or []
            index = min(state.get("history_index", 0), max(0, len(history) - 1))
            shown = history[index]["name"] if history else "-"
            bits = []
            if state.get("history_flip"):
                bits.append("mirrored")
            if state.get("history_angle"):
                bits.append(f"{state['history_angle']:+.0f} deg")
            if state.get("history_scale", 1.0) != 1.0:
                bits.append(f"{state['history_scale'] * 100:.0f}%")
            adjust = ("  [" + ", ".join(bits) + "]") if bits else ""
            status = (f"PREVIOUS {index + 1}/{len(history)}: {shown}{adjust}"
                      f"   -  drag=move  F=flip  [ ]=turn  + -=size  "
                      f"R=reset  ENTER=use  ESC=cancel")
            status_colour = (120, 230, 255)
        elif state["mode"] == "history":
            # Drag the previewed shape into position BEFORE applying it,
            # which is the point of previewing: line the old outline up
            # with where the fish is now, then press ENTER.
            if event == cv2.EVENT_LBUTTONDOWN:
                state["move_from"] = point.copy()
            elif event == cv2.EVENT_MOUSEMOVE and state.get("move_from") is not None:
                state["history_offset"] = (state.get("history_offset", np.zeros(2))
                                           + (point - state["move_from"]))
                state["move_from"] = point.copy()
            elif event == cv2.EVENT_LBUTTONUP:
                state["move_from"] = None

        elif state["mode"] == "move":
            status = f"MOVE SHAPE: drag anywhere to move all {TOTAL_LANDMARKS} together (M to exit)"
            status_colour = (120, 230, 255)
        elif state["mode"] == "manual_all":
            next_number = len(state["clicks"]) + 1
            if next_number > TOTAL_LANDMARKS:
                status = f"All {TOTAL_LANDMARKS} placed."
            else:
                status = (f"PLACE LANDMARK {next_number} OF {TOTAL_LANDMARKS}:  "
                          f"{describe_landmark(next_number)}")
            status_colour = (120, 230, 255)
        elif state["mode"] == "place" and len(state["clicks"]) < len(FIXED_LANDMARK_NAMES):
            nxt = FIXED_LANDMARK_NAMES[len(state["clicks"])].replace("_", " ").upper()
            status = f"CLICK LANDMARK {len(state['clicks']) + 1} OF {len(FIXED_LANDMARK_NAMES)}:  {nxt}"
            status_colour = (80, 220, 255)
        elif state["mode"] == "scale":
            status = f"SCALE BAR: click the two ends ({len(state['clicks'])}/2)"
            status_colour = (255, 0, 255)
        elif state["mode"] == "colour":
            status = (f"COLOR STANDARD: click "
                      f"'{COLOUR_STANDARD_NAMES[len(state['clicks'])]}' "
                      f"({len(state['clicks'])}/6)")
            status_colour = (255, 255, 0)
        elif not state["filled"]:
            status = f"All {len(FIXED_LANDMARK_NAMES)} placed - press 'Fill in points' (ENTER)"
            status_colour = (120, 230, 120)
        else:
            status = f"{result.get('name', '')}  -  {TOTAL_LANDMARKS} points placed, check then Next image"
            status_colour = (220, 220, 220)

        # Status and message go along the BOTTOM. They used to sit at y=20,
        # which is the same row as the buttons' keyboard-shortcut labels
        # (drawn at y0-6 = 24), so a long video name covered the controls.
        bar_top = VIEW_HEIGHT - 58
        cv2.rectangle(canvas, (0, bar_top), (VIEW_WIDTH, VIEW_HEIGHT), (22, 22, 22), -1)

        cv2.putText(canvas, status, (14, bar_top + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.56,
                    status_colour, 1, cv2.LINE_AA)
        if state["message"]:
            cv2.putText(canvas, state["message"], (14, bar_top + 38),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (170, 170, 170), 1, cv2.LINE_AA)

        for i, line in enumerate(REVIEW_HELP_LINES):
            cv2.putText(canvas, line, (VIEW_WIDTH - 690, bar_top + 20 + 15 * i),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.38, (150, 150, 150), 1, cv2.LINE_AA)
        cv2.putText(canvas, f"{state['zoom'] * 100:.0f}%", (VIEW_WIDTH - 70, bar_top + 52),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (150, 150, 150), 1, cv2.LINE_AA)

        cv2.imshow(window_name, canvas)

        raw = cv2.waitKeyEx(16)
        if raw == -1:
            continue
        # Arrow keys report different codes on Windows and Linux, and the
        # Windows ones are lost by the usual & 0xFF, so handle both here
        # before masking.
        if state["mode"] == "history":
            history = result.get("landmark_history") or []
            if raw in ARROW_LEFT or raw in ARROW_DOWN:
                state["history_index"] = max(0, state["history_index"] - 1)
                reset_history_transform()
                continue
            if raw in ARROW_RIGHT or raw in ARROW_UP:
                state["history_index"] = min(len(history) - 1,
                                             state["history_index"] + 1)
                reset_history_transform()
                continue
            masked = raw & 0xFF
            if masked in (ord("f"), ord("F")):
                state["history_flip"] = not state["history_flip"]
                state["message"] = ("Mirrored - use when the animal has turned to "
                                    "face the other way.")
                continue
            if masked in (ord("["), ord(",")):
                state["history_angle"] -= 5.0
                continue
            if masked in (ord("]"), ord(".")):
                state["history_angle"] += 5.0
                continue
            if masked in (ord("-"), ord("_")):
                state["history_scale"] = max(0.4, state["history_scale"] - 0.02)
                continue
            if masked in (ord("+"), ord("=")):
                state["history_scale"] = min(2.5, state["history_scale"] + 0.02)
                continue
            if masked in (ord("r"), ord("R")):
                reset_history_transform()
                state["message"] = "Reset to the shape as it was."
                continue
            if masked in (13, 10):
                apply_history()
                continue
            if masked == 27:
                state["mode"] = "review" if state["filled"] else "place"
                state["message"] = "Cancelled."
                continue

        if raw in ARROW_LEFT:
            state["pan"][0] -= 60 / state["zoom"]; continue
        if raw in ARROW_RIGHT:
            state["pan"][0] += 60 / state["zoom"]; continue
        if raw in ARROW_UP:
            state["pan"][1] -= 60 / state["zoom"]; continue
        if raw in ARROW_DOWN:
            state["pan"][1] += 60 / state["zoom"]; continue
        key = raw & 0xFF

        # While typing a label, keys go into the text - not to shortcuts.
        # Otherwise typing an "s" would jump into scale-bar mode mid-word.
        if state["typing"]:
            if key in (13, 10):                       # ENTER confirms
                state["typing"] = False
                result["label_source"] = "typed"
                result["label_valid"] = label_matches_known_prefix(result.get("label", ""))
                state["message"] = f"Label set to '{result.get('label','')}'."
            elif key == 27:                           # ESC cancels the edit
                state["typing"] = False
                result["label"] = state.get("label_before_typing", "")
                state["message"] = "Edit cancelled."
            elif key == 8:                            # backspace
                result["label"] = result.get("label", "")[:-1]
            elif 32 <= key < 127:
                result["label"] = result.get("label", "") + chr(key)
            continue
        pan_step = 60 / state["zoom"]
        if key in (ord("q"), ord("Q"), 27):
            state["quit"] = True
        elif key in (13, 10):            # ENTER = done with this image
            do_next()
        elif key == 32:                  # SPACE = fill in the 36
            do_fill()
        elif key in (ord("n"), ord("N")):
            do_next()
        elif key in (ord("c"), ord("C")):
            do_clear()
        elif key in (ord("s"), ord("S")):
            state["mode"], state["clicks"] = "scale", []
        elif key in (ord("k"), ord("K")):
            state["mode"], state["clicks"] = "colour", []
        elif key in (ord("j"), ord("J")):
            do_prev_standard()
        elif key in (ord("a"), ord("A")):
            do_manual_all()
        elif key in (ord("p"), ord("P")):
            do_history()
        elif key in (ord("g"), ord("G")):
            do_template()
        elif key in (ord("m"), ord("M")):
            do_move()
        elif key in (ord("b"), ord("B")):
            do_back()
        elif key in (ord("x"), ord("X")):
            do_skip()
        elif key in (ord("t"), ord("T")):
            start_typing()
        elif key == ord("0"):
            fit_to_window()
        elif key in (ord("+"), ord("=")):
            zoom_by(1.25, VIEW_WIDTH // 2, TOOLBAR_HEIGHT + view_h // 2)
        elif key in (ord("-"), ord("_")):
            zoom_by(0.8, VIEW_WIDTH // 2, TOOLBAR_HEIGHT + view_h // 2)
        elif key in (ord("u"), ord("U")):
            do_undo()
        elif key in (ord("e"), ord("E")):
            do_keepedits()

    if view_state is not None:
        view_state["zoom"] = state["zoom"]
        view_state["pan"] = [float(state["pan"][0]), float(state["pan"][1])]
        view_state["shape"] = (image_h, image_w)

    if state["quit"]:
        return "quit"
    return "back" if state.get("go_back") else "ok"


# Extras the user said they don't need (--no-label, --no-color-standard,
# --no-scale). Set once in main(); outstanding_items() then stops asking
# for them before a frame can be accepted.
NOT_REQUIRED = set()


def outstanding_items(result, n_clicks=0):
    """What still needs doing on this frame. Returns a list of names -
    empty means ready to accept.

    One definition used by both the checklist panel and the check on
    Next, so what the panel shows and what the button allows can't drift
    apart."""
    missing = []
    if "colour_standard" not in NOT_REQUIRED and result.get("colour_standard") is None:
        missing.append("color standard")
    if "label" not in NOT_REQUIRED and not result.get("label"):
        missing.append("label")
    if "scale" not in NOT_REQUIRED and result.get("scale_bar") is None:
        missing.append("scale")
    if result.get("landmarks") is None:
        missing.append("landmarks")
    return missing


def _draw_progress_header(canvas, result):
    """Where you are: which video, which frame, and how much is left.

    Without this the only clue is a line of console text behind the
    window, so it's easy to lose track of whether you're on frame 3 or 23
    of a video, or how many videos are still to go."""
    video = result.get("video_key") or ""
    frame_in_video = result.get("frame_in_video")
    frames_in_video = result.get("frames_in_video")
    video_number = result.get("video_number")
    video_total = result.get("video_total")
    position = result.get("frame_position")
    total = result.get("frame_total")

    label = result.get("label")
    heading = f"{video}"
    if label:
        heading += f"   [{label}]"
    if frame_in_video and frames_in_video:
        heading += f"   -  frame {frame_in_video} of {frames_in_video}"
    if video_number and video_total:
        heading += f"   -  video {video_number} of {video_total}"

    cv2.putText(canvas, heading, (14, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.58,
                (235, 235, 235), 1, cv2.LINE_AA)

    if not (position and total):
        return

    # Progress bar across the whole folder.
    bar_left, bar_right = 14, canvas.shape[1] - 200
    bar_top, bar_bottom = 34, 46
    cv2.rectangle(canvas, (bar_left, bar_top), (bar_right, bar_bottom),
                  (60, 60, 60), -1)
    filled_to = bar_left + int((bar_right - bar_left) * (position - 1) / max(1, total))
    cv2.rectangle(canvas, (bar_left, bar_top), (filled_to, bar_bottom),
                  (90, 180, 90), -1)

    # Tick marks where each video starts, so the bar shows video
    # boundaries rather than just an undifferentiated stretch.
    if video_total and video_total > 1:
        for boundary in range(1, video_total):
            at = bar_left + int((bar_right - bar_left) * boundary / video_total)
            cv2.line(canvas, (at, bar_top), (at, bar_bottom), (35, 35, 35), 1)

    cv2.putText(canvas, f"{position} / {total} frames",
                (bar_right + 12, bar_bottom - 1),
                cv2.FONT_HERSHEY_SIMPLEX, 0.42, (190, 190, 190), 1, cv2.LINE_AA)


def _draw_checklist(canvas, result, state, n_clicks):
    """A running checklist down the right-hand side: what's done on this
    frame and what still isn't.

    With a colour standard, a scale bar, a label, 7 fixed points and 36
    semilandmarks to get through, it's easy to press ENTER having missed
    one - and a frame that reaches Colormesh without a calibration is only
    discovered much later, in R."""
    n_fixed = len(FIXED_LANDMARK_NAMES)
    landmarks = result.get("landmarks")
    filled = landmarks is not None

    def state_of(done, detail="", warn=False):
        return ("done" if done and not warn else
                "warn" if done and warn else "todo"), detail

    # --- work out where each item stands ---
    standard = result.get("colour_standard")
    source = result.get("colour_standard_source") or ""
    items = [("Color standard", *state_of(
        standard is not None,
        source.replace("-", " ") if standard is not None else "press K"))]

    label = result.get("label")
    label_source = result.get("label_source") or ""
    items.append(("Label", *state_of(
        bool(label),
        f"{label} ({label_source})" if label else "press L, then T",
        warn=bool(label) and label_source in ("ocr", "ocr-tracked"))))

    scale = result.get("scale_bar")
    scale_source = result.get("scale_bar_source") or ""
    items.append(("Scale", *state_of(
        scale is not None,
        (f"{scale[2]:.0f}px "
         + ("(squares)" if scale_source == "colour_standard_square_width" else ""))
        if scale is not None else "press S")))

    have_seven = filled or n_clicks >= n_fixed
    items.append((f"{len(FIXED_LANDMARK_NAMES)} fixed points", *state_of(
        have_seven, "placed" if have_seven else f"{n_clicks} of {n_fixed} clicked")))

    items.append((f"{sum(SEMILANDMARKS_PER_SEGMENT)} semilandmarks", *state_of(
        filled, "placed" if filled else "press SPACE")))

    crossing = result.get("shape_self_intersects")
    if filled:
        items.append(("Outline order", *state_of(
            True,
            "crosses itself" if crossing else "clean",
            warn=bool(crossing))))

    # --- draw it ---
    panel_width = 250
    x0 = canvas.shape[1] - panel_width - 12
    y0 = TOOLBAR_HEIGHT + 12
    height = 62 + 26 * len(items)

    box = canvas[y0:y0 + height, x0:x0 + panel_width]
    if box.size:
        cv2.addWeighted(box, 0.25, np.zeros_like(box), 0.75, 0, box)
    cv2.rectangle(canvas, (x0, y0), (x0 + panel_width, y0 + height),
                  (90, 90, 90), 1)
    cv2.putText(canvas, "THIS FRAME", (x0 + 12, y0 + 22),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1, cv2.LINE_AA)

    colours = {"done": (120, 230, 120), "warn": (0, 190, 255), "todo": (150, 150, 150)}
    marks = {"done": "[x]", "warn": "[!]", "todo": "[ ]"}
    for row, (name, status, detail) in enumerate(items):
        y = y0 + 44 + row * 26
        colour = colours[status]
        cv2.putText(canvas, marks[status], (x0 + 12, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, colour, 1, cv2.LINE_AA)
        cv2.putText(canvas, name, (x0 + 46, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, colour, 1, cv2.LINE_AA)
        if detail:
            cv2.putText(canvas, detail[:26], (x0 + 46, y + 11),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.3, (140, 140, 140), 1, cv2.LINE_AA)

    # Same source of truth as the check on Next, so the panel can't say
    # "ready" while the button refuses.
    ready = not outstanding_items(result)
    cv2.putText(canvas,
                "ENTER to accept" if ready else "something still to do",
                (x0 + 12, y0 + height - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.36,
                (120, 230, 120) if ready else (0, 190, 255), 1, cv2.LINE_AA)


def _draw_overlay(view, result, state, to_display):
    """Draw landmarks onto the zoomed view. Marker and text sizes are fixed
    in SCREEN pixels, not image pixels, so they stay legible whether you're
    zoomed right out or in close on a fin."""
    height, width = view.shape[:2]

    def visible(p):
        return -50 <= p[0] <= width + 50 and -50 <= p[1] <= height + 50

    # the box currently being dragged
    if state.get("box_start") is not None and state.get("box_now") is not None:
        p0 = to_display(state["box_start"])
        p1 = to_display(state["box_now"])
        cv2.rectangle(view, p0, p1, (120, 230, 255), 1)

    if result.get("scale_bar") is not None:
        a, b, length = result["scale_bar"]
        pa, pb = to_display(a), to_display(b)
        cv2.line(view, pa, pb, (255, 0, 255), 2)
        cv2.putText(view, f"{length:.1f}px = {SCALE_BAR_MM:.0f}mm",
                    (pa[0], pa[1] - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                    (255, 0, 255), 1, cv2.LINE_AA)

    if result.get("colour_standard") is not None:
        for offset, point in enumerate(result["colour_standard"]):
            p = to_display(point)
            if not visible(p):
                continue
            cv2.circle(view, p, 7, (255, 255, 0), 2)
            cv2.putText(view, f"{TOTAL_LANDMARKS + 1 + offset} {COLOUR_STANDARD_NAMES[offset]}",
                        (p[0] + 10, p[1] - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.45,
                        (255, 255, 0), 1, cv2.LINE_AA)

    # Whatever is being clicked RIGHT NOW, in any mode. Previously this
    # only drew while placing the first 7, so clicking the scale bar or the
    # colour standard on an already-filled frame showed nothing until the
    # sequence finished and you found out whether you'd hit the right
    # spots.
    mode = state.get("mode")

    # Previewing an earlier frame's landmarks.
    if mode == "history":
        history = result.get("landmark_history") or []
        if history:
            chosen = history[min(state.get("history_index", 0), len(history) - 1)]
            pts = transform_landmarks(chosen["landmarks"],
                                      offset=state.get("history_offset"),
                                      flip=state.get("history_flip", False),
                                      angle=state.get("history_angle", 0.0),
                                      scale=state.get("history_scale", 1.0))
            loop = pts[PERIMETER_ORDER] if len(pts) == TOTAL_LANDMARKS else pts
            cv2.polylines(view, [np.array([to_display(p) for p in loop], np.int32)],
                          True, (120, 230, 255), 2, cv2.LINE_AA)
            drawn = np.array([to_display(p) for p in pts], np.int32)
            for number, p in enumerate(drawn, start=1):
                is_fixed = number <= len(FIXED_LANDMARK_NAMES)
                cv2.circle(view, tuple(p), 6 if is_fixed else 3,
                           (0, 0, 255) if is_fixed else (255, 220, 0), -1)
        return

    if state["clicks"]:
        if mode == "colour":
            names = COLOUR_STANDARD_NAMES
            colour = (255, 255, 0)
        elif mode == "scale":
            names = ["scale bar end 1", "scale bar end 2"]
            colour = (255, 0, 255)
        elif mode == "manual_all":
            names = None
            colour = (0, 0, 255)
        else:
            names = [n.replace("_", " ") for n in FIXED_LANDMARK_NAMES]
            colour = (0, 0, 255)

        for order, click in enumerate(state["clicks"], start=1):
            p = to_display(click)
            fixed_point = mode != "manual_all" or order <= len(FIXED_LANDMARK_NAMES)
            # Red is reserved for the 7 fixed anatomical landmarks. The 36
            # semilandmarks are drawn in cyan while being placed, so at a
            # glance you can see which are which.
            point_colour = colour if fixed_point else (255, 220, 0)
            cv2.circle(view, p, 7 if fixed_point else 4, point_colour, -1)
            if fixed_point:
                cv2.circle(view, p, 10, (255, 255, 255), 2)
            if names is not None and order <= len(names):
                text = f"{order} {names[order - 1]}"
            else:
                text = str(order)
            cv2.putText(view, text, (p[0] + 11, p[1] - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, point_colour, 1, cv2.LINE_AA)

        # A faint line through them in the order they will sit around the
        # fish, so a point clicked out of sequence shows up immediately.
        if len(state["clicks"]) >= 2:
            clicks = state["clicks"]
            if mode == "manual_all" and len(clicks) == TOTAL_LANDMARKS:
                sequence = [clicks[i] for i in PERIMETER_ORDER]
            else:
                sequence = clicks
            pts = [to_display(c) for c in sequence]
            for a, b in zip(pts, pts[1:]):
                cv2.line(view, a, b, (90, 90, 90), 1, cv2.LINE_AA)

    if not state["filled"] and mode != "manual_all":
        return

    landmarks = result.get("landmarks")
    if landmarks is None:
        return

    # The curve the semilandmarks were laid along.
    curve = result.get("outline")
    if curve is not None and len(curve) > 3:
        drawn = np.asarray(curve, dtype=np.float64)
        if len(drawn) == TOTAL_LANDMARKS:
            drawn = drawn[PERIMETER_ORDER]   # round the fish, not 1,2,3...
        pts = np.array([to_display(p) for p in drawn], np.int32)
        cv2.polylines(view, [pts], True, (120, 120, 120), 1, cv2.LINE_AA)

    for number, point in enumerate(landmarks, start=1):
        p = to_display(point)
        if not visible(p):
            continue
        is_fixed = number <= len(FIXED_LANDMARK_NAMES)
        if is_fixed:
            cv2.circle(view, p, 6, (0, 0, 255), -1)
            cv2.circle(view, p, 9, (255, 255, 255), 2)
        else:
            cv2.circle(view, p, 3, (0, 200, 255), -1)
        cv2.putText(view, str(number), (p[0] + 9, p[1] - 7),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42,
                    (0, 0, 255) if is_fixed else (0, 200, 255), 1, cv2.LINE_AA)

def write_tps(path, landmarks, image_name, image_height, scale=None,
              include_image=True):
    """TPS format, for Colormesh / tpsDig / geomorph / MorphoJ.

    TPS counts y upwards from the bottom of the image whereas OpenCV counts
    downwards from the top, so y is flipped on the way out. Automated_Colour_
    Extraction.R flips it back with abs(y - img.dim[2]) when it hands the
    landmarks to imager, so the two halves agree.

    scale, when given, is written as a SCALE= line - mm per pixel, taken
    from the scale bar you measured. The original ImageJ script wrote a
    SCALE line computed as (scalebar_px / landmark_1_x) / 10, which divides
    a length by an arbitrary landmark's x position and has no physical
    meaning; a real mm-per-pixel figure is written here instead."""
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(f"LM={len(landmarks)}\n")
        for x, y in landmarks:
            handle.write(f"{x:.4f} {image_height - y:.4f}\n")
        if include_image:
            handle.write(f"IMAGE={image_name}\n")
        if scale is not None:
            handle.write(f"SCALE={scale:.8f}\n")
        handle.write(f"ID={os.path.splitext(image_name)[0]}\n")


def write_points_txt(path, landmarks, colour_standard):
    """Plain numbered XY list - the same shape as ImageJ's Measure output
    for a multi-point selection."""
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(" \tLabel\tX\tY\n")
        for number, (x, y) in enumerate(landmarks, start=1):
            handle.write(f"{number}\t{LANDMARK_LABELS[number]}\t{x:.3f}\t{y:.3f}\n")
        if colour_standard is not None:
            for offset, (x, y) in enumerate(colour_standard):
                number = len(landmarks) + 1 + offset
                handle.write(f"{number}\t{COLOUR_STANDARD_NAMES[offset]}\t{x:.3f}\t{y:.3f}\n")


def csv_header():
    header = ["image", "fish_id", "label_source", "label_looks_valid",
              "usable", "skip_reason", "colour_standard_source",
              "fish_found", "scale_bar_px", "scale_bar_source", "px_per_mm", "mm_per_px",
              "background_brightness", "local_bg_brightness",
              "local_bg_B", "local_bg_G", "local_bg_R",
              "lightbox_circle_found"]
    for number in range(1, TOTAL_LANDMARKS + 1):
        header += [f"lm{number}_x", f"lm{number}_y"]
    for name in COLOUR_STANDARD_NAMES:
        header += [f"std_{name}_x", f"std_{name}_y",
                   f"std_{name}_B", f"std_{name}_G", f"std_{name}_R"]
    return header


def csv_row(result):
    scale_px = result["scale_bar"][2] if result.get("scale_bar") else ""
    px_per_mm = (scale_px / SCALE_BAR_MM) if scale_px else ""
    mm_per_px = (SCALE_BAR_MM / scale_px) if scale_px else ""
    local = result.get("ring") or {}

    row = [
        result.get("name", ""),
        result.get("label", "") or "",
        result.get("label_source", "") or "",
        "" if result.get("label_valid") is None else int(bool(result.get("label_valid"))),
        int(not result.get("skipped", False)),
        result.get("skip_reason", "") or "",
        result.get("colour_standard_source", "") or "",
        int(result.get("landmarks") is not None and not result.get("skipped")),
        f"{scale_px:.4f}" if scale_px else "",
        result.get("scale_bar_source", "") or "",
        f"{px_per_mm:.6f}" if px_per_mm else "",
        f"{mm_per_px:.6f}" if mm_per_px else "",
        result.get("background_brightness", ""),
        local.get("brightness", ""),
        local.get("bgr", ("", "", ""))[0],
        local.get("bgr", ("", "", ""))[1],
        local.get("bgr", ("", "", ""))[2],
        int(result.get("circle") is not None),
    ]

    landmarks = result.get("landmarks")
    for i in range(TOTAL_LANDMARKS):
        if landmarks is None:
            row += ["", ""]
        else:
            row += [f"{landmarks[i][0]:.3f}", f"{landmarks[i][1]:.3f}"]

    standard = result.get("colour_standard")
    colours = result.get("colour_standard_bgr")
    for i in range(len(COLOUR_STANDARD_NAMES)):
        if standard is None:
            row += ["", "", "", "", ""]
        else:
            bgr = colours[i] if colours else ("", "", "")
            row += [f"{standard[i][0]:.3f}", f"{standard[i][1]:.3f}", bgr[0], bgr[1], bgr[2]]

    return row


# =====================================================================
# NEW - PROCESSING ONE IMAGE
# =====================================================================

def process_frame(frame, name, options, remembered):
    """Run the whole pipeline on one image or video frame and return
    everything found, as a dictionary."""
    result = {"name": name,
              "follow": options.follow,
              "previous_colour_standard": remembered.get("last_colour_standard"),
              "landmark_history": remembered.get("landmark_history", []),
              "ring_display_width": 0 if options.no_ring_overlay else options.ring_display_width}

    circle = find_vignette_circle(frame)
    relevant_mask = get_relevant_mask(frame, circle)
    background_brightness = most_common_brightness(frame, relevant_mask)
    fish_contour, fish_box = find_fish(frame, background_brightness, relevant_mask,
                                       near_points=remembered.get("last_landmarks"))

    # If the previous frame's landmarks are available, also try a search
    # restricted to that neighbourhood. A blob found right where the fish
    # was is worth more than the biggest blob in the frame.
    if remembered.get("last_landmarks") is not None:
        nearby = detect_outline_near_points(frame, remembered["last_landmarks"],
                                            background_brightness)
        if nearby is not None:
            if fish_contour is None or cv2.contourArea(nearby) > 50:
                fish_contour = nearby
                fish_box = cv2.boundingRect(nearby)
                result["fish_source"] = "near-previous-frame"

    result["circle"] = circle
    result["background_brightness"] = int(background_brightness)
    result["fish_contour"] = fish_contour
    result["fish_box"] = fish_box

    fish_mask = np.zeros(frame.shape[:2], dtype=np.uint8)

    if fish_contour is not None:
        # Grow the outline to take in translucent fins - especially the
        # tail, which the main threshold usually loses on a white lightbox.
        if not options.no_faint_fins:
            fish_contour = recover_faint_fins(frame, background_brightness, relevant_mask,
                                              fish_contour, options.faint_threshold)
            result["fish_contour"] = fish_contour
            result["fish_box"] = cv2.boundingRect(fish_contour)
            fish_box = result["fish_box"]

        cv2.drawContours(fish_mask, [fish_contour], -1, 255, thickness=cv2.FILLED)
        result["ring"] = sample_ring_around_fish(frame, fish_contour, fish_box, relevant_mask)
        if result["ring"]:
            result["ring_mask"] = result["ring"]["ring_mask"]

        try:
            outline = resample_closed_curve(contour_to_points(fish_contour), CONTOUR_RESAMPLE_POINTS)
            result["outline"] = outline
            # The real detected fish edge, kept untouched for the lifetime
            # of this image. do_fill() always re-flows against this, never
            # against result["outline"] (which is overwritten for drawing
            # purposes whenever a point falls off the real edge).
            result["raw_outline"] = outline
            if options.manual_fixed or not AUTO_DETECT:
                # You're placing the primary points yourself (or this
                # animal's profile has no automatic detector), so don't guess.
                result["landmarks"] = None
            else:
                # Find the 7 anatomical points, then place the other 36
                # through EXACTLY the same function that SPACE uses. This
                # used to call place_all_landmarks() directly, which rides
                # the raw outline for every segment - so the automatic
                # first pass traced the dorsal and anal fin margins, and
                # then pressing SPACE silently produced a different (and
                # correct) result. One code path means what you see on
                # load is what you get after re-flowing.
                fixed = find_fixed_landmarks(outline, dorsal_side=options.dorsal)
                seven = [outline[i] for i in fixed]
                landmarks, curve = landmarks_from_seven_points(
                    seven, outline, follow=result.get("follow", "auto"))
                result["landmarks"] = landmarks
                result["fixed_indices"] = fixed
                result["outline"] = curve
        except Exception as error:  # a degenerate outline shouldn't kill the batch
            result["landmark_error"] = str(error)

    # The profile's default shape, placed for this frame, goes first in the
    # Previous list (G jumps straight to it). It's added to this frame's
    # copy only, never to the remembered history saved between frames.
    template_points = place_template(frame.shape, result.get("raw_outline"), circle)
    if template_points is not None:
        result["landmark_history"] = ([{"name": "default shape",
                                        "landmarks": template_points,
                                        "is_template": True}]
                                      + list(result["landmark_history"]))

    # --- scale bar ---
    if options.scale_px:
        result["scale_bar"] = (np.array([0.0, 0.0]), np.array([float(options.scale_px), 0.0]),
                               float(options.scale_px))
    elif remembered.get("last_scale_bar") is not None:
        # Carried over from an earlier frame of this video.
        result["scale_bar"] = remembered["last_scale_bar"]
        result["scale_bar_source"] = "carried-from-earlier-frame"
    elif options.scale_from_first and remembered.get("scale_bar") is not None:
        result["scale_bar"] = remembered["scale_bar"]
    else:
        result["scale_bar"] = detect_scale_bar(frame, exclude_mask=fish_mask)

    # --- colour standard ---
    # Detect the chart afresh in EVERY frame. The card is not fixed to the
    # rig - it moves between videos - so a position taught on one video is
    # wrong for the next, and tracking it would quietly sample the wrong
    # cells. detect_colour_standard() works from the patches' colours and
    # their positions relative to each other, so it doesn't care where in
    # the frame the card sits.
    detected = detect_colour_standard(frame, exclude_mask=fish_mask)
    if detected is not None:
        result["colour_standard"] = detected
        result["colour_standard_source"] = "auto-detected"
    else:
        # Only if automatic detection fails: fall back to a position you
        # set by hand earlier IN THIS SAME VIDEO, tracked into this frame.
        if remembered.get("last_colour_standard") is not None:
            # Carried over from an earlier frame of this same video, where
            # the camera really is static.
            result["colour_standard"] = [p.copy() for p
                                         in remembered["last_colour_standard"]]
            result["colour_standard_source"] = "carried-from-earlier-frame"
            taught = None
        else:
            taught = remembered.get("taught_standard")
        if taught is not None:
            result["colour_standard"] = track_colour_standard(frame, taught)
            result["colour_standard_source"] = "tracked-from-earlier-frame"
        elif options.colour_standard_from_first and remembered.get("colour_standard") is not None:
            result["colour_standard"] = remembered["colour_standard"]
            result["colour_standard_source"] = "reused"
        else:
            result["colour_standard"] = None
            result["colour_standard_source"] = None

    # --- tank label ---
    # Typed once per video and carried to its remaining frames. No OCR.
    confirmed = remembered.get("confirmed_label")
    if confirmed:
        result["label"] = confirmed
        result["label_valid"] = label_matches_known_prefix(confirmed)
        result["label_source"] = "typed"

    # --- scale bar fallback: some videos have no scale bar in frame, so
    # fall back to the known spacing between colour-standard squares.
    if result.get("scale_bar") is None and result.get("colour_standard") is not None:
        fallback = estimate_scale_from_colour_standard(frame, result["colour_standard"])
        if fallback is not None:
            a, b, equivalent_px, n_squares, spread = fallback
            result["scale_bar"] = (a, b, equivalent_px)
            result["scale_bar_source"] = "colour_standard_square_width"
            result["scale_squares_measured"] = n_squares
            result["scale_spread_percent"] = spread
    if "scale_bar_source" not in result:
        result["scale_bar_source"] = "scale_bar" if result.get("scale_bar") else None

    return result


def finalise(frame, result, remembered, options, out_folder=None):
    """Fill in derived values after any manual correction, and remember
    things that can be reused across a folder."""
    if result.get("colour_standard") is not None:
        result["colour_standard_bgr"] = sample_patch_colours(frame, result["colour_standard"])
        if options.colour_standard_from_first:
            remembered.setdefault("colour_standard", result["colour_standard"])
        # Whatever the 6 points ended up as after any dragging becomes the
        # taught standard for every later image, and is written to disk so
        # later runs on the same rig don't need teaching again.
        # Keep a hand-set chart position in memory for the REST OF THIS
        # VIDEO only (the main loop clears it when the video changes). It
        # is deliberately not written to disk: the card moves between
        # videos, so a saved position is a liability, not a shortcut.
        if remembered.get("taught_standard") is None \
                and result.get("colour_standard_source") in ("clicked", None) \
                and result.get("colour_standard") is not None:
            remembered["taught_standard"] = {
                "points": [[float(p[0]), float(p[1])] for p in result["colour_standard"]],
                "crop": None, "reference": None,
            }

    # Same teach-once idea for the label box, and remember a label you
    # typed by hand so later frames of the same video don't get re-OCR'd
    # into a different (possibly wrong) value.
    if result.get("label"):
        remembered["confirmed_label"] = result["label"]

    # Carry the scale bar and colour standard on to the next frame of this
    # video. This runs even when the frame was skipped, so marking a frame
    # unusable doesn't lose a scale bar you had just clicked - the next
    # frame starts with it already in place.
    if result.get("scale_bar") is not None:
        remembered["last_scale_bar"] = result["scale_bar"]
    if result.get("colour_standard") is not None:
        remembered["last_colour_standard"] = [np.asarray(p, float).copy()
                                              for p in result["colour_standard"]]

    # Remember the accepted landmarks: the next frame uses them to know
    # where to look for the fish, and they're kept in a list so you can
    # scroll back through earlier frames of this fish and reuse one.
    if result.get("landmarks") is not None and not result.get("skipped"):
        remembered["last_landmarks"] = result["landmarks"].copy()
        history = remembered.setdefault("landmark_history", [])
        history.append({"name": result.get("name", ""),
                        "landmarks": result["landmarks"].copy()})
        # A whole video's worth is plenty to scroll through.
        del history[:-40]
    if result.get("scale_bar") is not None and options.scale_from_first:
        remembered.setdefault("scale_bar", result["scale_bar"])


# =====================================================================
# NEW - INPUT GATHERING
# =====================================================================

def video_key_from_name(name):
    """Which video a frame came from, taken from its filename.

    extract_frames.py names frames LABEL_VIDEO_fNN_tSSSS.png, so the first
    two underscore-separated fields identify the video. Used to clear
    anything taught by hand - colour standard position, label box, typed
    label - when the run moves on to a different video, because none of
    those carry over: the card and label are repositioned each time."""
    stem = os.path.splitext(str(name))[0]
    parts = stem.split("_")
    if len(parts) >= 2:
        return "_".join(parts[:2])
    return stem


def natural_sort_key(text):
    """Sort image_2 before image_10, the way a person would."""
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", text)]


def gather_inputs(path, how_many_video_frames):
    """Return a list of (name, image) pairs from a folder of stills, a
    single image, or a video."""
    if os.path.isdir(path):
        files = []
        for extension in IMAGE_EXTENSIONS:
            files += glob.glob(os.path.join(path, "*" + extension))
            files += glob.glob(os.path.join(path, "*" + extension.upper()))
        files = sorted(set(files), key=lambda f: natural_sort_key(os.path.basename(f)))
        if not files:
            raise IOError(f"No images found in folder: {path}")
        return [(os.path.basename(f), cv2.imread(f)) for f in files]

    extension = os.path.splitext(path)[1].lower()
    if extension in VIDEO_EXTENSIONS:
        frames = get_sample_frames(path, how_many_video_frames)
        stem = os.path.splitext(os.path.basename(path))[0]
        return [(f"{stem}_frame{i:03d}", frame) for i, frame in enumerate(frames, start=1)]

    image = cv2.imread(path)
    if image is None:
        raise IOError(f"Could not read: {path}")
    return [(os.path.basename(path), image)]


# =====================================================================
# MAIN
# =====================================================================

def build_argument_parser():
    parser = argparse.ArgumentParser(
        description="Find the animal, place the landmarks, measure the scale bar "
                    "and read the color standard.")
    parser.add_argument("path", help="an image, a folder of images, or a video")
    parser.add_argument("--out", default="landmark_output", help="where to put the results")
    parser.add_argument("--dorsal", choices=["up", "down", "auto"], default="up",
                        help="which way the animal's back points in your photos (default: up)")
    parser.add_argument("--no-review", action="store_true",
                        help="skip the correction window and just save what was found")
    parser.add_argument("--scale-px", type=float, default=None,
                        help="scale bar length in pixels, if you already know it")
    parser.add_argument("--scale-from-first", action="store_true",
                        help="measure the scale bar once and reuse it (fixed camera)")
    parser.add_argument("--colour-standard-from-first", action="store_true",
                        help="locate the color standard once and reuse it (fixed camera)")
    parser.add_argument("--frames", type=int, default=10,
                        help="how many frames to sample if the input is a video")
    parser.add_argument("--ring-display-width", type=int, default=RING_DISPLAY_WIDTH,
                        help="thickness in pixels of the green background-ring outline "
                             "drawn on the debug image (default: %(default)s). Does not "
                             "affect the actual background color measurement.")
    parser.add_argument("--no-ring-overlay", action="store_true",
                        help="don't draw the green background ring on the debug image at all")
    parser.add_argument("--manual-fixed", action="store_true",
                        help="place the primary landmarks yourself on every image; the "
                             "semilandmarks are filled in automatically along the curve")
    parser.add_argument("--follow", choices=["auto", "outline", "spline"], default="auto",
                        help="what the semilandmarks follow between your primary points: the "
                             "detected outline, a smooth curve through your points, or "
                             "(default) the outline wherever it's trustworthy and the "
                             "smooth curve where it isn't")
    parser.add_argument("--faint-threshold", type=int, default=FAINT_FIN_THRESHOLD,
                        help="sensitivity for pulling translucent fins/tail into the outline; "
                             "lower = more sensitive (default: %(default)s)")
    parser.add_argument("--no-teach-standard", action="store_true",
                        help="don't save/reuse the color standard between images and runs; "
                             "re-detect it on every frame instead")
    parser.add_argument("--allow-incomplete", action="store_true",
                        help="let a frame be accepted with the color standard, "
                             "label, scale or landmarks still missing. Off by "
                             "default: an uncalibrated frame fails later in "
                             "Colormesh rather than here.")
    parser.add_argument("--redo", action="store_true",
                        help="ignore what's already in landmarks.csv and do every "
                             "image again (by default, images already recorded "
                             "there are skipped so you can resume)")
    parser.add_argument("--no-faint-fins", action="store_true",
                        help="don't try to recover translucent fins (use the solid body only)")
    parser.add_argument("--profile", default=None,
                        help="animal profile JSON (number and names of the primary "
                             "landmarks, semilandmarks between them, default shape). "
                             "Default: profiles/killifish.json, the 43-landmark scheme")
    parser.add_argument("--no-label", action="store_true",
                        help="don't require a typed/read label on each frame")
    parser.add_argument("--no-color-standard", "--no-colour-standard",
                        dest="no_color_standard", action="store_true",
                        help="don't require the color standard on each frame")
    parser.add_argument("--no-scale", action="store_true",
                        help="don't require the scale bar on each frame")
    return parser


def main():
    parser = build_argument_parser()
    options = parser.parse_args()
    if options.no_label:
        NOT_REQUIRED.add("label")
    if options.no_color_standard:
        NOT_REQUIRED.add("colour_standard")
    if options.no_scale:
        NOT_REQUIRED.add("scale")

    profile_path = options.profile or DEFAULT_PROFILE
    if os.path.exists(profile_path):
        try:
            apply_profile(profile_path)
        except (ValueError, KeyError, json.JSONDecodeError) as error:
            sys.exit(f"Could not use the animal profile {profile_path}: {error}")
    elif options.profile:
        sys.exit(f"Animal profile not found: {options.profile}")
    print(f"Animal profile: {PROFILE_NAME}  ({len(FIXED_LANDMARK_NAMES)} primary + "
          f"{sum(SEMILANDMARKS_PER_SEGMENT)} semilandmarks = {TOTAL_LANDMARKS})"
          + ("" if TEMPLATE is None else "  - default shape: G"))
    if not AUTO_DETECT:
        print("  Primary landmarks are placed by hand for this profile "
              "(click them, or G for the default shape).")

    print(f"Reading: {options.path}\n")
    inputs = gather_inputs(options.path, options.frames)
    if not inputs:
        print("Nothing to process.")
        return

    debug_folder = os.path.join(options.out, DEBUG_FOLDER)
    os.makedirs(debug_folder, exist_ok=True)

    csv_path = os.path.join(options.out, "landmarks.csv")

    # RESUME. Any image already recorded in landmarks.csv - whether it was
    # landmarked or marked unusable - is skipped, so you can stop partway
    # through a folder and pick up later, and so adding a replacement frame
    # to a folder doesn't mean redoing the other 24. Pass --redo to ignore
    # this and start the folder from scratch.
    already_done = {}
    if os.path.exists(csv_path) and not options.redo:
        try:
            with open(csv_path, newline="", encoding="utf-8") as handle:
                for existing in csv.DictReader(handle):
                    already_done[existing.get("image", "")] = existing
        except Exception as error:
            print(f"(couldn't read the existing {csv_path}: {error})")
            already_done = {}
    remembered = {}
    rows = []
    view_state = {}          # zoom/pan carried between images

    # Nothing taught by hand is loaded from disk at startup any more. The
    # colour standard and the tank label are repositioned for every video,
    # so a position saved on a previous run would be wrong here - it would
    # sample whatever now sits at those old coordinates without
    # complaining. Both are detected per frame instead, and a hand-set
    # position only carries to the rest of the video it was set on.

    if already_done:
        before = len(inputs)
        inputs = [(n, f) for (n, f) in inputs if n not in already_done]
        skipped_done = before - len(inputs)
        if skipped_done:
            print(f"{skipped_done} image(s) already done - skipping them. "
                  f"{len(inputs)} to do.")
            print("Pass --redo to start the folder over.\n")
        if not inputs:
            print("Everything in this folder is already done.")

    # Index-based rather than a for loop, so "Back" can step to the
    # previous frame instead of only ever moving forwards.
    index = 0
    while index < len(inputs):
        name, frame = inputs[index]
        position = index + 1
        if frame is None:
            print(f"--- {name} --- could not be read, skipping.")
            index += 1
            continue

        # New video? Anything set by hand on the previous video's frames
        # (chart position, label box, typed label) does not apply here.
        this_video = video_key_from_name(name)
        if remembered.get("current_video") != this_video:
            for key in ("taught_standard", "taught_label_box",
                        "confirmed_label", "colour_standard",
                        "last_scale_bar", "last_colour_standard",
                        "last_landmarks", "landmark_history"):
                remembered.pop(key, None)
            remembered["current_video"] = this_video

        print(f"--- {position}/{len(inputs)}: {name} ---")
        result = process_frame(frame, name, options, remembered)
        # For the header and progress bar in the review window.
        result["frame_position"] = position
        result["frame_total"] = len(inputs)
        result["video_key"] = this_video
        video_keys = [video_key_from_name(n) for n, _ in inputs]
        result["video_number"] = len(set(video_keys[:index + 1]))
        result["video_total"] = len(set(video_keys))
        frames_here = [k for k, v in enumerate(video_keys) if v == this_video]
        result["frame_in_video"] = frames_here.index(index) + 1
        result["frames_in_video"] = len(frames_here)

        print("  Lightbox circle: " + (
            "found " + str(tuple(int(v) for v in result["circle"]))
            if result.get("circle") else "not found (using whole frame)"))

        if result.get("fish_contour") is None:
            print("  No animal-like blob found."
                  + ("" if options.no_review else f" Press G for the default shape, or click the {len(FIXED_LANDMARK_NAMES)} primary landmarks."))
        else:
            print(f"  Animal bounding box: {result['fish_box']}")
            if result.get("ring"):
                print(f"  Local background right around the animal: "
                      f"brightness={result['ring']['brightness']}, BGR={result['ring']['bgr']}")
            if result.get("landmarks") is not None:
                print(f"  Placed {TOTAL_LANDMARKS} landmarks "
                      f"({len(FIXED_LANDMARK_NAMES)} fixed + {sum(SEMILANDMARKS_PER_SEGMENT)} semilandmarks).")
            elif options.manual_fixed:
                print(f"  Waiting for you to click the {len(FIXED_LANDMARK_NAMES)} fixed landmarks.")
            else:
                print(f"  Could not landmark this outline: {result.get('landmark_error')}")

        if result.get("scale_bar"):
            length = result["scale_bar"][2]
            source = result.get("scale_bar_source", "scale_bar")
            if source == "colour_standard_square_width":
                source_note = (f" (from {result.get('scale_squares_measured', '?')} "
                               f"color standard square widths, "
                               f"{result.get('scale_spread_percent', 0):.0f}% spread)")
            else:
                source_note = ""
            print(f"  Scale bar: {length:.1f} px for {SCALE_BAR_MM:.0f} mm{source_note} "
                  f"({length / SCALE_BAR_MM:.3f} px/mm)   <- 5th spreadsheet column")
        else:
            print("  Scale bar: not found (press S in the review window to click it)")

        if result.get("label"):
            flag = "" if result.get("label_valid") else "   <-- UNEXPECTED FORMAT, check it"
            print(f"  Label: {result['label']} ({result.get('label_source')}){flag}")
        elif result.get("label_box") is not None:
            print("  Label: could not read (press T in the review window to type it)")
        else:
            print("  Label: no box set (press L in the review window to draw one)")

        print("  Color standard: " + (
            f"6 patches ({result.get('colour_standard_source')})"
            if result.get("colour_standard")
            else "not found (press K in the review window to click all 6)"))

        if not options.no_review:
            try:
                start_mode = "review" if result.get("landmarks") is not None else "place"
                outcome = review_window(
                    frame, result, start_mode=start_mode, view_state=view_state,
                    options_allow_incomplete=options.allow_incomplete)
                if outcome == "quit":
                    print("\nStopped at your request. Results so far have been saved.")
                    break
                if outcome == "back":
                    if index == 0:
                        print("  Already at the first frame.")
                    else:
                        # Drop the previous frame's saved result so it comes
                        # up fresh, and go back to it.
                        index -= 1
                        previous_name = inputs[index][0]
                        rows = [r for r in rows if r[0] != previous_name]
                        already_done.pop(previous_name, None)
                        for folder, suffix in (("Landmarks", "_LM.TPS"),
                                               ("Landmarks_calib", "_calib_LM.TPS")):
                            stale = os.path.join(options.out, folder,
                                                 previous_name + suffix)
                            if os.path.exists(stale):
                                os.remove(stale)
                        print(f"  Going back to {previous_name}")
                    continue
            except cv2.error:
                print("  (no display available - continuing without the review window)")
                options.no_review = True

        finalise(frame, result, remembered, options, out_folder=options.out)

        stem = os.path.splitext(name)[0]
        if result.get("skipped"):
            print(f"  SKIPPED: {result.get('skip_reason', 'marked unusable')} "
                  f"- no TPS written, recorded in the CSV")
        if result.get("landmarks") is not None and not result.get("skipped"):
            # Colormesh's Automated_Colour_Extraction.R expects two files per
            # image, named exactly like this: the 43 body landmarks in
            # <image>_LM.TPS, and the 6 colour-standard points on their own
            # in <image>_calib_LM.TPS. They go in separate folders because
            # the R script lists a whole directory of *_LM.TPS to build the
            # consensus shape, and calibration files must not be in it.
            landmark_folder = os.path.join(options.out, "Landmarks")
            calib_folder = os.path.join(options.out, "Landmarks_calib")
            os.makedirs(landmark_folder, exist_ok=True)
            os.makedirs(calib_folder, exist_ok=True)

            mm_per_px = None
            if result.get("scale_bar"):
                mm_per_px = SCALE_BAR_MM / result["scale_bar"][2]

            write_tps(os.path.join(landmark_folder, f"{name}_LM.TPS"),
                      result["landmarks"], name, frame.shape[0], scale=mm_per_px)
            if result.get("colour_standard") is not None:
                write_tps(os.path.join(calib_folder, f"{name}_calib_LM.TPS"),
                          np.array(result["colour_standard"]), name,
                          frame.shape[0], include_image=False)
            write_points_txt(os.path.join(options.out, f"{stem}_points.txt"),
                             result["landmarks"], result.get("colour_standard"))

        cv2.imwrite(os.path.join(debug_folder, f"{stem}.png"), annotate(frame, result))
        rows.append(csv_row(result))
        index += 1

    if not options.no_review:
        cv2.destroyAllWindows()

    # Put the previously-done rows back alongside the new ones, so resuming
    # builds up one complete CSV rather than replacing it with just this
    # session's images.
    header = csv_header()
    kept = []
    new_names = {r[0] for r in rows}
    for image_name, existing in already_done.items():
        if image_name in new_names:
            continue                      # redone this session
        kept.append([existing.get(column, "") for column in header])
    all_rows = kept + rows
    all_rows.sort(key=lambda r: natural_sort_key(str(r[0])))

    with open(csv_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(all_rows)

    skipped = sum(1 for r in all_rows if len(r) > 4 and str(r[4]) == "0")
    print(f"\nWrote {len(all_rows)} row(s) to {csv_path}"
          + (f" ({len(rows)} new this session)" if kept else ""))
    if skipped:
        print(f"{skipped} frame(s) marked unusable and skipped - they are in the "
              f"CSV with usable=0 but have no TPS, so Colormesh will ignore them.")
    print(f"Annotated images are in '{debug_folder}' - red = the {len(FIXED_LANDMARK_NAMES)} fixed landmarks, "
          f"orange = the {sum(SEMILANDMARKS_PER_SEGMENT)} semilandmarks, cyan = color standard, magenta = scale bar, "
          f"green = sampled background ring, blue = lightbox edge.")


if __name__ == "__main__":
    main()