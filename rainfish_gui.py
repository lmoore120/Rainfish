r"""
fishcolour_gui.py - the whole pipeline in one window.

Run this and everything else follows from it: choose your videos, set the
options, and work down the steps. Nothing has to be run in the right order
by hand, and each step is checked before the next one unlocks.

    python fishcolour_gui.py

WHAT IT DOES
  Settings      your rig: scale bar, colour card, landmark scheme, sampling
  1 Videos      choose a folder of videos (or pick individual files)
  2 Extract     pull sharp frames, with video date, resolution and codec
  3 Review      look over the frames, drop or replace bad ones
  4 Landmark    place the 43 landmarks on each frame
  5 Checks      facing, landmark quality, colour standard, scale
  6 Colour      Colormesh warping and sampling, then CIE L*a*b*
  7 Results     rates, capacity, graphs, and colour maps per fish

HOW IT IS PUT TOGETHER
  Each step runs the existing command-line script as a separate process and
  streams its output into the log pane at the bottom. That is deliberate:
  the landmarking and frame-review windows are OpenCV windows with their
  own event loop, which fights with this window's event loop if they share
  a process. Running them separately also means the scripts themselves stay
  exactly as they are, already tested, rather than being rewritten.

  The R scripts have their paths written into the top of the file. Rather
  than ask you to edit them, this writes configured copies into
  <project>\_generated\ and runs those. Your originals are never changed.

WHAT YOU NEED
  Python packages:  python -m pip install -r requirements.txt
  R, with Colormesh, geomorph, Morpho, imager, dplyr, abind
  (Steps 1-5 work without R. Step 6 onward needs it.)
"""

import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

HERE = os.path.dirname(os.path.abspath(__file__))

try:
    import fishcolour_config as config_module
except ImportError:
    config_module = None


# =====================================================================
# Finding the other scripts and the tools they need
# =====================================================================

PYTHON_STEPS = {
    "extract": "extract_frames.py",
    "review": "review_frames.py",
    "landmark": "find_fish_and_landmarks.py",
    "colormaps": "render_colormaps.py",
    "sheets": "frame_sheets.py",
}

R_STEPS = {
    "colormesh": "Colormesh_extraction.R",
    "cie": "CIE_conversion.R",
    "rates": "plasticity_rates.R",
}


def script_path(name):
    return os.path.join(HERE, name)


def find_rscript():
    """Rscript, from the PATH or the usual Windows install folders."""
    found = shutil.which("Rscript")
    if found:
        return found
    for base in (r"C:\Program Files\R", r"C:\Program Files (x86)\R"):
        if os.path.isdir(base):
            # Newest version first, so an old R 3.x doesn't win.
            for version in sorted(os.listdir(base), reverse=True):
                candidate = os.path.join(base, version, "bin", "Rscript.exe")
                if os.path.exists(candidate):
                    return candidate
    return None


def missing_python_packages():
    missing = []
    for module, package in (("cv2", "opencv-python"), ("numpy", "numpy")):
        try:
            __import__(module)
        except ImportError:
            missing.append(package)
    return missing


# =====================================================================
# Running a step without freezing the window
# =====================================================================

class StepRunner:
    """Runs one script in its own process and reports back.

    Output is read on a background thread and handed to the window through
    a queue, so the window keeps redrawing while a long step runs. Without
    this, everything would appear frozen for the whole of a Colormesh run.
    """

    PROGRESS = re.compile(r"[\[(]?(\d+)\s*/\s*(\d+)[\])]?")

    def __init__(self, on_output, on_progress, on_finished):
        self.on_output = on_output
        self.on_progress = on_progress
        self.on_finished = on_finished
        self.messages = queue.Queue()
        self.process = None
        self.running = False

    def start(self, command, working_directory=None, label=""):
        if self.running:
            return False
        self.running = True
        self.label = label
        thread = threading.Thread(target=self._run, args=(command, working_directory),
                                  daemon=True)
        thread.start()
        return True

    def _run(self, command, working_directory):
        started = time.time()
        try:
            self.messages.put(("output", "$ " + " ".join(
                f'"{c}"' if " " in str(c) else str(c) for c in command) + "\n"))
            # Line-buffered, stderr folded into stdout, so the log reads in
            # the order things actually happened.
            self.process = subprocess.Popen(
                command, cwd=working_directory, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True, bufsize=1,
                encoding="utf-8", errors="replace",
                creationflags=(subprocess.CREATE_NO_WINDOW
                               if os.name == "nt" and hasattr(subprocess, "CREATE_NO_WINDOW")
                               else 0))
            for line in self.process.stdout:
                self.messages.put(("output", line))
                match = self.PROGRESS.search(line)
                if match:
                    done, total = int(match.group(1)), int(match.group(2))
                    if 0 < done <= total and total > 1:
                        self.messages.put(("progress", (done, total)))
            code = self.process.wait()
        except FileNotFoundError as error:
            self.messages.put(("output", f"\nCould not start it: {error}\n"))
            code = -1
        except Exception as error:                      # noqa: BLE001
            self.messages.put(("output", f"\nSomething went wrong: {error}\n"))
            code = -1
        finally:
            self.running = False
            self.process = None
        self.messages.put(("finished", (code, time.time() - started)))

    def stop(self):
        if self.process is not None:
            try:
                self.process.terminate()
                self.messages.put(("output", "\nStopped.\n"))
            except Exception:                           # noqa: BLE001
                pass

    def pump(self):
        """Called by the window a few times a second to collect messages."""
        try:
            while True:
                kind, payload = self.messages.get_nowait()
                if kind == "output":
                    self.on_output(payload)
                elif kind == "progress":
                    self.on_progress(*payload)
                elif kind == "finished":
                    self.on_finished(*payload)
        except queue.Empty:
            pass


