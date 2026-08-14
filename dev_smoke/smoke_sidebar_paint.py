"""Renders the sidebar auto-hide overlay offscreen and samples pixels to verify
its chrome (container bg + title bar) matches the resolved SIDEPANEL tokens.

Objective substitute for eyeballing a screenshot: grab() -> QImage -> pixelColor.
Run before and after the QSS->painted-chrome conversion; the visible result must
be identical (the container bg is mostly occluded by the title bar + content).
"""
import sys, logging
import os
# Run directly (python dev_smoke/<name>.py) and sys.path[0] is dev_smoke/,
# so the demos package below would not resolve. run_all.py sets PYTHONPATH
# instead, which is why this only ever broke on direct invocation.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
logging.disable(logging.CRITICAL)
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QSize
app = QApplication(sys.argv)

from PySide6.QtGui import QPalette, QColor
from demos.demo_app import DemoMainWindow
from lace.enums import DockWidgetArea
from lace.dock_theme import DockStyleCategory
from lace.dock_style_manager import get_dock_style_manager, apply_dock_theme

win = DemoMainWindow(); win.resize(1000, 700); win.show(); app.processEvents()
dm = win.dock_manager
side = dm.sidebar_manager
sm = get_dock_style_manager()


def sample(theme: str):
    apply_dock_theme(theme)
    dw = list(dm.dock_widgets_map().values())[0]
    if not side.is_pinned(dw):
        side.pin_widget(dw, area=DockWidgetArea.left)
    app.processEvents()
    overlay = side._overlay
    overlay.show_widget(dw, DockWidgetArea.left, animate=False, size=QSize(300, 500))
    app.processEvents()
    img = overlay.grab().toImage()
    tb = overlay._title_bar
    tb_h = tb.height()

    def px(x, y):
        c = img.pixelColor(x, y)
        return (c.red(), c.green(), c.blue())

    bg = sm.get(DockStyleCategory.SIDEPANEL, "bg_normal")
    exp = bg.getRgb()[:3] if bg else None
    # x=3 is left of the title label (padding_left=10) -> pure title-bar bg
    title_px = px(3, tb_h // 2)

    # Label text colour now comes from the palette (was hex QSS).
    tcol = sm.get(DockStyleCategory.SIDEPANEL, "title_text_color")
    exp_text = tcol.getRgb()[:3] if tcol else None
    lbl_pal = tb._title_label.palette().color(QPalette.WindowText).getRgb()[:3]

    # Scan the title-bar band for a rendered glyph pixel in the text colour,
    # proving the palette actually paints the label (not just set-and-ignored).
    text_rendered = False
    if exp_text is not None:
        for y in range(2, tb_h - 2):
            for x in range(8, min(img.width(), 140)):
                if all(abs(a - b) <= 6 for a, b in zip(px(x, y), exp_text)):
                    text_rendered = True
                    break
            if text_rendered:
                break

    result = {
        "overlay": (overlay.width(), overlay.height()),
        "title_px": title_px,
        "expected_bg": exp,
        "corner_px": px(2, 2),
        "lbl_pal": lbl_pal,
        "expected_text": exp_text,
        "text_rendered": text_rendered,
    }
    side.unpin_widget(dw)
    app.processEvents()
    return result


def sample_strip(theme: str):
    """Sample the always-visible SideTabBar strip: bg pixel + first-button pos."""
    apply_dock_theme(theme)
    dw = list(dm.dock_widgets_map().values())[0]
    if not side.is_pinned(dw):
        side.pin_widget(dw, area=DockWidgetArea.left)
    app.processEvents()
    bar = side._sidebars[DockWidgetArea.left]
    img = bar.grab().toImage()
    c = img.pixelColor(1, 1)
    bg = sm.get(DockStyleCategory.SIDEBAR, "bg_color")
    exp = bg.getRgb()[:3] if bg else None
    g = bar._scroll_area.geometry()   # content inset shifts if the border reserve changes
    res = {"strip": (bar.width(), bar.height()), "bg_px": (c.red(), c.green(), c.blue()),
           "expected": exp, "scroll_geo": (g.x(), g.y(), g.width(), g.height())}
    side.unpin_widget(dw)
    app.processEvents()
    return res


print("--- SideTabBar strip baseline ---")
for theme in ("default", "light", "monokai"):
    s = sample_strip(theme)
    print(f"[{theme}] strip={s['strip']} bg_px={s['bg_px']} expected={s['expected']} scroll_geo={s['scroll_geo']}")
    assert s["expected"] is not None
    for got, want in zip(s["bg_px"], s["expected"]):
        assert abs(got - want) <= 2, f"{theme}: strip bg {s['bg_px']} != {s['expected']}"
    # content inset must stay put (border reserve preserved)
    assert s["scroll_geo"] == (1, 1, s["strip"][0] - 2, s["strip"][1] - 2), f"{theme}: scroll geo shifted -> {s['scroll_geo']}"

def sample_decorations(theme: str):
    """Force the overflow counter badge + drop indicator visible and pixel-check
    them (both were hex QSS, now painted / palette)."""
    apply_dock_theme(theme)
    dw = list(dm.dock_widgets_map().values())[0]
    if not side.is_pinned(dw):
        side.pin_widget(dw, area=DockWidgetArea.left)
    app.processEvents()
    bar = side._sidebars[DockWidgetArea.left]

    # Counter badge
    bar._counter_lbl.setText("9")
    bar._counter_lbl.setFixedSize(24, 18)
    bar._counter_lbl.show()
    app.processEvents()
    cimg = bar._counter_lbl.grab().toImage()
    cc = cimg.pixelColor(5, cimg.height() // 2)          # left of the centred digit -> bg fill
    counter_bg = sm.get(DockStyleCategory.SIDEBAR, "tab_bg_hover_start")
    exp_cbg = counter_bg.getRgb()[:3] if counter_bg else None
    counter_text = sm.get(DockStyleCategory.SIDEBAR, "tab_text_normal")
    exp_ctext = counter_text.getRgb()[:3] if counter_text else None
    # Find the pure rendered text colour pixel inside the badge to avoid subpixel antialiasing edge misses
    if exp_ctext is not None:
        best_diff, best_px = min(
            (sum(abs(a - b) for a, b in zip(cimg.pixelColor(x, y).getRgb()[:3], exp_ctext)), cimg.pixelColor(x, y).getRgb()[:3])
            for y in range(cimg.height()) for x in range(cimg.width())
        )
        ct = QColor(*best_px)
    else:
        ct = cimg.pixelColor(cimg.width() // 2, cimg.height() // 2)

    # Drop indicator
    bar._show_drop_indicator()
    app.processEvents()
    dimg = bar._drop_indicator.grab().toImage()
    dc = dimg.pixelColor(1, dimg.height() // 2)
    ind = sm.get(DockStyleCategory.SIDEBAR, "indicator_color")
    exp_ind = ind.getRgb()[:3] if ind else None
    bar._hide_drop_indicator()

    res = {"counter_px": (cc.red(), cc.green(), cc.blue()), "exp_cbg": exp_cbg,
           "counter_text_px": (ct.red(), ct.green(), ct.blue()), "exp_ctext": exp_ctext,
           "drop_px": (dc.red(), dc.green(), dc.blue()), "exp_ind": exp_ind}
    side.unpin_widget(dw)
    app.processEvents()
    return res


def sample_buttons(theme: str):
    """ChromeToolButton: uniform sizing within [minimum, sizeHint] preserved,
    plus painted hover fill (forced flag)."""
    apply_dock_theme(theme)
    dw = list(dm.dock_widgets_map().values())[0]
    if not side.is_pinned(dw):
        side.pin_widget(dw, area=DockWidgetArea.left)
    app.processEvents()
    overlay = side._overlay
    overlay.show_widget(dw, DockWidgetArea.left, animate=False, size=QSize(300, 500))
    app.processEvents()
    title_bar = overlay._title_bar
    buttons = (title_bar._reattach_btn, title_bar._float_btn,
               title_bar._maximize_btn, title_bar._close_btn)
    btn = title_bar._close_btn
    size = (btn.width(), btn.height())
    size_hint = (btn.sizeHint().width(), btn.sizeHint().height())
    sizes = {(b.width(), b.height()) for b in buttons}

    # The CSS minimum the shared styler writes, read from the same tokens it
    # uses rather than hard-coded: this floor was pinned at 22 from a
    # "min-width 18" that the tokens have since moved off, so the check failed
    # on every theme for a size that was correct.
    min_box = (sm.get(DockStyleCategory.SIDEPANEL, "button_size", 17)
               + 2 * sm.get(DockStyleCategory.SIDEPANEL, "button_padding", 2))

    hb = sm.get(DockStyleCategory.SIDEPANEL, "button_hover_bg")
    exp_hb = hb.getRgb()[:3] if hb else None
    btn.set_hovered(True)
    app.processEvents()
    himg = btn.grab().toImage()
    hpx = himg.pixelColor(2, 2)          # corner: hover fill (radius is small)
    btn.setDown(True)                    # pressed state
    app.processEvents()
    pimg = btn.grab().toImage()
    ppx = pimg.pixelColor(2, 2)
    btn.setDown(False)
    btn.set_hovered(False)
    app.processEvents()
    nimg = btn.grab().toImage()
    npx = nimg.pixelColor(2, 2)          # corner: no fill -> not the hover colour

    res = {"size": size, "size_hint": size_hint, "sizes": sizes,
           "min_box": min_box,
           "hover_px": (hpx.red(), hpx.green(), hpx.blue()),
           "exp_hb": exp_hb, "idle_px": (npx.red(), npx.green(), npx.blue()),
           "pressed_px": (ppx.red(), ppx.green(), ppx.blue())}
    side.unpin_widget(dw)
    app.processEvents()
    return res


print("--- ChromeToolButton (size + painted hover) ---")
for theme in ("default", "light", "monokai"):
    b = sample_buttons(theme)
    print(f"[{theme}] size={b['size']} hint={b['size_hint']} sizes={b['sizes']} "
          f"hover={b['hover_px']}/{b['exp_hb']} "
          f"pressed={b['pressed_px']} idle={b['idle_px']}")
    # The shared styler must size every title-bar button identically (no button
    # is special-cased).  With 4 buttons + the title label the layout may
    # legitimately squeeze them toward their CSS minimum (button_size +
    # 2x button_padding), so assert uniform size within the declared
    # [minimum, sizeHint] range rather than a hard-coded snapshot.
    assert len(b["sizes"]) == 1, f"{theme}: buttons not uniformly sized -> {b['sizes']}"
    for got, hint in zip(b["size"], b["size_hint"]):
        assert b["min_box"] <= got <= hint + 1,             f"{theme}: button size {b['size']} outside [{b['min_box']}, hint+1]"
    for got, want in zip(b["hover_px"], b["exp_hb"]):
        assert abs(got - want) <= 2, f"{theme}: hover fill {b['hover_px']} != {b['exp_hb']}"
    # pressed reads distinctly from hover (translucent dark wash on top)
    pdist = sum(abs(a - c) for a, c in zip(b["pressed_px"], b["hover_px"]))
    assert pdist >= 15, f"{theme}: pressed {b['pressed_px']} ~ hover {b['hover_px']} (dist {pdist})"
    # fill appears only on hover: idle corner differs from the hover fill —
    # but only checkable when the hover colour differs from the transparent
    # grab background (black); monokai's hover resolves to black, so skip there.
    if max(b["exp_hb"]) > 8:
        assert tuple(b["idle_px"]) != tuple(b["exp_hb"]), f"{theme}: idle shows hover fill"

def check_vertical_tab():
    """VerticalTabButton bg/indicator go through the shared paint_tab now —
    verify the active indicator hugs the correct (mirrored) edge and the hover
    gradient runs start->end horizontally."""
    from lace.sidebar_tab import VerticalTabButton
    apply_dock_theme("default")
    hs = sm.get(DockStyleCategory.SIDEBAR, "tab_bg_hover_start").getRgb()[:3]
    he = sm.get(DockStyleCategory.SIDEBAR, "tab_bg_hover_end").getRgb()[:3]
    ind = sm.get(DockStyleCategory.SIDEBAR, "indicator_color").getRgb()[:3]

    def px(b, x, y):
        c = b.grab().toImage().pixelColor(x, y)
        return (c.red(), c.green(), c.blue())

    def mk(area, checked, hovered, pos):
        b = VerticalTabButton("Panel"); b.set_area(area)
        b.resize(30, 120); b.setChecked(checked); b._is_hovered = hovered
        b.refresh_style(); b._indicator_position = pos
        return b

    def near(a, b, tol=3):
        return all(abs(x - y) <= tol for x, y in zip(a, b))

    # active, left sidebar, pos "left" -> indicator on LEFT edge (solid)
    b = mk(DockWidgetArea.left, True, False, "left")
    assert px(b, 1, 60) == ind, f"left/left indicator {px(b,1,60)} != {ind}"
    # active, right sidebar, pos "left" -> mirrored to RIGHT edge
    b = mk(DockWidgetArea.right, True, False, "left")
    assert px(b, b.grab().width() - 2, 60) == ind, f"right/left indicator {px(b,b.grab().width() - 2,60)} != {ind}"
    # hover -> horizontal gradient start(left) .. end(right); ~1 off the pure
    # endpoints one pixel in, so allow a small tolerance.
    b = mk(DockWidgetArea.left, False, True, "left")
    assert near(px(b, 1, 60), hs), f"hover start {px(b,1,60)} != {hs}"
    assert near(px(b, b.grab().width() - 2, 60), he), f"hover end {px(b,b.grab().width() - 2,60)} != {he}"


check_vertical_tab()
print("VERTICAL TAB OK")


def check_vertical_tab_shape():
    """The tab's flat edge mirrors with the bar, and the outline either closes
    across that edge or leaves it open.

    Rendered on the real platform rather than offscreen: this is antialiased
    corner and stroke geometry, and the two backends round it differently.
    Corners are read by alpha — nothing else paints the button, so a square one
    comes back covered and a rounded one untouched.
    """
    from PySide6.QtCore import QPoint
    from PySide6.QtGui import QImage, QRegion
    from PySide6.QtWidgets import QWidget
    from lace.dock_theme import ThemeSpec, build_theme
    from lace.sidebar_tab import VerticalTabButton

    W, H = 30, 120

    def theme(**kw):
        sm.apply_theme_dict(build_theme(ThemeSpec(
            base=[20, 20, 30, 255], accent=[255, 100, 180, 255],
            text=[240, 240, 250, 255], tab_radius=6,
            # The strip defaults to the accent on the content-facing edge —
            # the same colour and pixels the active tab's outline would use.
            sidebar_indicator_width=0, **kw)))

    def mk(area=DockWidgetArea.left, checked=True):
        b = VerticalTabButton("Panel"); b.set_area(area)
        b.resize(W, H); b.setChecked(checked); b._is_hovered = False
        b.refresh_style()
        return b

    def render(b):
        img = QImage(b.size(), QImage.Format_ARGB32); img.fill(0)
        # DrawChildren only: the default flags paint the palette background
        # over the whole rect first and every corner comes back opaque.
        b.render(img, QPoint(), QRegion(), QWidget.RenderFlag.DrawChildren)
        return img

    def rounded(b):
        img = render(b)
        w, h = b.width() - 1, b.height() - 1
        return {n for n, (x, y) in (("tl", (0, 0)), ("tr", (w, 0)),
                                    ("br", (w, h)), ("bl", (0, h)))
                if img.pixelColor(x, y).alpha() == 0}

    def inked(b):
        on = render(b)
        saved, b._border_width = b._border_width, 0.0
        try:
            off = render(b)
        finally:
            b._border_width = saved
        xs, ys = range(W // 3, W - W // 3), range(H // 3, H - H // 3)
        edges = {"left": [(0, y) for y in ys], "right": [(W - 1, y) for y in ys],
                 "top": [(x, 0) for x in xs], "bottom": [(x, H - 1) for x in xs]}
        return {n for n, pts in edges.items()
                if any(on.pixelColor(x, y) != off.pixelColor(x, y) for x, y in pts)}

    theme()
    assert not rounded(mk()), "the default sidebar tab is no longer a rectangle"

    theme(sidebar_tab_flat_edge="outward")
    assert rounded(mk(DockWidgetArea.left)) == {"tr", "br"}, "left bar, outward"
    assert rounded(mk(DockWidgetArea.right)) == {"tl", "bl"}, "right bar, outward"

    theme(sidebar_tab_flat_edge="inward")
    assert rounded(mk(DockWidgetArea.left)) == {"tl", "bl"}, "left bar, inward"

    theme(sidebar_tab_flat_edge="none")
    assert rounded(mk()) == {"tl", "tr", "br", "bl"}, "all four corners rounded"

    theme(sidebar_tab_flat_edge="outward", sidebar_tab_border_width=2.0)
    assert inked(mk()) == {"top", "right", "bottom"}, "the flat edge is not open"

    theme(sidebar_tab_flat_edge="outward", sidebar_tab_border_width=2.0,
          sidebar_tab_border_closed=True)
    assert inked(mk()) == {"left", "top", "right", "bottom"}, "outline not closed"

    apply_dock_theme("default")


check_vertical_tab_shape()
print("VERTICAL TAB SHAPE OK")

print("--- SideTabBar decorations (counter + drop indicator) ---")
for theme in ("default", "light", "monokai"):
    d = sample_decorations(theme)
    print(f"[{theme}] counter_bg={d['counter_px']}/{d['exp_cbg']} "
          f"counter_text={d['counter_text_px']}/{d['exp_ctext']} "
          f"drop={d['drop_px']}/{d['exp_ind']}")
    for got, want in zip(d["counter_px"], d["exp_cbg"]):
        assert abs(got - want) <= 3, f"{theme}: counter bg {d['counter_px']} != {d['exp_cbg']}"
    for got, want in zip(d["counter_text_px"], d["exp_ctext"]):
        assert abs(got - want) <= 6, f"{theme}: counter text {d['counter_text_px']} != {d['exp_ctext']}"
    for got, want in zip(d["drop_px"], d["exp_ind"]):
        assert abs(got - want) <= 2, f"{theme}: drop {d['drop_px']} != {d['exp_ind']}"

print("--- Overlay ---")
for theme in ("default", "light", "monokai"):
    r = sample(theme)
    print(f"[{theme}] overlay={r['overlay']} title_px={r['title_px']} "
          f"expected_bg={r['expected_bg']} lbl_pal={r['lbl_pal']} "
          f"expected_text={r['expected_text']} text_rendered={r['text_rendered']}")
    # title-bar background must match the resolved SIDEPANEL bg token (±2 for AA/rounding)
    assert r["expected_bg"] is not None, f"{theme}: no bg token"
    for got, want in zip(r["title_px"], r["expected_bg"]):
        assert abs(got - want) <= 2, f"{theme}: title_px {r['title_px']} != bg {r['expected_bg']}"
    # label palette carries the resolved title-text token, and it actually renders
    if r["expected_text"] is not None:
        for got, want in zip(r["lbl_pal"], r["expected_text"]):
            assert abs(got - want) <= 2, f"{theme}: lbl_pal {r['lbl_pal']} != {r['expected_text']}"
        assert r["text_rendered"], f"{theme}: no glyph pixel in title colour {r['expected_text']}"

print("SIDEBAR PAINT OK")
