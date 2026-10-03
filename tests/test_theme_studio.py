# -*- coding: utf-8 -*-
"""Theme Studio (plan Phase K2): the model, an offscreen run of the window,
and that the Studio's theme never reaches a host application."""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication, QToolTip

from lace.dock_custom_theme import THEME_SPECS
from lace.dock_theme import build_theme, deep_to_serializable
from lace.theme_kit import CHASSIS, audit
from lace.theme_kit.studio import KEYWORDS, StudioModel, StudioWindow, launch

ROOT = Path(__file__).resolve().parent.parent
Role = QPalette.ColorRole


def tokens(spec):
    return deep_to_serializable(build_theme(spec))


def settle(app, n=4):
    for _ in range(n):
        app.processEvents()


def palette_key(pal: QPalette):
    return tuple(pal.color(g, r).rgba()
                 for g in (QPalette.ColorGroup.Active, QPalette.ColorGroup.Disabled)
                 for r in (Role.Window, Role.WindowText, Role.Base, Role.Text, Role.Button,
                           Role.Highlight, Role.HighlightedText))


@pytest.mark.parametrize("key", ["dark", "slate_amber", "cyberpunk_neon", "violet_haze_light",
                                 "neon_dusk"])
def test_model_reproduces_a_loaded_theme(key):
    """Loading a preset and changing nothing gives the preset back."""
    model = StudioModel(THEME_SPECS[key], key)
    assert tokens(model.spec()) == tokens(THEME_SPECS[key])
    assert model.diff() == {}


def test_model_fix_and_seed():
    model = StudioModel()
    model.set_seed("text", "#3a3d45")        # too close to the base
    report = model.report()
    assert report.capped
    field = model.apply_fix(report.suggest()[0])
    assert field == "text" and "text" in model.fixes
    assert len(model.report().capped) < len(report.capped)
    model.set_seed("text", None)              # a new seed drops its fix
    assert "text" not in model.fixes and model.seeds["text"] is None


def test_studio_offscreen(qapp, tmp_path):
    """Set seeds, walk every keyword and chassis, fix the audit, export."""
    win = StudioWindow()
    win.show()
    settle(qapp)
    m = win.model
    m.set_seed("base", "#23252b")
    m.set_seed("accent", "#e0803a")
    for key, values in KEYWORDS.items():
        box = win.keyword_boxes[key]
        for value in values:
            box.textActivated.emit(value)
            win.refresh()
            assert m.keywords[key] == value
    for name in CHASSIS:
        win.chassis_box.textActivated.emit(name)
        win.refresh()
        assert m.chassis == name
    win.tint_slider.setValue(30)
    assert m.tint == pytest.approx(0.3)
    for v in (100, 250, 400):
        win.zoom_slider.setValue(v)
        assert win.gallery_view.pixmap().width() > 0

    m.set_seed("text", "#4a4a4a")             # a text colour that misses its floor
    win.refresh()
    for _ in range(10):
        if not win.fix_buttons:
            break
        before = len(m.report().capped)
        win.fix_buttons[0].click()
        win.refresh()
        assert len(m.report().capped) < before
    report = m.report()
    assert report.strict_passed, report.lines()

    path = tmp_path / "studio.json"
    m.name = "studio_made"
    m.to_json(path)
    from lace.theme_models import ThemeJson, load_theme_json
    loaded = ThemeJson.load(path).to_theme_spec()
    assert tokens(loaded) == tokens(m.spec())
    assert deep_to_serializable(load_theme_json(path)) == tokens(m.spec())
    assert audit(loaded).strict_passed
    assert "studio_made" in win.copy_python()
    assert win.diff_view.toPlainText()

    win.open_member("light")
    win.refresh()
    assert m.name == "studio_made_light"
    win.close()
    settle(qapp)


def test_studio_controls_keep_their_palette(qapp):
    """Inside the Studio only the preview follows the theme."""
    app_before = palette_key(QApplication.palette())
    win = StudioWindow(THEME_SPECS["dark"], "dark")
    win.show()
    settle(qapp)
    chrome = palette_key(win.controls.palette())
    assert chrome == app_before
    win.open_spec(THEME_SPECS["solarized_light"], "solarized_light")
    win.refresh()
    settle(qapp)
    assert palette_key(win.controls.palette()) == chrome
    assert palette_key(win.panels.palette()) == chrome
    assert palette_key(win.preview_host.palette()) != chrome
    win.close()
    settle(qapp)


def test_launch_leaves_the_host_alone(qapp, monkeypatch, make_desk):
    """From a Lace app, the Studio opens in its own process: the host's
    palette, tooltips and style manager do not change."""
    from lace.dock_style_manager import get_dock_style_manager

    make_desk()
    get_dock_style_manager().apply_theme_dict(build_theme(THEME_SPECS["dark"]))
    settle(qapp)
    before = (palette_key(QApplication.palette()), palette_key(QToolTip.palette()),
              get_dock_style_manager().generation)
    calls = []
    monkeypatch.setattr(subprocess, "Popen", lambda cmd, **kw: calls.append(cmd))
    launch(preset="slate_amber")
    settle(qapp)
    assert calls == [[sys.executable, "-m", "lace.theme_kit", "studio", "--preset",
                      "slate_amber"]]
    after = (palette_key(QApplication.palette()), palette_key(QToolTip.palette()),
             get_dock_style_manager().generation)
    assert after == before


def test_studio_cli_runs(tmp_path):
    out = tmp_path / "studio.png"
    env = dict(os.environ, PYTHONPATH=str(ROOT), QT_QPA_PLATFORM="offscreen")
    r = subprocess.run([sys.executable, "-m", "lace.theme_kit", "studio", "--preset",
                        "slate_amber", "--tab", "1", "--zoom", "300", "--screenshot", str(out)],
                       capture_output=True, text=True, env=env, cwd=ROOT, timeout=120)
    assert r.returncode == 0, r.stderr
    assert out.stat().st_size > 10_000
