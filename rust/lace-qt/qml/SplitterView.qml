import QtQuick

import com.lace.dock 1.0

// A splitter node with a fully manual proportional layout.
//
// Qt's SplitView refuses to distribute dynamically added children (added via
// addItem they freeze at their implicit size; fill/preferred attached
// properties never engage — probed exhaustively). So this is a plain Item:
// children are parented directly and positioned imperatively from `shares`
// weights. Both axes run the same code path, so horizontal and vertical
// splits behave identically. Drag handles resize neighbours live.
Item {
    id: splitter
    property int splitOrientation: Qt.Horizontal
    property string nodePath: ""
    // Parallel arrays: boxes[i] owns shares[i] weight units.
    property var boxes: []
    property var shares: []
    property int handlePx: Math.max(3, LaceTheme.num("splitter.total_width") || 7)
    property int minPx: 60

    onWidthChanged: relayout()
    onHeightChanged: relayout()

    function setShares(s) {
        shares = s.slice()
        relayout()
    }

    function addBox(item, share) {
        boxes.push(item)
        shares.push((typeof share === "number" && share > 0) ? share : 1)
        boxes = boxes
        shares = shares
        item.parent = splitter
        ensureHandles()
        relayout()
    }

    function clearBoxes() {
        for (var i = boxes.length - 1; i >= 0; --i)
            boxes[i].destroy()
        for (var h = handles.length - 1; h >= 0; --h)
            handles[h].destroy()
        boxes = []
        shares = []
        handles = []
    }

    property var handles: []

    function ensureHandles() {
        var want = Math.max(0, boxes.length - 1)
        while (handles.length < want) {
            var idx = handles.length
            var h = handleComp.createObject(splitter, { handleIndex: idx })
            handles.push(h)
        }
        handles = handles
        for (var i = 0; i < handles.length; ++i)
            handles[i].visible = i < want
    }

    function visibleBoxes() {
        var out = []
        for (var i = 0; i < boxes.length; ++i) {
            if (boxes[i].visible !== false)
                out.push(i)
        }
        return out
    }

    function relayout() {
        if (boxes.length === 0)
            return
        // Handles show only between visible boxes (maximize hides the
        // rest): reset all, then enable exactly the positioned ones.
        for (var hz = 0; hz < handles.length; ++hz)
            handles[hz].visible = false
        var horiz = splitOrientation === Qt.Horizontal
        var span = horiz ? width : height
        var vis = visibleBoxes()
        if (vis.length === 0 || span <= 0)
            return
        var total = 0
        for (var v = 0; v < vis.length; ++v)
            total += Math.max(0.0001, shares[vis[v]])
        var gaps = (vis.length - 1) * handlePx
        var avail = Math.max(0, span - gaps)
        var acc = 0
        for (var k = 0; k < vis.length; ++k) {
            var bi = vis[k]
            var px = (k === vis.length - 1)
                ? Math.max(0, avail - acc)
                : Math.round(avail * Math.max(0.0001, shares[bi]) / total)
            var box = boxes[bi]
            if (horiz) {
                box.x = acc
                box.y = 0
                box.width = px
                box.height = height
            } else {
                box.x = 0
                box.y = acc
                box.width = width
                box.height = px
            }
            if (k < vis.length - 1 && handles[k]) {
                var hh = handles[k]
                hh.visible = true
                if (horiz) {
                    hh.x = acc + px
                    hh.y = 0
                    hh.width = handlePx
                    hh.height = height
                } else {
                    hh.x = 0
                    hh.y = acc + px
                    hh.width = width
                    hh.height = handlePx
                }
            }
            acc += px + handlePx
        }
    }

    // Live drag scale for handle drags (recomputed per gesture).
    property var dragState: null

    Component {
        id: handleComp
        Rectangle {
            property int handleIndex: 0
            color: handleHover.hovered
                ? (LaceTheme.color("splitter.handle_hover_color") || "grey")
                : (LaceTheme.color("splitter.handle_color") || "darkgrey")
            HoverHandler {
                id: handleHover
            }
            MouseArea {
                anchors.fill: parent
                cursorShape: splitter.splitOrientation === Qt.Horizontal
                    ? Qt.SplitHCursor : Qt.SplitVCursor
                acceptedButtons: Qt.LeftButton
                onPressed: function(mouse) {
                    var horiz = splitter.splitOrientation === Qt.Horizontal
                    var span = horiz ? splitter.width : splitter.height
                    var vis = splitter.visibleBoxes()
                    // Locate this handle among the visible gaps.
                    var pos = -1
                    for (var g = 0; g < vis.length - 1; ++g) {
                        if (vis[g] === handleIndex) {
                            pos = g
                            break
                        }
                    }
                    if (pos < 0)
                        return
                    splitter.dragState = {
                        left: vis[pos],
                        right: vis[pos + 1],
                        start: horiz ? mouse.x : mouse.y,
                        total: (function() {
                            var t = 0
                            for (var v = 0; v < vis.length; ++v)
                                t += Math.max(0.0001, splitter.shares[vis[v]])
                            return t
                        })(),
                        avail: Math.max(1, span - (vis.length - 1) * splitter.handlePx),
                        vis: vis
                    }
                    mouse.accepted = true
                }
                onPositionChanged: function(mouse) {
                    var st = splitter.dragState
                    if (!st)
                        return
                    var horiz = splitter.splitOrientation === Qt.Horizontal
                    var now = horiz ? mouse.x : mouse.y
                    var dPx = now - st.start
                    var dShare = dPx * st.total / st.avail
                    var next = splitter.shares.slice()
                    var a = Math.max(0.0001, st.left >= 0 ? next[st.left] : 1)
                    var b = Math.max(0.0001, st.right >= 0 ? next[st.right] : 1)
                    // Clamp so neither side drops below minPx.
                    var minShare = splitter.minPx * st.total / st.avail
                    var lo = minShare - a
                    var hi = b - minShare
                    if (hi < lo)
                        return
                    var clamped = Math.max(lo, Math.min(hi, dShare))
                    next[st.left] = a + clamped
                    next[st.right] = b - clamped
                    splitter.shares = next
                    splitter.relayout()
                    mouse.accepted = true
                }
                onReleased: function(mouse) {
                    if (splitter.dragState && splitter.afterDrag)
                        splitter.afterDrag(splitter.shares.slice())
                    splitter.dragState = null
                    mouse.accepted = true
                }
            }
        }
    }

    // Called with the final shares when a handle drag ends; the builder
    // wires it to persist sizes back into the layout doc (silent, no rebuild).
    property var afterDrag: null
}
