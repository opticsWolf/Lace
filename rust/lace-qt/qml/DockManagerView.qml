import QtQuick

import com.lace.dock 1.0

// Renders the main container of the manager's layout snapshot and owns the
// floating windows. Rebuilds everything on `layoutJsonChanged`; per-tab
// current switches are silent (see LaceManager.setCurrentTab) so tab-local
// state such as typed text survives them.
Item {
    id: view
    required property var manager
    property var doc: null
    property var floats: []
    // Last rebuild tally, for the headless smoke self-test.
    property var lastCounts: ({ areas: 0, widgets: 0, floats: 0 })
    // Node registry for maximize + the main container's index.
    property var nodeRegistry: []
    property int mainIndex: 0

    ContainerBuilder {
        id: builder
        manager: view.manager
        docksView: view
    }

    Item {
        id: mainArea
        anchors.fill: parent
    }

    // Result preview for the hovered drop (rubber band). While a move-drag
    // runs, hoverMove keeps this on the exact rect the widget would take.
    property rect dropPreview: Qt.rect(0, 0, 0, 0)
    property bool dropPreviewValid: false
    // Dragged widget name (drives the follow ghost) + current hit.
    property string dragName: ""
    property var currentHit: null
    property rect hoverAreaRect: Qt.rect(0, 0, 0, 0)

    function zoneKey(kind, container, path, edge) {
        return kind === "C"
            ? ("C:" + container + "/" + edge)
            : ("S:" + container + "/" + path + "/" + edge)
    }

    // Areas of the main container in view coordinates (manual layout sets
    // explicit x/y/width/height, so climbing parents is exact).
    function mainAreaRects() {
        var out = []
        for (var e of nodeRegistry) {
            var item = e.item
            if (!item || item.areaPath === undefined)
                continue
            var parts = String(e.key).split("/")
            if (parts[0] !== String(mainIndex))
                continue
            var x = item.x, y = item.y, p = item.parent
            while (p && p !== mainArea && p !== view) {
                x += p.x
                y += p.y
                p = p.parent
            }
            out.push({
                container: mainIndex,
                path: parts.slice(1).join("/"),
                rect: Qt.rect(x, y, item.width, item.height)
            })
        }
        return out
    }

    function allowedEdges(container) {
        try {
            return String(manager.dropEdges(container)).split(",")
        } catch (e) {
            return []
        }
    }

    // Geometric hit test in view coordinates. Container rim zones win over
    // area zones (mirrors the old overlay stacking); area edges are 56px
    // bands, the rest is center. Returns null when nothing is droppable.
    function hitTest(vx, vy) {
        if (vx < 0 || vy < 0 || vx > width || vy > height)
            return null
        var rim = 72
        var edges = allowedEdges(mainIndex)
        var at = function(edge) { return edges.indexOf(edge) >= 0 }
        if (vx < rim && at("left"))
            return { kind: "C", container: mainIndex, path: "", edge: "left" }
        if (vx > width - rim && at("right"))
            return { kind: "C", container: mainIndex, path: "", edge: "right" }
        if (vy < rim && at("top"))
            return { kind: "C", container: mainIndex, path: "", edge: "top" }
        if (vy > height - rim && at("bottom"))
            return { kind: "C", container: mainIndex, path: "", edge: "bottom" }
        var band = 56
        var areas = mainAreaRects()
        for (var a of areas) {
            var r = a.rect
            if (vx < r.x || vy < r.y || vx > r.x + r.width || vy > r.y + r.height)
                continue
            var lx = vx - r.x, ty = vy - r.y
            var rx = r.x + r.width - vx, by = r.y + r.height - vy
            var m = Math.min(lx, ty, rx, by)
            var edge = "center"
            if (m < band) {
                if (m === lx) edge = "left"
                else if (m === ty) edge = "top"
                else if (m === rx) edge = "right"
                else edge = "bottom"
            }
            if (edges.indexOf(edge) < 0)
                return null
            return { kind: "S", container: a.container, path: a.path, edge: edge }
        }
        if (at("center"))
            return { kind: "C", container: mainIndex, path: "", edge: "center" }
        return null
    }

    function previewRectFor(hit) {
        if (!hit)
            return Qt.rect(0, 0, 0, 0)
        if (hit.kind === "C") {
            var third = hit.edge === "left" || hit.edge === "right"
                ? Math.round(width / 3) : Math.round(height / 3)
            if (hit.edge === "left") return Qt.rect(0, 0, third, height)
            if (hit.edge === "right") return Qt.rect(width - third, 0, third, height)
            if (hit.edge === "top") return Qt.rect(0, 0, width, third)
            if (hit.edge === "bottom") return Qt.rect(0, height - third, width, third)
            return Qt.rect(0, 0, width, height)
        }
        var areas = mainAreaRects()
        for (var a of areas) {
            if (a.container === hit.container && a.path === hit.path) {
                var r = a.rect
                var hw = Math.round(r.width / 2), hh = Math.round(r.height / 2)
                if (hit.edge === "left") return Qt.rect(r.x, r.y, hw, r.height)
                if (hit.edge === "right") return Qt.rect(r.x + hw, r.y, r.width - hw, r.height)
                if (hit.edge === "top") return Qt.rect(r.x, r.y, r.width, hh)
                if (hit.edge === "bottom") return Qt.rect(r.x, r.y + hh, r.width, r.height - hh)
                return r
            }
        }
        return Qt.rect(0, 0, 0, 0)
    }

    // Called by the title/tab sensors while a move-drag runs. Updates the
    // manager hover (drives zone highlights), the result preview, the
    // cross anchor and the follow ghost.
    function hoverMove(vx, vy) {
        moveGhost(vx, vy)
        var hit = hitTest(vx, vy)
        currentHit = hit
        if (!hit) {
            hoverAreaRect = Qt.rect(0, 0, width, height)
            manager.clearDragTarget()
            dropPreviewValid = false
            return null
        }
        var ok
        if (hit.kind === "C") {
            hoverAreaRect = Qt.rect(0, 0, width, height)
            ok = manager.overContainerDrop(hit.container, hit.edge)
        } else {
            hoverAreaRect = areaRectOf(hit.container, hit.path)
            ok = manager.overSectionDrop(hit.container, hit.path, hit.edge)
        }
        if (!ok) {
            dropPreviewValid = false
            return null
        }
        dropPreview = previewRectFor(hit)
        dropPreviewValid = true
        return hit
    }

    function areaRectOf(container, path) {
        var areas = mainAreaRects()
        for (var a of areas) {
            if (a.container === container && a.path === path)
                return a.rect
        }
        return Qt.rect(0, 0, width, height)
    }

    // Follow ghost: a small live rendering of the dragged widget under
    // the cursor (global coords = hosting window origin + view point).
    function moveGhost(vx, vy) {
        if (dragName === "" || !ghost.visible)
            return
        var host = view.Window.window
        if (!host)
            return
        ghost.x = Math.round(host.x + vx - ghost.width / 2)
        ghost.y = Math.round(host.y + vy - 24)
    }

    function clearHover() {
        manager.clearDragTarget()
        dropPreviewValid = false
        dragName = ""
        currentHit = null
    }

    // Follow ghost: live rendering of the dragged widget under the cursor.
    // A tool window (no taskbar entry, no activation) driven by hoverMove.
    Window {
        id: ghost
        flags: Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
        visible: view.manager.dragActive && view.dragName !== ""
        width: 340
        height: 220
        opacity: 0.92
        color: "transparent"
        Rectangle {
            anchors.fill: parent
            color: LaceTheme.color("panel.bg_normal") || "#2a2a2a"
            border.color: LaceTheme.color("overlay.frame_color") || "blue"
            border.width: 2
            radius: LaceTheme.num("core.corner_radius") || 0
        }
        WidgetCard {
            anchors.fill: parent
            anchors.margins: 8
            manager: view.manager
            widgetName: view.dragName
            widgetClosed: false
            enabled: false
        }
    }

    function refresh() {
        try {
            doc = JSON.parse(manager.layoutJson)
        } catch (e) {
            console.warn("lace dock: layout snapshot did not parse: " + e)
            return
        }
        rebuild()
    }

    function clearChildren(item) {
        for (var i = item.children.length - 1; i >= 0; --i)
            item.children[i].destroy()
    }

    // Reconcile float windows with the document by container id: windows
    // whose container survives are kept (no flicker, no close storms) and
    // asked to refresh their own tree; removed ones are torn down with the
    // guard set so their onClosing does NOT dock anything back.
    // (Unconditional destroy used to close every float on every rebuild —
    // the close handler then docked each float back, so floats could never
    // survive a structural op and lastError filled with stale failures.)
    function syncFloats() {
        var wanted = {}
        for (var c = 0; c < doc.containers.length; ++c) {
            if (!doc.containers[c].is_main)
                wanted[doc.containers[c].id || ("float-" + c)] = c
        }
        var keep = []
        for (var w of floats) {
            if (w && wanted[w.cid] !== undefined) {
                keep.push(w)
                delete wanted[w.cid]
            } else if (w) {
                w.teardown = true
                w.close()
                w.destroy()
            }
        }
        floats = keep
        for (var cid in wanted) {
            var win = builder.floatComp.createObject(null, {
                manager: view.manager,
                doc: view.doc,
                containerIndex: wanted[cid],
                builder: builder,
                cid: cid
            })
            if (win)
                floats.push(win)
        }
        floats = floats
        for (var k of floats) {
            if (k.refreshContent)
                k.refreshContent()
        }
        return floats.length
    }

    function rebuild() {
        clearChildren(mainArea)
        view.nodeRegistry = []
        if (!doc || !doc.containers)
            return
        var counts = { areas: 0, widgets: 0, floats: 0 }
        for (var c = 0; c < doc.containers.length; ++c) {
            var container = doc.containers[c]
            if (container.is_main) {
                view.mainIndex = c
                var rootItem = builder.buildNode(mainArea, container.data.root_splitter, c, "", counts, view.nodeRegistry)
                // Plain Items don't lay out children: the root fills manually
                // (nested items are positioned by the manual SplitterView).
                if (rootItem)
                    rootItem.anchors.fill = mainArea
            }
        }
        counts.floats = syncFloats()
        console.log("lace dock: areas=" + counts.areas
            + " widgets=" + counts.widgets + " floats=" + counts.floats)
        view.lastCounts = counts
        builder.applyMaximize(view.nodeRegistry, manager.maximizedArea, view.mainIndex)
    }

    OverlayCross {
        manager: view.manager
        mainIndex: view.mainIndex
        hoverRect: view.hoverAreaRect
        activeEdge: view.currentHit ? view.currentHit.edge : ""
        allowedEdges: view.dragActive ? allowedEdges(mainIndex) : ["left", "right", "top", "bottom", "center"]
        containerMode: view.currentHit ? view.currentHit.kind === "C" : false
    }

    // Rubber band: the exact rect a release would dock into.
    Rectangle {
        x: view.dropPreview.x
        y: view.dropPreview.y
        width: view.dropPreview.width
        height: view.dropPreview.height
        z: 30
        visible: view.manager.dragActive && view.dropPreviewValid
        color: LaceTheme.color("overlay.overlay_color") || "transparent"
        border.color: LaceTheme.color("overlay.frame_color") || "blue"
        border.width: 3
    }

    Component.onCompleted: refresh()

    Connections {
        target: view.manager
        function onLayoutJsonChanged() { view.refresh() }
        function onMaximizedAreaChanged() {
            builder.applyMaximize(view.nodeRegistry, view.manager.maximizedArea, view.mainIndex)
        }
    }
}
