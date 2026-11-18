"""The Rainfish window: settings saved and loaded, older projects, the
animal choice, text size, and the checks that stop a step running on
input it can't use. Needs a screen (on a server, run under xvfb)."""
import json
import tkinter
import tkinter.simpledialog

import pytest

import rainfish_gui as gui


@pytest.fixture
def app(monkeypatch, tmp_path):
    gui.tk.simpledialog = tkinter.simpledialog
    monkeypatch.setattr(gui, "SPLASH_IMAGE", str(tmp_path / "no_splash.png"))
    monkeypatch.setattr(gui, "PREFS_FILE", str(tmp_path / "prefs.json"))
    messages = []
    for kind in ("showwarning", "showerror", "showinfo"):
        monkeypatch.setattr(gui.messagebox, kind,
                            lambda title, text="", **k: messages.append((title, text)))
    monkeypatch.setattr(gui.messagebox, "askyesno", lambda *a, **k: False)
    try:
        window = gui.Application()
    except tkinter.TclError as error:
        pytest.skip(f"no display available for the window ({error})")
    window.messages = messages
    window.started = []
    window.run_step = lambda label, *a, **k: window.started.append(label)
    window.update()
    yield window
    window.destroy()


def test_window_opens(app):
    assert app.title() == "Rainfish"
    assert "frames_per_video" in app.settings_widgets
    assert "capacity_frame_seconds" not in app.settings_widgets   # now the optional extra frame
    assert app.profile_file == gui.FISH_PROFILE                    # fish preset by default
    assert app.extra_frame.get() is False


def test_settings_round_trip(app, tmp_path):
    app.project.set(str(tmp_path))
    app.settings_widgets["frames_per_video"].set("12")
    app.extra_frame.set(True)
    app.extra_frame_seconds.set("240")
    app.landmark_requires["label"].set(False)
    app.save_settings()
    saved = json.loads((tmp_path / gui.SETTINGS_FILE).read_text())
    assert saved["sampling"]["frames_per_video"] == 12
    assert saved["sampling"]["extra_frame"] is True
    assert saved["landmarking_requires"]["label"] is False

    app.settings_widgets["frames_per_video"].set("3")
    app.extra_frame.set(False)
    app.landmark_requires["label"].set(True)
    app.load_settings()
    assert app.settings_widgets["frames_per_video"].get() == "12"
    assert app.extra_frame.get() is True and app.extra_frame_seconds.get() == "240"
    assert app.landmark_requires["label"].get() is False


def test_older_project_settings_still_load(app, tmp_path):
    (tmp_path / gui.OLD_SETTINGS_FILE).write_text(json.dumps(
        {"sampling": {"frames_per_video": 10, "capacity_frame_seconds": 300}}))
    app.project.set(str(tmp_path))
    app.load_settings()
    assert app.extra_frame.get() is True             # they always took a capacity frame
    assert app.extra_frame_seconds.get() == "300"
    assert app.profile_file == gui.FISH_PROFILE


def test_unknown_animal_falls_back_to_fish(app, tmp_path):
    (tmp_path / gui.SETTINGS_FILE).write_text(json.dumps({"animal_profile": "gone.json"}))
    app.project.set(str(tmp_path))
    app.load_settings()
    assert app.profile_file == gui.FISH_PROFILE


def test_text_size_changes_and_is_limited(app):
    app.set_font_size(12, save=False)
    app.change_font_size(+1)
    assert app.font_size == 13
    assert gui.tkfont.nametofont("TkDefaultFont").cget("size") == 13
    app.set_font_size(999, save=False)
    assert app.font_size == gui.MAX_FONT_SIZE
    app.change_font_size(0)
    assert app.font_size == gui.DEFAULT_FONT_SIZE


def test_results_step_refuses_too_few_frames(app, tmp_path):
    """With fewer than 4 frames per video the rates can't be fitted; say so
    rather than letting R stop with an error."""
    (tmp_path / "frames").mkdir()
    (tmp_path / "colormaps").mkdir()
    (tmp_path / "colormaps" / "LAB_average_white.csv").write_text("image,L_mean\n")
    rows = ["image,video,seconds,capacity_frame"]
    rows += [f"v1_f{i}.png,v1.mp4,{i * 10},0" for i in range(2)]
    (tmp_path / "frames" / "frames_manifest.csv").write_text("\n".join(rows) + "\n")
    app.rscript = app.rscript or "Rscript"
    app.project.set(str(tmp_path))
    app.step_results()
    assert app.started == []
    assert app.messages and app.messages[-1][0] == "Not enough frames per video"


def test_extract_step_passes_extra_frame_choice(app, tmp_path):
    (tmp_path / "videos").mkdir()
    (tmp_path / "videos" / "clip.mp4").write_bytes(b"")
    app.project.set(str(tmp_path))
    commands = []
    app.run_step = lambda label, command, *a, **k: commands.append(command)
    app.extra_frame.set(False)
    app.step_extract()
    assert commands[-1][commands[-1].index("--capacity-at") + 1] == "0"
    app.extra_frame.set(True)
    app.extra_frame_seconds.set("250")
    app.step_extract()
    assert commands[-1][commands[-1].index("--capacity-at") + 1] == "250.0"
