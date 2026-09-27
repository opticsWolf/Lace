# Session S7 Checklist — Theme Studio (Phase K2)

**Goal:** Check by hand what `tests/test_theme_studio.py` can't: picking colours in the
dialog, reading the live preview, and loading a Studio theme in the demo and in another app.

No trace log for this session: sign it off by ticking the boxes and noting the date at the
bottom.

## Setup

```powershell
python -m lace.theme_kit studio
python -m lace.theme_kit studio --preset slate_amber
```

## 1. Two seeds to a passing audit
- [ ] Pick a **base** and an **accent** with the colour buttons; the dock layout, the
      Controls tab and the family strip follow within a moment.
- [ ] Set **text** to a colour close to the base: the Audit tab lists `capped` rows, each
      with a *Fix* button showing old → new.
- [ ] Click *Fix* until the header reads **PASS**. The status line names the fixed fields.
- [ ] **auto** next to text / surface / border returns it to a derived colour and drops its fix.

## 2. Keywords, chassis, tint
- [ ] Each keyword drop-down (`contrast`, `depth`, `selection`, `title_mode`,
      `hover_mode`) visibly changes the preview.
- [ ] Every chassis in the drop-down changes geometry only; colours stay.
- [ ] The neutral-tint slider turns the greys toward the accent hue.

## 3. Preview
- [ ] Dock layout: two areas, tabs, the left sidebar tab opens its panel, and the separate
      **Floating** window is themed too.
- [ ] Controls tab: the zoom slider (100–400 %) redraws the gallery; glyphs stay sharp.
- [ ] The Studio's own panels (left, bottom, zoom bar) keep the system look whatever the theme.

## 4. Family, export, diff
- [ ] The Family tab shows dark / neutral / light with swatches and pass / FAIL; clicking one
      opens it for editing, named `<theme>_<variant>`.
- [ ] *Save JSON...* writes a file; *Copy ThemeSpec* puts a `"name": ThemeSpec(...),` entry
      on the clipboard.
- [ ] The Diff tab lists what changed against the theme the session started from.

## 5. Round trip
- [ ] The saved JSON, applied to the demo (a `DemoMainWindow`, then
      `apply_theme_dict(load_theme_json(path))`; the demo has no JSON menu item), looks as in
      the Studio.
- [ ] In another app, `get_dock_style_manager().apply_theme_dict(load_theme_json(path))`
      gives the same look.
- [ ] `python -m lace.theme_kit audit <file>` exits 0.
- [ ] From a Lace app, `lace.theme_kit.studio.launch()` opens the Studio in its own process and
      the app's theme does not change.

## Sign-off

| Date | Tester | Notes |
|---|---|---|
|  |  |  |
