# -*- coding: utf-8 -*-
"""Theme kit (plan Phase K1): derive, compose, audit, family, status colours,
export and the CLI."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from hypothesis import given, settings, strategies as st

from lace import color_science as cs
from lace.dock_custom_theme import THEME_SPECS
from lace.dock_theme import ThemeSpec, build_theme, deep_to_serializable, explicit_tokens
from lace.theme_contrast import CONTRAST_LEVELS, CONTRAST_TARGETS, audit as phase2_audit
from lace.theme_kit import (CHASSIS, audit, chassis_of, compose, derive, export, family,
                            palette_of, spec_delta, status_colors)
from lace.theme_kit.audit import _lookup
from lace.theme_kit.derive import STATUS_HUES
from lace.theme_models import ThemeJson
from tests.theme_sets import FIXTURES, kilim_keys

ROOT = Path(__file__).resolve().parent.parent


def spec_for(key):
    if key.startswith("kilim_"):
        return ThemeJson.load(FIXTURES / f"{key}.json").to_theme_spec()
    return THEME_SPECS[key]


ALL_SPECS = sorted(THEME_SPECS) + kilim_keys()


def tokens(spec):
    return deep_to_serializable(build_theme(spec))


# --- derive + compose + audit ---------------------------------------------------
channel = st.integers(0, 255)
colour = st.tuples(channel, channel, channel).map(lambda t: [*t, 255])


@settings(max_examples=30, deadline=None)
@given(colour, colour, st.sampled_from(CONTRAST_LEVELS), st.sampled_from(sorted(CHASSIS)))
def test_derived_themes_pass_or_say_why(base, accent, contrast, chassis):
    """Random seeds: nothing derived misses a floor, and every miss is named
    as the seeds' own (capped) or out of reach."""
    spec = compose(derive(base, accent, contrast=contrast), chassis)
    report = audit(spec)
    assert report.contrast == contrast
    assert report.passed, report.lines()
    explicit = explicit_tokens(spec)
    assert all(m.token in explicit for m in report.capped)


def test_derive_picks_readable_text():
    for base in ("#101010", "#f4f4f4", "#3a6ea5", "#808080"):
        pal = derive(base, "#ff8800")
        assert cs.contrast_ratio(pal.text, pal.base) >= 4.5


def test_neutral_tint_turns_the_base_toward_the_accent():
    plain = derive("#20242c", "#e0a030")
    tinted = derive("#20242c", "#e0a030", neutral_tint=1.0)
    _, c0, _, _ = cs.to_oklch(plain.base)
    L1, c1, h1, _ = cs.to_oklch(tinted.base)
    assert c1 > c0
    assert abs(h1 - cs.to_oklch(plain.accent)[2]) < 3
    assert abs(L1 - cs.to_oklch(plain.base)[0]) < 0.01
    with pytest.raises(ValueError):
        derive("#000", "#fff", neutral_tint=2)


def test_audit_suggestions_fix_capped_colours():
    spec = ThemeSpec(base=[30, 30, 30, 255], accent=[60, 60, 70, 255], text=[70, 70, 70, 255])
    report = audit(spec)
    assert report.capped and not report.strict_passed
    fixed = {s.token: s.new for s in report.suggest()}
    checked = 0
    for m in report.capped:
        if m.kind == "contrast" and m.token in fixed:
            bg = _lookup(report.theme, m.surface)
            assert cs.contrast_ratio(fixed[m.token], bg) >= m.target - 0.01
            checked += 1
    assert checked


def test_audit_warns_on_a_faint_accent():
    spec = ThemeSpec(base=[40, 40, 40, 255], accent=[52, 52, 58, 255], text=[230, 230, 230, 255])
    assert any(w.kind == "accent" for w in audit(spec).warnings)