# =====================================================================
# Checks between steps
# =====================================================================

def count_files(folder, *endings):
    if not os.path.isdir(folder):
        return 0
    return sum(1 for f in os.listdir(folder)
               if f.lower().endswith(tuple(e.lower() for e in endings)))


def read_csv_rows(path):
    import csv
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


class ProjectChecks:
    """Looks at what is actually on disk and says what state the project is
    in. Every step asks this before it runs, so a step cannot quietly run on
    missing or half-finished input."""

    VIDEO_ENDINGS = (".mp4", ".mov", ".avi", ".mkv", ".m4v", ".mpg", ".mpeg", ".wmv")

    def __init__(self, project):
        self.project = project

    def path(self, *parts):
        return os.path.join(self.project, *parts)

    def videos(self):
        folder = self.path("videos")
        if not os.path.isdir(folder):
            return []
        return sorted(f for f in os.listdir(folder)
                      if f.lower().endswith(self.VIDEO_ENDINGS))

    def frames_state(self):
        folder = self.path("frames")
        manifest = os.path.join(folder, "frames_manifest.csv")
        rows = read_csv_rows(manifest)
        on_disk = count_files(folder, ".png", ".jpg", ".jpeg", ".tif", ".tiff")
        videos = {r.get("video", "") for r in rows}
        return {"folder": folder, "manifest": manifest, "rows": len(rows),
                "on_disk": on_disk, "videos": len(videos),
                "capacity_column": bool(rows) and "capacity_frame" in rows[0]}

    def landmarks_state(self):
        folder = self.path("landmarks")
        rows = read_csv_rows(os.path.join(folder, "landmarks.csv"))
        usable = [r for r in rows if str(r.get("usable", "1")) == "1"]
        no_id = [r for r in usable if not r.get("fish_id")]
        no_card = [r for r in usable if not r.get("colour_standard_source")]
        crossing = [r for r in usable if str(r.get("shape_self_intersects", "0")) == "1"]
        return {"folder": folder,
                "tps": count_files(os.path.join(folder, "Landmarks"), ".TPS"),
                "calib": count_files(os.path.join(folder, "Landmarks_calib"), ".TPS"),
                "rows": len(rows), "usable": len(usable), "skipped": len(rows) - len(usable),
                "no_id": len(no_id), "no_card": len(no_card), "crossing": len(crossing)}

    def colour_state(self):
        colormaps = self.path("colormaps")
        colormap_file = os.path.join(colormaps, "colormap_calib.csv")
        lab = [f for f in (os.listdir(colormaps) if os.path.isdir(colormaps) else [])
               if f.startswith("LAB_average")]
        return {"folder": colormaps,
                "colormap": colormap_file if os.path.exists(colormap_file) else None,
                "consensus": os.path.exists(os.path.join(colormaps, "consensus_shape.rds")),
                "per_frame": count_files(os.path.join(colormaps, "per_frame"), ".csv"),
                "lab": os.path.join(colormaps, lab[0]) if lab else None}

    def results_state(self):
        folder = self.path("results")
        by_video = os.path.join(folder, "plasticity_by_video.csv")
        return {"folder": folder,
                "by_video": by_video if os.path.exists(by_video) else None,
                "rows": len(read_csv_rows(by_video))}

    def facing_report(self):
        """Which way each fish faces, read from the landmark files.

        Mixed facing is the one thing that must be known BEFORE Colormesh
        runs: averaging a fish with its own mirror image collapses the
        reference shape and scrambles every colour measurement. Colormesh
        corrects this itself, but it is worth seeing the numbers."""
        folder = os.path.join(self.path("landmarks"), "Landmarks")
        if not os.path.isdir(folder):
            return None
        right = left = unreadable = 0
        for name in os.listdir(folder):
            if not name.upper().endswith(".TPS"):
                continue
            points = []
            try:
                with open(os.path.join(folder, name), encoding="utf-8") as handle:
                    for line in handle:
                        if "=" in line:
                            continue
                        bits = line.split()
                        if len(bits) >= 2:
                            points.append((float(bits[0]), float(bits[1])))
            except Exception:                           # noqa: BLE001
                unreadable += 1
                continue
            if len(points) < 5:
                unreadable += 1
                continue
            snout = points[0][0]
            tail = (points[3][0] + points[4][0]) / 2
            if snout > tail:
                right += 1
            else:
                left += 1
        return {"right": right, "left": left, "unreadable": unreadable}


