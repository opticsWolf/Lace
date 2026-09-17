import QtQuick

// Tier-0 floating container: a plain OS-framed Window (custom chrome is a
// Phase-7 concern). Geometry comes from the layout's container_geometries
// copy; closing the window docks the container back into the main view.
//
// Lifetime vs the main rebuild: DockManagerView keeps this window alive
// across rebuilds while its container id survives (see syncFloats) and only
// destroys it for real removals. `teardown` distinguishes the two: a close
// that comes from rebuild teardown must NOT dock the container back — only
// genuine user closes do. The container is always resolved by `cid` (never
// by index: container order shifts as floats come and go).
Window {
    id: win
    required property var manager
    required property var doc
    required property int containerIndex
    required property string cid
    required property var builder

    // Set by the owner before close/destroy during rebuild teardown.
    property bool teardown: false

    title: "Lace float: " + cid
    width: 480
    height: 360
    visible: true

    Item {
        id: content
        anchors.fill: parent
    }

    property var nodeRegistry: []

    function liveDoc() {
        try {
            return JSON.parse(manager.layoutJson)
        } catch (e) {
            return null
        }
    }

    function ownIndex(live) {
        if (!live || !live.containers)
            return -1
        for (var c = 0; c < live.containers.length; ++c) {
            var id = live.containers[c].id || ("float-" + c)
            if (!live.containers[c].is_main && id === win.cid)
                return c
        }
        return -1
    }

    function applyMax() {
        var idx = ownIndex(liveDoc())
        if (idx >= 0)
            builder.applyMaximize(nodeRegistry, manager.maximizedArea, idx)
    }

    function buildFrom(live, index) {
        for (var i = content.children.length - 1; i >= 0; --i)
            content.children[i].destroy()
        nodeRegistry = []
        var counts = { areas: 0, widgets: 0, floats: 0 }
        var rootItem = builder.buildNode(content,
            live.containers[index].data.root_splitter,
            index, "", counts, nodeRegistry)
        if (rootItem)
            rootItem.anchors.fill = content
        applyMax()
    }

    // Rebuild the float's own tree after the document reshaped (called by
    // the owner for windows that survive a main rebuild).
    function refreshContent() {
        var live = liveDoc()
        var index = ownIndex(live)
        if (index < 0)
            return
        buildFrom(live, index)
    }

    Component.onCompleted: {
        var g = (doc.container_geometries || {})[cid]
        if (g) {
            win.x = g.x
            win.y = g.y
            win.width = g.width
            win.height = g.height
        }
        var live = liveDoc() || doc
        var index = ownIndex(live)
        if (index < 0)
            index = containerIndex
        buildFrom(live, index)
    }

    Connections {
        target: manager
        function onMaximizedAreaChanged() { applyMax() }
    }

    onClosing: function(close) {
        if (!win.teardown)
            manager.dockFloating(cid)
    }
}