@pytest.mark.parametrize("key", ALL_SPECS)
def test_audit_agrees_with_phase2(key):
    """The kit's failures are exactly Phase 2's hard misses."""
    spec = spec_for(key)
    theme = build_theme(spec)
    explicit = explicit_tokens(spec)
    hard = {(m.token, m.surface) for m in phase2_audit(theme, spec.contrast, spec.depth)
            if m.token not in explicit and not m.unreachable}
    report = audit(spec)
    assert {(m.token, m.surface) for m in report.failures} == hard
    assert report.passed == (not hard)


# --- chassis ----------------------------------------------------------------------
@pytest.mark.parametrize("key", ALL_SPECS)
def test_chassis_round_trip(key):
    spec = spec_for(key)
    name, overrides = chassis_of(spec)
    assert name in CHASSIS
    assert tokens(compose(palette_of(spec), name, **overrides)) == tokens(spec)


@pytest.mark.parametrize("key, chassis", [
    ("dark", "classic"), ("nordic", "flat"), ("solarized_light", "flat"),
    ("cyberpunk_edge", "edge"), ("violet_haze", "haze"),
    ("midnight_haze", "haze"), ("cyberpunk_neon", "neon"),
])
def test_chassis_source_presets(key, chassis):
    """Each chassis is closest to the preset it was taken from."""
    assert chassis_of(THEME_SPECS[key])[0] == chassis


def test_chassis_colour_roles_follow_the_palette():
    pal = derive("#202020", "#00a0ff")
    spec = compose(pal, "edge", focus_border_color=[255, 0, 0, 255])
    assert list(spec.sidebar_tab_border_active_color) == list(pal.accent)
    spec = compose(derive("#202020", "#00a0ff"), "haze")
    assert list(spec.sidebar_tab_border_color) == [0, 0, 0, 0]
    with pytest.raises(TypeError):
        compose(pal, "edge", not_a_field=1)


def test_neon_dusk_needs_overrides():
    """The plan's example of a preset that fits no chassis exactly."""
    assert chassis_of(THEME_SPECS["neon_dusk"])[1]


# --- family -----------------------------------------------------------------------
#: Mean ΔE (OKLab) over the colours a family member sets, against the
#: hand-made preset. ~0.02 is just noticeable; 0.06 reads as the same theme
#: with a few colours tuned differently.
FAMILY_BUDGET = 0.06

FAMILIES = {
    "cyberpunk_edge": {"neutral": "cyberpunk_edge_neutral", "light": "cyberpunk_edge_light"},
    "violet_haze": {"neutral": "violet_haze_neutral", "light": "violet_haze_light"},
    "midnight_haze": {"neutral": "midnight_haze_neutral", "light": "midnight_haze_light"},
    "slate_amber_dark": {"neutral": "slate_amber", "light": "slate_amber_light"},
}

#: Members the kit misses by more than the budget, and why. Listed, not forced.
FAMILY_MISSES = {
    ("slate_amber_dark", "neutral"): "slate_amber sits at L 0.815, a light theme "
                                     "rather than the mid-tone neutral the kit makes",
}


@pytest.mark.parametrize("source, variant", [
    pytest.param(s, v, marks=pytest.mark.xfail(strict=True, reason=FAMILY_MISSES[(s, v)]))
    if (s, v) in FAMILY_MISSES else (s, v)
    for s, members in FAMILIES.items() for v in members
])
def test_family_reproduces_hand_made_members(source, variant):
    made = family(THEME_SPECS[source])[variant]
    mean, worst, field = spec_delta(made, THEME_SPECS[FAMILIES[source][variant]])
    assert mean <= FAMILY_BUDGET, (mean, worst, field)


@pytest.mark.parametrize("key", ["cyberpunk_edge", "violet_haze_light", "slate_amber",
                                 "kilim_dark", "kilim_light_neo"])
