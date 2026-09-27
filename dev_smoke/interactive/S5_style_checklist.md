# Session S5 Checklist — LaceStyle (Phase 4)

**Goal:** Check by hand what the gallery and `smoke_lace_style.py` can't:
real hover, press, focus and keyboard navigation for every LaceStyle family,
live token switching, and sharpness on a zoomed canvas.

No trace log for this session: sign it off by ticking the boxes and noting
the theme(s) and date at the bottom.

## Setup

```powershell
python dev_smoke/interactive/style_showcase.py kilim_dark
python dev_smoke/interactive/style_showcase.py kilim_light_neo
python dev_smoke/interactive/style_showcase.py kilim_dark --zoom
python -m demos.demo_app
```

Run sections 1–7 in the showcase under **both** `kilim_dark` and
`kilim_light_neo`; section 8 in the `--zoom` window; section 9 in the demo.

## 1. Buttons (4b-1)
- [ ] **Hover / press:** Push, Toggle, and the non-flat tool buttons step
      lighter on hover and further on press; no gradient, no bevel.
- [ ] **Default button:** accent fill; its label stays readable at rest,
      hover and press.
- [ ] **Flat / auto-raise:** no face at rest; a face appears on hover and press.
- [ ] **Toggle:** checked shows the accent wash with an accent outline;
      clicking again returns it to the plain face.
- [ ] **Split tool button:** the arrow has air on both sides, the divider line
      sits between the two halves; the menu half opens the menu.
- [ ] **Keyboard focus:** Tab onto each button: an accent ring *inside* the
      face; a mouse click leaves no ring.
- [ ] **Disabled:** "Disabled" is muted but its outline is still visible.

## 2. Inputs (4b-2)
- [ ] **Line edit:** flat Base field; the outline turns accent while focused
      (mouse or keyboard).
- [ ] **Combo:** chevron inside the field; the editable combo's arrow area
      tints on hover and press, reaching the field edge with no gap.
- [ ] **Spin boxes:** up/down chevrons and the plus/minus variant; each step
      area tints on hover and press; at the maximum the up glyph is dimmed.
- [ ] **NoButtons spin box:** plain field only.
- [ ] **Keyboard:** Tab through the fields; arrow keys step the spin boxes;
      the focused field alone shows the accent outline.
- [ ] **Disabled / read-only:** the disabled edit is muted with a visible
      outline; the read-only edit looks like a field, not a label.

## 3. Checks
- [ ] **Check box:** hover turns the outline accent; checked is an accent fill
      with a crisp tick; partial is an accent wash with a dash.
- [ ] **Radio:** hover outline accent; selected is an accent ring and dot.
- [ ] **Space bar:** toggles the focused box / radio; the focus ring shows
      around the indicator only after keyboard navigation.
- [ ] **Disabled:** box and radio outlines muted but visible.

## 4. Range (4b-3)
- [ ] **Slider:** groove accent up to the round knob; the knob steps on hover
      and press; dragging and arrow keys both move it.
- [ ] **Ticks:** flat tick marks line up with the knob's centre at each step.
- [ ] **Disabled slider:** muted accent fill, distinct from the track.
- [ ] **Progress:** rounded track and fill; the text stays readable.
- [ ] **Busy progress:** a segment slides smoothly along the track.

## 5. Containers (4b-4)
- [ ] **Tabs:** bare at rest, a wash on hover, the selected tab filled with an
      accent underline on the pane side — check the North, South and West tab
      widgets. The disabled "Off" tab is muted and can't be selected.
- [ ] **Tab keyboard focus:** Tab onto a tab bar: an accent ring inside the
      focused tab, no tinted box; arrow keys switch tabs.
- [ ] **Group boxes:** rounded 1 px frames with the title legible.
- [ ] **Header:** flat sections with separators; click "Name" to sort — the
      vector chevron flips direction; hover and press step the section.
- [ ] **Table / tree selection:** flat highlight, square rows joining across
      columns; hover shows a faint wash; the tree's item checks match section 3.
- [ ] **Tree branches:** vector chevrons, open and shut.
- [ ] **Tool box:** rounded page tabs; hover steps them; clicking switches page.

## 6. Menus and tooltips
- [ ] **Menu bar:** hovering "File" / "Style" shows a rounded highlight;
      clicking opens the menu with the highlight kept.
- [ ] **Menu items:** rounded highlight inset from the popup edge; "Save" is
      disabled; separators are flat lines; "Wrap lines" shows a bare tick
      (no box); "Recent" shows a vector submenu arrow.
- [ ] **Style menu radios:** exclusive choices show a dot, not a radio circle.
- [ ] **Keyboard:** Alt+F opens File; arrows move the highlight; Esc closes.
- [ ] **Tooltip:** hover the table: rounded corners with no square corners
      showing behind them, a 1 px outline, readable text.

## 7. Live tokens (Style menu)
- [ ] **Scrollbar → thin / expanding / fusion:** thin bars with no arrows;
      expanding bars grow under the mouse and show triangle arrows; fusion is
      stock Fusion. Layouts adjust without leftovers.
- [ ] **Contrast → low / normal / high:** outlines, focus ring and scrollbar
      handle get stronger with each level.
- [ ] **Radius → 0 / 2 / 4 / 8:** buttons, fields, frames and tooltips follow;
      check boxes stay square at 0 and never turn round at 8.

## 8. Zoom (`--zoom`; Weave canvas if available)
- [ ] **Keys 1 / 2 / 4:** at 100 %, 200 % and 400 % every glyph — chevrons,
      ticks, dashes, radio dots, branch arrows, scrollbar arrows — stays sharp
      with no pixel stair-steps or blur.
- [ ] **Interaction when zoomed:** hover and click still land on the right
      control (combo opens, slider drags, spin box steps).
- [ ] **Weave:** place a node with every family at 100 / 200 / 400 %; the same
      holds on the real canvas.

## 9. Demo app
- [ ] **Theme switching:** switch through several themes from the demo's
      menu; controls repaint without stale colours.
- [ ] **Docking chrome** is unchanged from 0.7.6 apart from the controls
      inside the docks.

---

| Theme | Date | Signed off by | Notes |
|---|---|---|---|
| kilim_dark | | | |
| kilim_light_neo | | | |