# =====================================================================
# Writing configured copies of the R scripts
# =====================================================================

def forward(path):
    """R wants forward slashes, even on Windows."""
    return os.path.abspath(path).replace("\\", "/")


def write_configured_r(project, settings, generated_folder):
    """Copy each R script with its paths and settings filled in.

    Every substitution is checked: if a line this expects is not found, it
    says so rather than running a script still pointing at someone else's
    folders."""
    os.makedirs(generated_folder, exist_ok=True)
    done, problems = [], []

    def configure(name, replacements):
        source = script_path(name)
        if not os.path.exists(source):
            problems.append(f"{name} is missing from {HERE}")
            return
        with open(source, encoding="utf-8") as handle:
            text = handle.read()
        for pattern, replacement in replacements:
            new_text, count = re.subn(pattern, replacement.replace("\\", "\\\\"),
                                      text, count=1, flags=re.M)
            if count == 0:
                problems.append(f"{name}: could not find the line matching "
                                f"{pattern!r} to set. The script may have been edited.")
            text = new_text
        target = os.path.join(generated_folder, name)
        with open(target, "w", encoding="utf-8") as handle:
            handle.write(text)
        done.append(target)

    frames = forward(os.path.join(project, "frames")) + "/"
    landmarks = forward(os.path.join(project, "landmarks"))
    colormaps = forward(os.path.join(project, "colormaps")) + "/"
    warped = forward(os.path.join(project, "warped")) + "/"
    results = forward(os.path.join(project, "results")) + "/"
    manifest = forward(os.path.join(project, "frames", "frames_manifest.csv"))
    patches = forward(os.path.join(project, "RGB_calib_val.csv"))

    configure(R_STEPS["colormesh"], [
        (r'^image_dir\s*<-.*$', f'image_dir <- "{frames}"'),
        (r'^landmark_dir\s*<-.*$', f'landmark_dir <- "{landmarks}/Landmarks/"'),
        (r'^calib_dir\s*<-.*$', f'calib_dir <- "{landmarks}/Landmarks_calib/"'),
        (r'^warped_dir\s*<-.*$', f'warped_dir <- "{warped}"'),
        (r'^output_dir\s*<-.*$', f'output_dir <- "{colormaps}"'),
        (r'^calib_values_file\s*<-.*$', f'calib_values_file <- "{patches}"'),
        (r'^num_passes\s*<-.*$', f'num_passes <- {settings["num_passes"]}'),
    ])
    configure(R_STEPS["cie"], [
        (r'^colormap_file\s*<-.*$',
         f'colormap_file <- "{colormaps}colormap_calib.csv"'),
        (r'^manifest_file\s*<-.*$', f'manifest_file <- "{manifest}"'),
        (r'^output_dir\s*<-.*$', f'output_dir <- "{colormaps}"'),
    ])

    background = settings.get("background") or "white"
    configure(R_STEPS["rates"], [
        (r'^lab_file\s*<-.*$',
         f'lab_file <- "{colormaps}LAB_average_{background}.csv"'),
        (r'^manifest_file\s*<-.*$', f'manifest_file <- "{manifest}"'),
        (r'^landmarks_csv\s*<-.*$', f'landmarks_csv <- "{landmarks}/landmarks.csv"'),
        (r'^output_dir\s*<-.*$', f'output_dir <- "{results}"'),
    ])
    return done, problems


def write_patch_values(project, reference_rgb, names):
    """RGB_calib_val.csv, the known colours of the card, for Colormesh."""
    import csv
    path = os.path.join(project, "RGB_calib_val.csv")
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["patch", "R", "G", "B"])
        for name in names:
            rgb = reference_rgb.get(name)
            if rgb:
                writer.writerow([name] + list(rgb))
    return path


# =====================================================================
# The window
# =====================================================================

