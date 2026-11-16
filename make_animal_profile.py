r"""
make_animal_profile.py - create a landmark scheme and default shape for a
new animal, from one of your own frames.

    python make_animal_profile.py                 (asks for a frame)
    python make_animal_profile.py some_frame.png

1. Name the animal and say how many PRIMARY landmarks it has (the named
   anatomical points, like the killifish's 7), then name each one and say
   how many semilandmarks go between it and the next. The last one's
   semilandmarks run back round to landmark 1, so the outline is closed.
2. Click the primary landmarks on the frame, in order.
3. Press "Fill in semilandmarks": they're spaced evenly along a smooth
   curve through your primary points. Drag any point (primary or semi)
   onto the animal's real edge.
4. Save. The profile goes in the profiles folder, and becomes an option in
   the Animal dropdown in Rainfish. find_animal_landmarks.py uses it with
   --profile, and the shape you drew becomes the default shape (G).

The shape is stored centred, at unit size and turned so landmark 1 points
right, so it fits any frame size; where you drew it in the frame doesn't
matter.
"""
import argparse
import base64
import json
import os
import re
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PROFILE_DIR = os.path.join(HERE, "profiles")
CANVAS_W, CANVAS_H = 960, 680
PRIMARY_COLOUR = "#e0302a"
SEMI_COLOUR = "#ff9a1f"
LINE_COLOUR = "#2ec24a"
HIT_RADIUS = 9


# ---------------------------------------------------------------- geometry
def catmull_rom_piece(p0, p1, p2, p3, samples=200):
    """The stretch of a centripetal-ish (uniform) Catmull-Rom curve from p1 to p2."""
    t = np.linspace(0.0, 1.0, samples)[:, None]
    return 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t ** 2
                  + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3)


def semis_along_curve(primaries, counts):
    """Evenly spaced (by arc length) semilandmarks between each consecutive
    pair of primary points, along a closed smooth curve through them.
    Returned in landmark-number order: all of segment 1->2, then 2->3, ..."""
    p = np.asarray(primaries, dtype=np.float64)
    n = len(p)
    out = []
    for segment, how_many in enumerate(counts):
        if how_many <= 0:
            continue
        piece = catmull_rom_piece(p[(segment - 1) % n], p[segment],
                                  p[(segment + 1) % n], p[(segment + 2) % n])
        steps = np.linalg.norm(np.diff(piece, axis=0), axis=1)
        along = np.concatenate([[0.0], np.cumsum(steps)])
        total = along[-1] or 1.0
        for k in range(1, how_many + 1):
            target = total * k / (how_many + 1)
            out.append([np.interp(target, along, piece[:, 0]),
                        np.interp(target, along, piece[:, 1])])
    return np.array(out).reshape(-1, 2)


def perimeter_order(n_primary, counts):
    """0-based order of the landmarks walking round the outline."""
    order, number = [0], n_primary
    for segment, how_many in enumerate(counts):
        order += list(range(number, number + how_many))
        number += how_many
        end = (segment + 1) % n_primary
        if end:
            order.append(end)
    return order