def test_family_members_keep_hue_and_pass(key):
    spec = spec_for(key)
    members = family(spec)
    assert set(members) == {"dark", "neutral", "light"}
    Ls = [cs.to_oklch(list(members[v].base))[0] for v in ("dark", "neutral", "light")]
    assert Ls == sorted(Ls)
    h0 = cs.to_oklch(list(spec.accent))[2]
    for member in members.values():
        h = cs.to_oklch(list(member.accent))[2]
        assert min(abs(h - h0), 360 - abs(h - h0)) < 12
        assert audit(member).passed


# --- status colours ---------------------------------------------------------------
@pytest.mark.parametrize("base", ["#15171c", "#f5f5f2", "#1e1a2e", "#fafafa"])
def test_status_colours_match_and_read(base):
    pal = derive(base, "#4f8cff")
    colours = status_colors(pal)
    assert set(colours) == set(STATUS_HUES)
    Ls = {round(cs.to_oklch(c)[0], 2) for c in colours.values()}
    assert len(Ls) == 1
    target = CONTRAST_TARGETS["muted"]["normal"]
    assert all(cs.contrast_ratio(c, pal.base) >= target for c in colours.values())
    for name, c in colours.items():
        h = cs.to_oklch(c)[2]
        assert min(abs(h - STATUS_HUES[name]), 360 - abs(h - STATUS_HUES[name])) < 10


# --- export -----------------------------------------------------------------------
@pytest.mark.parametrize("key", ALL_SPECS)
def test_json_round_trip(key, tmp_path):
    spec = spec_for(key)
    path = tmp_path / "t.json"
    export.to_json(spec, path, name=key)
    from lace.theme_models import load_theme_json
    assert deep_to_serializable(load_theme_json(path)) == tokens(spec)


@pytest.mark.parametrize("key", ALL_SPECS)
def test_python_literal_round_trip(key):
    spec = spec_for(key)
    assert tokens(eval(export.to_python(spec), {"ThemeSpec": ThemeSpec})) == tokens(spec)
    named = eval("{" + export.to_python(spec, name=key) + "}", {"ThemeSpec": ThemeSpec})
    assert tokens(named[key]) == tokens(spec)


def test_diff():
    a = THEME_SPECS["dark"]
    from dataclasses import replace
    b = replace(a, accent=[200, 60, 60, 255])
    d = export.diff(a, b)
    assert d and all(v is None or v > 0 for v in d.values())
    assert "CORE.accent_color" in d
    assert export.diff(a, a) == {}
    values = [v for v in d.values() if v is not None]
    assert values == sorted(values, reverse=True)


# --- CLI --------------------------------------------------------------------------
def _cli(*args):
    env = dict(os.environ, PYTHONPATH=str(ROOT))
    return subprocess.run([sys.executable, "-m", "lace.theme_kit", *args],
                          capture_output=True, text=True, env=env, cwd=ROOT, timeout=120)


def test_cli(tmp_path):
    fixture = str(FIXTURES / "kilim_dark.json")
    out = tmp_path / "derived.json"
    r = _cli("derive", "--base", "#1b1d23", "--accent", "#4f8cff", "--chassis", "edge",
             "--out", str(out))
    assert r.returncode == 0, r.stderr
    assert json.loads(out.read_text())["corner_radius"] == 10
    assert _cli("audit", str(out)).returncode in (0, 1)
    for source in ([fixture], ["--preset", "slate_amber"]):
        r = _cli("audit", *source, "--allow-capped")
        assert r.returncode == 0, r.stdout + r.stderr
        r = _cli("family", *source, "--out-dir", str(tmp_path / "fam"))
        assert r.returncode == 0, r.stderr
        r = _cli("chassis", *source)
        assert r.returncode == 0 and "chassis" in r.stdout
    assert len(list((tmp_path / "fam").glob("*.json"))) == 6

    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"base": "#202020", "accent": "#303030", "text": "#2a2a2a"}))
    r = _cli("audit", str(bad))
    assert r.returncode == 1 and "capped" in r.stdout