class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Fish colour change - pipeline")
        self.geometry("1100x800")
        self.minsize(900, 650)

        self.project = tk.StringVar(value="")
        self.rscript = find_rscript()
        self.runner = StepRunner(self.append_log, self.set_progress, self.step_finished)
        self.current_step = None
        self._after_step = None
        self.settings_widgets = {}

        self._build()
        self.after(120, self._pump)
        self._check_tools()

    # ---------------------------------------------------------- layout
    def _build(self):
        top = ttk.Frame(self, padding=8)
        top.pack(fill="x")
        ttk.Label(top, text="Project folder:").pack(side="left")
        ttk.Entry(top, textvariable=self.project).pack(side="left", fill="x",
                                                       expand=True, padx=6)
        ttk.Button(top, text="Choose...", command=self.choose_project).pack(side="left")
        ttk.Button(top, text="New...", command=self.new_project).pack(side="left", padx=4)

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=8)
        self._build_settings_tab()
        self._build_steps_tab()

        bar = ttk.Frame(self, padding=(8, 4))
        bar.pack(fill="x")
        self.status = ttk.Label(bar, text="Choose a project folder to begin.")
        self.status.pack(side="left")
        self.progress = ttk.Progressbar(bar, mode="determinate", length=260)
        self.progress.pack(side="right")
        self.stop_button = ttk.Button(bar, text="Stop", command=self.runner.stop,
                                      state="disabled")
        self.stop_button.pack(side="right", padx=8)

        log_frame = ttk.LabelFrame(self, text="What is happening", padding=4)
        log_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.log = tk.Text(log_frame, height=14, wrap="word", bg="#1e1e1e",
                           fg="#dcdcdc", insertbackground="#dcdcdc")
        scroll = ttk.Scrollbar(log_frame, command=self.log.yview)
        self.log.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.log.pack(fill="both", expand=True)
        self.log.tag_configure("good", foreground="#7ec77e")
        self.log.tag_configure("bad", foreground="#ff8a7a")
        self.log.tag_configure("note", foreground="#f0c674")

    def _build_settings_tab(self):
        tab = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(tab, text="Settings")

        ttk.Label(tab, text="These describe your equipment and your animal. "
                            "They are saved in the project as fishcolour.yaml.",
                  wraplength=900).grid(row=0, column=0, columnspan=4, sticky="w",
                                       pady=(0, 10))

        fields = [
            ("Sampling", None, None, None),
            ("Frames per video", "frames_per_video", "10",
             "evenly spaced across the window below"),
            ("Window (seconds)", "window_seconds", "120",
             "the stretch those frames are spread across"),
            ("Capacity frame at (seconds)", "capacity_frame_seconds", "300",
             "one extra frame at the end of the trial; 0 for none"),
            ("Equipment", None, None, None),
            ("Scale bar length (mm)", "scale_bar_mm", "11.5",
             "the real length of the scale bar in shot"),
            ("Colour patch width (mm)", "colour_standard_square_mm", "11.5",
             "the real width of one printed square on the card"),
            ("Background", "background", "white",
             "white or black - used to name the output files"),
            ("Analysis", None, None, None),
            ("Colormesh passes", "num_passes", "7",
             "sampling density; 7 gave about 1,500 points here"),
            ("Frames averaged for the endpoint", "z_inf_end_frames", "2",
             "1 reproduces the original protocol exactly"),
        ]
        row = 1
        for label, key, default, hint in fields:
            if key is None:
                ttk.Separator(tab, orient="horizontal").grid(
                    row=row, column=0, columnspan=4, sticky="ew", pady=(12, 4))
                row += 1
                ttk.Label(tab, text=label, font=("", 10, "bold")).grid(
                    row=row, column=0, sticky="w")
                row += 1
                continue
            ttk.Label(tab, text=label + ":").grid(row=row, column=0, sticky="w", pady=2)
            variable = tk.StringVar(value=default)
            ttk.Entry(tab, textvariable=variable, width=14).grid(
                row=row, column=1, sticky="w", padx=6)
            ttk.Label(tab, text=hint, foreground="#666").grid(
                row=row, column=2, sticky="w")
            self.settings_widgets[key] = variable
            row += 1

        ttk.Separator(tab, orient="horizontal").grid(row=row, column=0, columnspan=4,
                                                     sticky="ew", pady=10)
        row += 1
        buttons = ttk.Frame(tab)
        buttons.grid(row=row, column=0, columnspan=4, sticky="w")
        ttk.Button(buttons, text="Save settings",
                   command=self.save_settings).pack(side="left")
        ttk.Button(buttons, text="Reload from project",
                   command=self.load_settings).pack(side="left", padx=6)
        tab.columnconfigure(2, weight=1)

    def _build_steps_tab(self):
        tab = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(tab, text="Steps")
        self.step_rows = {}

        steps = [
            ("videos", "1. Videos", "Put your videos in the project's videos folder",
             self.step_videos, "Check"),
            ("extract", "2. Extract frames",
             "Pull sharp frames, with each video's date, size and length",
             self.step_extract, "Run"),
            ("review", "3. Review frames",
             "Look over every fish's frames; drop or replace bad ones",
             self.step_review, "Open"),
            ("landmark", "4. Landmarking",
             "Place the 43 landmarks, type the fish ID, check the colour card",
             self.step_landmark, "Open"),
            ("checks", "5. Checks",
             "Facing, landmark quality, colour standard, scale",
             self.step_checks, "Check"),
            ("colour", "6. Extract colour",
             "Colormesh warping and sampling, then CIE L*a*b*",
             self.step_colour, "Run"),
            ("results", "7. Results",
             "Rates, capacity, graphs and colour maps",
             self.step_results, "Run"),
        ]
        for index, (key, title, description, command, verb) in enumerate(steps):
            frame = ttk.Frame(tab, padding=(0, 6))
            frame.grid(row=index, column=0, sticky="ew")
            tab.columnconfigure(0, weight=1)
            frame.columnconfigure(1, weight=1)

            state = ttk.Label(frame, text="\u25cb", width=3, font=("", 14))
            state.grid(row=0, column=0, rowspan=2)
            ttk.Label(frame, text=title, font=("", 11, "bold")).grid(
                row=0, column=1, sticky="w")
            ttk.Label(frame, text=description, foreground="#666").grid(
                row=1, column=1, sticky="w")
            button = ttk.Button(frame, text=verb, width=10,
                                command=command)
            button.grid(row=0, column=2, rowspan=2, padx=6)
            detail = ttk.Label(frame, text="", foreground="#444")
            detail.grid(row=2, column=1, columnspan=2, sticky="w")
            self.step_rows[key] = {"state": state, "button": button, "detail": detail}

        ttk.Separator(tab, orient="horizontal").grid(row=len(steps), column=0,
                                                     sticky="ew", pady=10)
        bottom = ttk.Frame(tab)
        bottom.grid(row=len(steps) + 1, column=0, sticky="w")
        ttk.Button(bottom, text="Refresh all",
                   command=self.refresh_steps).pack(side="left")
        ttk.Button(bottom, text="Open project folder",
                   command=self.open_project_folder).pack(side="left", padx=6)

    # ------------------------------------------------------- utilities
    def append_log(self, text, tag=None):
        self.log.insert("end", text, tag or ())
        self.log.see("end")

    def set_progress(self, done, total):
        self.progress["maximum"] = total
        self.progress["value"] = done
        percent = 100.0 * done / total
        self.status.configure(text=f"{self.current_step or 'Working'}: "
                                   f"{done} of {total} ({percent:.0f}%)")

    def step_finished(self, code, seconds):
        self.stop_button.configure(state="disabled")
        follow_on = getattr(self, "_after_step", None)
        self._after_step = None
        if code == 0:
            self.progress["value"] = self.progress["maximum"] or 1
            self.append_log(f"\n100% complete - finished in {seconds / 60:.1f} min.\n",
                            "good")
            self.status.configure(text=f"{self.current_step}: finished.")
        else:
            self.append_log(f"\nStopped with error code {code} after "
                            f"{seconds / 60:.1f} min. Read the messages above.\n", "bad")
            self.status.configure(text=f"{self.current_step}: did not finish.")
            # A later stage must not run on the back of a failed one: the
            # CIE conversion on a half-finished Colormesh run would quietly
            # produce colours for only some of the fish.
            follow_on = None
        self.current_step = None
        self.refresh_steps()
        if follow_on is not None:
            self.after(400, follow_on)

    def _pump(self):
        self.runner.pump()
        self.after(120, self._pump)

    def _check_tools(self):
        missing = missing_python_packages()
        if missing:
            self.append_log(f"Missing Python package(s): {', '.join(missing)}.\n"
                            f"Install with:  python -m pip install "
                            f"{' '.join(missing)}\n", "bad")
        if self.rscript is None:
            self.append_log("R was not found. Steps 1-5 work without it; step 6 "
                            "onward needs R with the Colormesh package.\n", "note")
        else:
            self.append_log(f"Using R at {self.rscript}\n")

    def require_project(self):
        if not self.project.get() or not os.path.isdir(self.project.get()):
            messagebox.showwarning("No project",
                                   "Choose a project folder first.")
            return False
        return True

    def run_step(self, label, command, working_directory=None):
        if self.runner.running:
            messagebox.showinfo("Busy", "Something is already running. Wait for it "
                                        "to finish, or press Stop.")
            return
        self.current_step = label
        self.progress["value"] = 0
        self.progress["maximum"] = 100
        self.status.configure(text=f"{label}: starting...")
        self.append_log(f"\n=== {label} ===\n", "note")
        self.stop_button.configure(state="normal")
        self.runner.start(command, working_directory, label)

    # -------------------------------------------------------- project
    def choose_project(self):
        folder = filedialog.askdirectory(title="Choose the project folder")
        if folder:
            self.project.set(folder)
            self.load_settings()
            self.refresh_steps()

    def new_project(self):
        parent = filedialog.askdirectory(title="Where should the project folder go?")
        if not parent:
            return
        name = tk.simpledialog.askstring("New project",
                                         "Name for this project folder:",
                                         parent=self)
        if not name:
            return
        folder = os.path.join(parent, name)
        for sub in ("videos", "frames", "landmarks", "colormaps", "warped", "results"):
            os.makedirs(os.path.join(folder, sub), exist_ok=True)
        self.project.set(folder)
        self.save_settings()
        self.append_log(f"Made {folder} with its folders. Put your videos in "
                        f"{os.path.join(folder, 'videos')}.\n", "good")
        self.refresh_steps()

    def open_project_folder(self):
        if not self.require_project():
            return
        folder = self.project.get()
        if os.name == "nt":
            os.startfile(folder)                         # noqa: S606
        elif sys.platform == "darwin":
            subprocess.Popen(["open", folder])
        else:
            subprocess.Popen(["xdg-open", folder])

    # ------------------------------------------------------- settings
    def settings_dict(self):
        out = {}
        for key, variable in self.settings_widgets.items():
            value = variable.get().strip()
            if key == "background":
                out[key] = value or "white"
                continue
            try:
                out[key] = float(value) if "." in value else int(value)
            except ValueError:
                out[key] = value
        return out

    def save_settings(self):
        if not self.require_project():
            return
        values = self.settings_dict()
        config = {
            "sampling": {
                "frames_per_video": int(values.get("frames_per_video", 10)),
                "window_seconds": float(values.get("window_seconds", 120)),
                "capacity_frame_seconds": float(values.get("capacity_frame_seconds", 300)),
            },
            "scale": {
                "scale_bar_mm": float(values.get("scale_bar_mm", 11.5)),
                "colour_standard_square_mm":
                    float(values.get("colour_standard_square_mm", 11.5)),
            },
            "analysis": {
                "num_passes": int(values.get("num_passes", 7)),
                "z_inf_end_frames": int(values.get("z_inf_end_frames", 2)),
            },
            "background": values.get("background", "white"),
        }
        path = os.path.join(self.project.get(), "fishcolour.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(config, handle, indent=2)

        if config_module is not None:
            reference = config_module.DEFAULTS["colour_standard"]
            write_patch_values(self.project.get(), reference["reference_rgb"],
                               reference["names"])
        self.append_log(f"Settings saved to {path}\n", "good")

    def load_settings(self):
        path = os.path.join(self.project.get(), "fishcolour.json")
        if not os.path.exists(path):
            return
        with open(path, encoding="utf-8") as handle:
            config = json.load(handle)
        flat = {}
        flat.update(config.get("sampling", {}))
        flat.update(config.get("scale", {}))
        flat.update(config.get("analysis", {}))
        flat["background"] = config.get("background", "white")
        for key, variable in self.settings_widgets.items():
            if key in flat:
                value = flat[key]
                variable.set(str(int(value)) if isinstance(value, float)
                             and value.is_integer() else str(value))
        self.append_log(f"Settings loaded from {path}\n")

    # ---------------------------------------------------------- steps
    def mark(self, key, symbol, detail="", colour="#444"):
        row = self.step_rows[key]
        row["state"].configure(text=symbol)
        row["detail"].configure(text=detail, foreground=colour)

    def refresh_steps(self):
        if not self.project.get() or not os.path.isdir(self.project.get()):
            for key in self.step_rows:
                self.mark(key, "\u25cb", "")
            return
        checks = ProjectChecks(self.project.get())

        videos = checks.videos()
        self.mark("videos", "\u2714" if videos else "\u25cb",
                  f"{len(videos)} video(s) in the videos folder" if videos
                  else "no videos yet - put them in the project's videos folder",
                  "#2a7" if videos else "#a60")

        frames = checks.frames_state()
        if frames["rows"]:
            note = (f"{frames['rows']} frames from {frames['videos']} video(s)"
                    f"{'' if frames['capacity_column'] else '  (no capacity frame)'}")
            if frames["on_disk"] < frames["rows"]:
                note += f"  - WARNING: only {frames['on_disk']} image files on disk"
            self.mark("extract", "\u2714", note, "#2a7")
        else:
            self.mark("extract", "\u25cb", "not extracted yet")

        reviewed = os.path.join(frames["folder"], "reviewed_videos.txt")
        if os.path.exists(reviewed):
            with open(reviewed, encoding="utf-8") as handle:
                done = len([l for l in handle if l.strip()])
            self.mark("review", "\u2714" if done >= frames["videos"] else "\u25d0",
                      f"{done} of {frames['videos']} video(s) reviewed", "#2a7")
        else:
            self.mark("review", "\u25cb",
                      "optional, but catches bad frames before landmarking")

        marks = checks.landmarks_state()
        if marks["rows"]:
            note = (f"{marks['tps']} landmarked, {marks['skipped']} skipped, "
                    f"of {frames['rows']} frames")
            warnings = []
            if marks["no_card"]:
                warnings.append(f"{marks['no_card']} without a colour standard")
            if marks["crossing"]:
                warnings.append(f"{marks['crossing']} with a crossed outline")
            if warnings:
                note += "  - " + "; ".join(warnings)
            complete = frames["rows"] and marks["rows"] >= frames["rows"]
            self.mark("landmark", "\u2714" if complete and not warnings else "\u25d0",
                      note, "#2a7" if complete and not warnings else "#a60")
        else:
            self.mark("landmark", "\u25cb", "not started")

        colour = checks.colour_state()
        if colour["lab"]:
            self.mark("colour", "\u2714",
                      f"colour extracted ({colour['per_frame']} frames measured)", "#2a7")
        elif colour["per_frame"]:
            self.mark("colour", "\u25d0",
                      f"{colour['per_frame']} frames measured so far", "#a60")
        else:
            self.mark("colour", "\u25cb", "needs R and the Colormesh package")

        results = checks.results_state()
        self.mark("results", "\u2714" if results["by_video"] else "\u25cb",
                  f"{results['rows']} fish in the results" if results["by_video"]
                  else "not run yet", "#2a7" if results["by_video"] else "#444")

    def step_videos(self):
        if not self.require_project():
            return
        folder = os.path.join(self.project.get(), "videos")
        os.makedirs(folder, exist_ok=True)
        videos = ProjectChecks(self.project.get()).videos()
        if videos:
            self.append_log(f"{len(videos)} video(s) in {folder}:\n", "good")
            for name in videos[:12]:
                self.append_log(f"   {name}\n")
            if len(videos) > 12:
                self.append_log(f"   ... and {len(videos) - 12} more\n")
        else:
            self.append_log(f"No videos in {folder}.\n", "bad")
            if messagebox.askyesno("Add videos",
                                   "No videos found. Choose video files to copy in?"):
                files = filedialog.askopenfilenames(
                    title="Choose video files",
                    filetypes=[("Videos", "*.mp4 *.mov *.avi *.mkv *.m4v"),
                               ("All files", "*.*")])
                for path in files:
                    shutil.copy2(path, folder)
                    self.append_log(f"   copied {os.path.basename(path)}\n")
        self.refresh_steps()

    def step_extract(self):
        if not self.require_project():
            return
        videos = ProjectChecks(self.project.get()).videos()
        if not videos:
            messagebox.showwarning("No videos", "Put videos in the project's videos "
                                                "folder first (step 1).")
            return
        self.save_settings()
        values = self.settings_dict()
        project = self.project.get()
        command = [sys.executable, script_path(PYTHON_STEPS["extract"]),
                   os.path.join(project, "videos"),
                   "--out", os.path.join(project, "frames"),
                   "--frames", str(int(values.get("frames_per_video", 10))),
                   "--seconds", str(float(values.get("window_seconds", 120)))]
        if "capacity_frame_seconds" in values:
            command += ["--capacity-at", str(float(values["capacity_frame_seconds"]))]
        self.run_step("Extracting frames", command)

    def step_review(self):
        if not self.require_project():
            return
        project = self.project.get()
        if not ProjectChecks(project).frames_state()["rows"]:
            messagebox.showwarning("No frames", "Extract frames first (step 2).")
            return
        self.append_log("The review window is opening. Y keeps a fish, N rejects it, "
                        "Q saves and closes. It can be closed and reopened at any "
                        "time.\n", "note")
        self.run_step("Reviewing frames",
                      [sys.executable, script_path(PYTHON_STEPS["review"]),
                       os.path.join(project, "frames"),
                       "--videos", os.path.join(project, "videos")])

    def step_landmark(self):
        if not self.require_project():
            return
        project = self.project.get()
        if not ProjectChecks(project).frames_state()["rows"]:
            messagebox.showwarning("No frames", "Extract frames first (step 2).")
            return
        self.append_log("The landmarking window is opening. Press T to type the fish "
                        "ID, click the 7 points, SPACE to fill in the rest, ENTER for "
                        "the next frame, Q to save and close. It picks up where you "
                        "left off.\n", "note")
        self.run_step("Landmarking",
                      [sys.executable, script_path(PYTHON_STEPS["landmark"]),
                       os.path.join(project, "frames"),
                       "--out", os.path.join(project, "landmarks")])

    def step_checks(self):
        if not self.require_project():
            return
        checks = ProjectChecks(self.project.get())
        frames = checks.frames_state()
        marks = checks.landmarks_state()
        self.append_log("\n=== Checks ===\n", "note")

        def line(ok, text):
            self.append_log(("  OK   " if ok else "  !    ") + text + "\n",
                            "good" if ok else "bad")

        line(frames["rows"] > 0, f"{frames['rows']} frames recorded in the manifest")
        line(frames["on_disk"] >= frames["rows"],
             f"{frames['on_disk']} image files on disk")
        line(frames["capacity_column"],
             "capacity frame recorded" if frames["capacity_column"]
             else "no capacity_frame column - frames came from an older version")
        line(marks["tps"] > 0, f"{marks['tps']} frames landmarked "
                               f"({marks['skipped']} skipped as unusable)")
        line(marks["calib"] == marks["tps"],
             f"{marks['calib']} colour-standard files (should equal the landmark count)")
        line(marks["no_card"] == 0,
             f"{marks['no_card']} landmarked frame(s) have no colour standard"
             if marks["no_card"] else "every landmarked frame has a colour standard")
        line(marks["crossing"] == 0,
             f"{marks['crossing']} outline(s) cross themselves - points out of order"
             if marks["crossing"] else "no crossed outlines")
        if marks["no_id"]:
            self.append_log(f"  note  {marks['no_id']} frame(s) have no fish ID yet "
                            f"(press T while landmarking)\n", "note")

        facing = checks.facing_report()
        if facing:
            total = facing["right"] + facing["left"]
            self.append_log(f"\n  Facing: {facing['right']} right, {facing['left']} left"
                            f" (of {total})\n")
            if facing["right"] and facing["left"]:
                self.append_log("  Both directions are present. Colormesh mirrors the "
                                "minority before building the reference shape, which "
                                "it must: averaging a fish with its mirror image "
                                "collapses that shape. Watch for the 'Mirroring N "
                                "frame(s)' line in step 6.\n", "note")
            if facing["unreadable"]:
                self.append_log(f"  {facing['unreadable']} landmark file(s) could not "
                                f"be read.\n", "bad")
        self.refresh_steps()

    def step_colour(self):
        if not self.require_project():
            return
        if self.rscript is None:
            messagebox.showerror("R not found",
                                 "This step needs R with the Colormesh package.\n\n"
                                 "Install R, then in R:\n"
                                 '    install.packages(c("Colormesh", "geomorph", '
                                 '"Morpho", "imager", "dplyr", "abind"))')
            return
        project = self.project.get()
        marks = ProjectChecks(project).landmarks_state()
        if marks["tps"] == 0:
            messagebox.showwarning("No landmarks", "Landmark some frames first (step 4).")
            return
        if marks["no_card"]:
            if not messagebox.askyesno(
                    "Frames without a colour standard",
                    f"{marks['no_card']} landmarked frame(s) have no colour standard, "
                    f"so they cannot be calibrated and will fail in Colormesh.\n\n"
                    f"Carry on anyway?"):
                return

        self.save_settings()
        values = self.settings_dict()
        generated = os.path.join(project, "_generated")
        written, problems = write_configured_r(project, values, generated)
        for problem in problems:
            self.append_log("  " + problem + "\n", "bad")
        if problems:
            messagebox.showerror("Could not set up the R scripts",
                                 "\n".join(problems))
            return
        self.append_log(f"Wrote configured copies of the R scripts into {generated}\n")
        for folder in ("warped", "colormaps", "results"):
            os.makedirs(os.path.join(project, folder), exist_ok=True)

        self._colour_stage = 0
        self._run_colour_stage()

    def _run_colour_stage(self):
        """Colormesh, then the CIE conversion, one after the other."""
        project = self.project.get()
        generated = os.path.join(project, "_generated")
        stages = [("Colormesh (warping and sampling)", R_STEPS["colormesh"]),
                  ("CIE L*a*b* conversion", R_STEPS["cie"])]
        if self._colour_stage >= len(stages):
            self.append_log("\nColour extraction finished. Step 7 next.\n", "good")
            self.refresh_steps()
            return
        label, script = stages[self._colour_stage]
        self._colour_stage += 1
        self._after_step = self._run_colour_stage
        self.run_step(label, [self.rscript, os.path.join(generated, script)],
                      working_directory=generated)

    def step_results(self):
        if not self.require_project():
            return
        if self.rscript is None:
            messagebox.showerror("R not found", "This step needs R.")
            return
        project = self.project.get()
        colour = ProjectChecks(project).colour_state()
        if not colour["lab"]:
            messagebox.showwarning("No colour data",
                                   "Run step 6 first - there is no LAB_average file yet.")
            return
        self.save_settings()
        values = self.settings_dict()
        generated = os.path.join(project, "_generated")
        written, problems = write_configured_r(project, values, generated)
        if problems:
            messagebox.showerror("Could not set up the R scripts", "\n".join(problems))
            return
        self._results_stage = 0
        self._run_results_stage()

    def _run_results_stage(self):
        project = self.project.get()
        generated = os.path.join(project, "_generated")
        if self._results_stage == 0:
            self._results_stage = 1
            self._after_step = self._run_results_stage
            self.run_step("Rates and capacity",
                          [self.rscript, os.path.join(generated, R_STEPS["rates"])],
                          working_directory=generated)
            return
        if self._results_stage == 1:
            self._results_stage = 2
            self._after_step = None
            colour = ProjectChecks(project).colour_state()
            if colour["colormap"] and os.path.exists(script_path(PYTHON_STEPS["colormaps"])):
                self.run_step("Colour maps per fish",
                              [sys.executable, script_path(PYTHON_STEPS["colormaps"]),
                               "--colormap", colour["colormap"],
                               "--manifest", os.path.join(project, "frames",
                                                          "frames_manifest.csv"),
                               "--landmarks-csv", os.path.join(project, "landmarks",
                                                               "landmarks.csv"),
                               "--out", os.path.join(project, "results")])
            else:
                self.append_log("\nAll done. Results are in the results folder.\n",
                                "good")
                self.refresh_steps()


def main():
    if sys.version_info < (3, 8):
        print("This needs Python 3.8 or newer.")
        return 1
    try:
        import tkinter                                   # noqa: F401
    except ImportError:
        print("Tkinter is missing. On Windows and macOS it comes with Python; "
              "on Linux install python3-tk.")
        return 1
    import tkinter.simpledialog                          # noqa: F401
    tk.simpledialog = tkinter.simpledialog
    Application().mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