def segments_cross(a1, a2, b1, b2):
    def side(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    return ((side(b1, b2, a1) > 0) != (side(b1, b2, a2) > 0)
            and (side(a1, a2, b1) > 0) != (side(a1, a2, b2) > 0))


def count_crossings(loop):
    n, crossings = len(loop), 0
    for i in range(n):
        for j in range(i + 2, n):
            if i == 0 and j == n - 1:
                continue
            if segments_cross(loop[i], loop[(i + 1) % n], loop[j], loop[(j + 1) % n]):
                crossings += 1
    return crossings


def normalise_shape(points, n_primary):
    """Centre, unit centroid size, landmark 1 pointing along +x.

    'Back' is the primary landmark furthest from landmark 1. A shape drawn
    facing left is mirrored first (rather than rotated 180 degrees), so the
    animal's top stays on top."""
    pts = np.asarray(points, dtype=np.float64)
    primaries = pts[:n_primary]
    back = int(np.argmax(np.linalg.norm(primaries - primaries[0], axis=1)))
    if pts[0, 0] < pts[back, 0]:
        pts = pts.copy()
        pts[:, 0] = -pts[:, 0]
    pts = pts - pts.mean(axis=0)
    pts = pts / (np.sqrt((pts ** 2).sum()) or 1.0)
    axis = pts[0] - pts[back]
    angle = np.arctan2(axis[1], axis[0])
    c, s = np.cos(-angle), np.sin(-angle)
    return pts @ np.array([[c, -s], [s, c]]).T, back


# --------------------------------------------------------------------- app
class ProfileMaker(tk.Tk):
    def __init__(self, image_path=None, out_dir=PROFILE_DIR):
        super().__init__()
        self.title("Rainfish - create an animal profile")
        self.geometry("1360x780")
        self.out_dir = out_dir
        self.image = None             # original BGR frame
        self.photo = None
        self.view_scale = 1.0
        self.primaries = []           # image coordinates
        self.semis = None             # array, image coordinates, or None
        self.dragging = None          # ("p", i) or ("s", i)
        self.name_vars, self.count_vars = [], []
        self.saved_path = None

        self._build()
        self.set_primary_count()
        if image_path:
            self.load_image(image_path)
        else:
            self.after(200, self.open_image)

    # ------------------------------------------------------------- layout
    def _build(self):
        left = ttk.Frame(self, padding=10)
        left.pack(side="left", fill="y")
        right = ttk.Frame(self, padding=(0, 10, 10, 10))
        right.pack(side="left", fill="both", expand=True)

        ttk.Label(left, text="Animal name:").grid(row=0, column=0, sticky="w")
        self.profile_name = tk.StringVar(value="")
        ttk.Entry(left, textvariable=self.profile_name, width=28).grid(
            row=0, column=1, columnspan=2, sticky="w", pady=2)

        ttk.Label(left, text="Primary landmarks:").grid(row=1, column=0, sticky="w")
        self.n_primary = tk.IntVar(value=7)
        ttk.Spinbox(left, from_=3, to=40, textvariable=self.n_primary, width=6).grid(
            row=1, column=1, sticky="w", pady=2)
        ttk.Button(left, text="Set", command=self.set_primary_count).grid(
            row=1, column=2, sticky="w")

        ttk.Label(left, text="Name each primary landmark, and how many "
                             "semilandmarks go between it and the next one "
                             "(the last runs back to landmark 1).",
                  wraplength=330, foreground="#555").grid(
            row=2, column=0, columnspan=3, sticky="w", pady=(8, 4))

        table_holder = ttk.Frame(left)
        table_holder.grid(row=3, column=0, columnspan=3, sticky="nsew")
        left.rowconfigure(3, weight=1)
        self.table_canvas = tk.Canvas(table_holder, width=340, height=330,
                                      highlightthickness=0)
        scroll = ttk.Scrollbar(table_holder, command=self.table_canvas.yview)
        self.table = ttk.Frame(self.table_canvas)
        self.table.bind("<Configure>", lambda e: self.table_canvas.configure(
            scrollregion=self.table_canvas.bbox("all")))
        self.table_canvas.create_window((0, 0), window=self.table, anchor="nw")
        self.table_canvas.configure(yscrollcommand=scroll.set)
        self.table_canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        self.total_label = ttk.Label(left, text="", font=("", 10, "bold"))
        self.total_label.grid(row=4, column=0, columnspan=3, sticky="w", pady=6)

        buttons = ttk.Frame(left)
        buttons.grid(row=5, column=0, columnspan=3, sticky="ew")
        for text, command in (("Open frame...", self.open_image),
                              ("Undo last click", self.undo),
                              ("Clear points", self.clear_points),
                              ("Fill in semilandmarks", self.fill_semis),
                              ("Save profile", self.save)):
            ttk.Button(buttons, text=text, command=command).pack(fill="x", pady=2)

        self.status = ttk.Label(right, text="", font=("", 11))
        self.status.pack(anchor="w", pady=(0, 6))
        self.canvas = tk.Canvas(right, width=CANVAS_W, height=CANVAS_H, bg="#222",
                                highlightthickness=0, cursor="crosshair")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Button-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", lambda e: setattr(self, "dragging", None))
        self.canvas.bind("<Button-3>", lambda e: self.undo())
        self.bind("<Control-z>", lambda e: self.undo())

    def set_primary_count(self):
        try:
            n = max(3, min(40, int(self.n_primary.get())))
        except (tk.TclError, ValueError):
            n = 7
        self.n_primary.set(n)
        old_names = [v.get() for v in self.name_vars]
        old_counts = [v.get() for v in self.count_vars]
        for child in self.table.winfo_children():
            child.destroy()
        self.name_vars, self.count_vars = [], []
        ttk.Label(self.table, text="#").grid(row=0, column=0)
        ttk.Label(self.table, text="Name").grid(row=0, column=1, sticky="w")
        ttk.Label(self.table, text="Semis to next").grid(row=0, column=2)
        for i in range(n):
            name = tk.StringVar(value=old_names[i] if i < len(old_names)
                                else f"landmark_{i + 1}")
            count = tk.StringVar(value=old_counts[i] if i < len(old_counts) else "3")
            ttk.Label(self.table, text=str(i + 1)).grid(row=i + 1, column=0, padx=(0, 4))
            ttk.Entry(self.table, textvariable=name, width=24).grid(
                row=i + 1, column=1, pady=1)
            spin = ttk.Spinbox(self.table, from_=0, to=60, textvariable=count, width=5,
                               command=self.on_counts_changed)
            spin.grid(row=i + 1, column=2, padx=4)
            spin.bind("<KeyRelease>", lambda e: self.on_counts_changed())
            target = "1" if i == n - 1 else str(i + 2)
            ttk.Label(self.table, text=f"-> {target}", foreground="#777").grid(
                row=i + 1, column=3)
            name.trace_add("write", lambda *a: self.redraw())
            self.name_vars.append(name)
            self.count_vars.append(count)
        if len(self.primaries) > n:
            self.primaries = self.primaries[:n]
        self.semis = None
        self.on_counts_changed()

    def counts(self):
        out = []
        for v in self.count_vars:
            try:
                out.append(max(0, int(v.get())))
            except ValueError:
                out.append(0)
        return out

    def on_counts_changed(self):
        n, semis = len(self.count_vars), sum(self.counts())
        self.total_label.configure(text=f"{n} primary + {semis} semilandmarks "
                                        f"= {n + semis} landmarks")
        if self.semis is not None:
            self.semis = None         # counts changed: old semis no longer match
        self.redraw()

    # -------------------------------------------------------------- image
    def open_image(self):
        path = filedialog.askopenfilename(
            title="Choose a frame showing the animal",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.tif *.tiff *.bmp"),
                       ("All files", "*.*")])
        if path:
            self.load_image(path)

    def load_image(self, path):
        image = cv2.imread(path)
        if image is None:
            messagebox.showerror("Can't open", f"Couldn't read {path} as an image.")
            return
        self.image = image
        h, w = image.shape[:2]
        self.view_scale = min(CANVAS_W / w, CANVAS_H / h, 1.0)
        shown = cv2.resize(image, (int(w * self.view_scale), int(h * self.view_scale)),
                           interpolation=cv2.INTER_AREA)
        ok, png = cv2.imencode(".png", shown)
        self.photo = tk.PhotoImage(data=base64.b64encode(png.tobytes()))
        self.primaries, self.semis = [], None
        if not self.profile_name.get():
            self.profile_name.set("")
        self.redraw()

    def to_view(self, point):
        return point[0] * self.view_scale, point[1] * self.view_scale

    def to_image(self, x, y):
        return np.array([x / self.view_scale, y / self.view_scale])

    # ------------------------------------------------------------ editing
    def hit(self, x, y):
        candidates = [("p", i, p) for i, p in enumerate(self.primaries)]
        if self.semis is not None:
            candidates += [("s", i, p) for i, p in enumerate(self.semis)]
        for kind, i, p in candidates:
            vx, vy = self.to_view(p)
            if (vx - x) ** 2 + (vy - y) ** 2 <= HIT_RADIUS ** 2:
                return kind, i
        return None

    def on_press(self, event):
        if self.image is None:
            return
        hit = self.hit(event.x, event.y)
        if hit:
            self.dragging = hit
            return
        if len(self.primaries) < len(self.name_vars):
            self.primaries.append(self.to_image(event.x, event.y))
            if len(self.primaries) == len(self.name_vars):
                self.fill_semis()
            self.redraw()

    def on_drag(self, event):
        if not self.dragging:
            return
        kind, i = self.dragging
        point = self.to_image(event.x, event.y)
        if kind == "p":
            self.primaries[i] = point
        else:
            self.semis[i] = point
        self.redraw()

    def undo(self):
        if self.semis is not None:
            self.semis = None
        elif self.primaries:
            self.primaries.pop()
        self.redraw()

    def clear_points(self):
        self.primaries, self.semis = [], None
        self.redraw()

    def fill_semis(self):
        if len(self.primaries) != len(self.name_vars):
            messagebox.showinfo("Not yet", f"Click all {len(self.name_vars)} primary "
                                           f"landmarks first ({len(self.primaries)} so far).")
            return
        self.semis = semis_along_curve(self.primaries, self.counts())
        self.redraw()

    def all_points(self):
        if self.semis is None or len(self.primaries) != len(self.name_vars):
            return None
        return np.vstack([np.asarray(self.primaries), self.semis.reshape(-1, 2)])

    # ------------------------------------------------------------ drawing
    def redraw(self):
        if not hasattr(self, "canvas"):
            return
        c = self.canvas
        c.delete("all")
        if self.photo is not None:
            c.create_image(0, 0, image=self.photo, anchor="nw")
        else:
            c.create_text(CANVAS_W // 2, CANVAS_H // 2, fill="#ccc",
                          text="Open a frame showing the animal (button on the left).")
        n = len(self.name_vars)
        points = self.all_points()
        if points is not None:
            order = perimeter_order(n, self.counts())
            loop = [self.to_view(points[i]) for i in order]
            c.create_line(*[v for xy in loop + loop[:1] for v in xy],
                          fill=LINE_COLOUR, width=2)
            for k, p in enumerate(self.semis):
                x, y = self.to_view(p)
                c.create_oval(x - 4, y - 4, x + 4, y + 4, fill=SEMI_COLOUR, outline="")
        elif len(self.primaries) >= 2:
            pts = [self.to_view(p) for p in self.primaries]
            c.create_line(*[v for xy in pts for v in xy], fill=LINE_COLOUR, dash=(4, 3))
        for i, p in enumerate(self.primaries):
            x, y = self.to_view(p)
            c.create_oval(x - 6, y - 6, x + 6, y + 6, fill=PRIMARY_COLOUR, outline="white")
            label = self.name_vars[i].get() if i < n else ""
            c.create_text(x + 9, y - 9, anchor="w", fill="white",
                          text=f"{i + 1} {label}", font=("", 10, "bold"))

        if self.image is None:
            text = "Open a frame to begin."
        elif len(self.primaries) < n:
            nxt = self.name_vars[len(self.primaries)].get()
            text = (f"Click primary landmark {len(self.primaries) + 1} of {n}:  {nxt}"
                    f"      (right-click = undo)")
        elif self.semis is None:
            text = "All primary landmarks placed - press 'Fill in semilandmarks'."
        else:
            text = ("Drag any point onto the animal's edge, then 'Save profile'.  "
                    f"{len(points)} landmarks.")
        self.status.configure(text=text)

    # --------------------------------------------------------------- save
    def save(self):
        name = self.profile_name.get().strip()
        if not name:
            messagebox.showwarning("Name needed", "Give the animal a name first.")
            return
        labels = [v.get().strip().replace(" ", "_") for v in self.name_vars]
        if any(not label for label in labels):
            messagebox.showwarning("Names needed", "Every primary landmark needs a name.")
            return
        if len(set(labels)) != len(labels):
            messagebox.showwarning("Duplicate names", "Each primary landmark needs a "
                                                      "different name.")
            return
        points = self.all_points()
        if points is None:
            messagebox.showwarning("Shape needed", "Click the primary landmarks and fill "
                                                   "in the semilandmarks first.")
            return
        counts = self.counts()
        loop = points[perimeter_order(len(labels), counts)]
        crossings = count_crossings(loop)
        if crossings and not messagebox.askyesno(
                "Outline crosses itself",
                f"The outline crosses itself in {crossings} place(s), which usually "
                f"means points are out of order. Save anyway?"):
            return

        template, back = normalise_shape(points, len(labels))
        slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") or "animal"
        os.makedirs(self.out_dir, exist_ok=True)
        path = os.path.join(self.out_dir, f"{slug}.json")
        if os.path.basename(path) == "killifish.json":
            messagebox.showwarning("Reserved name", "killifish.json is the built-in fish "
                                                    "preset - choose another name.")
            return
        if os.path.exists(path) and not messagebox.askyesno(
                "Replace?", f"A profile called {slug} already exists. Replace it?"):
            return
        profile = {
            "name": f"{name} ({len(points)} landmarks)",
            "fixed_names": labels,
            "semis_per_segment": counts,
            "force_body_curve_segments": [],
            "auto_detect": False,
            "facing": {"front": [1], "back": [back + 1]},
            "template": [[round(float(x), 5), round(float(y), 5)] for x, y in template],
            "template_source": "drawn with make_animal_profile.py",
        }
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(profile, handle, indent=1)
        self.saved_path = path
        print(f"SAVED: {path}", flush=True)
        messagebox.showinfo("Saved", f"Saved {profile['name']} to\n{path}")
        self.destroy()


def main():
    parser = argparse.ArgumentParser(description="Create an animal landmark profile.")
    parser.add_argument("image", nargs="?", help="a frame showing the animal")
    parser.add_argument("--out", default=PROFILE_DIR, help="folder to save the profile in")
    options = parser.parse_args()
    app = ProfileMaker(options.image, options.out)
    app.mainloop()
    if not app.saved_path:
        print("Closed without saving a profile.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
