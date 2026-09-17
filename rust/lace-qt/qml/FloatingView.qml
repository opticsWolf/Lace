import QtQuick

// Tier-0 floating container: a plain OS-framed Window (custom chrome is a
// Phase-7 concern). Geometry comes from the layout's container_geometries
// copy; closing the window docks the container back into the main view.
Window {
    id: win
    required property var manager
    required property var doc
    required property int containerIndex
    required property string cid
    required property var builder

    title: "Lace float: " + cid
    width: 480
    height: 360
    visible: true

    Item {
        id: content
        anchors.fill: parent
    }

    property var nodeRegistry: []

    function applyMax() {
        builder.applyMaximize(nodeRegistry, manager.maximizedArea, containerIndex)
    }

    Component.onCompleted: {
        var g = (doc.container_geometries || {})[cid]
        if (g) {
            win.x = g.x
            win.y = g.y
            win.width = g.width
            win.height = g.height
        }
        nodeRegistry = []
        var counts = { areas: 0, widgets: 0, floats: 0 }
        var rootItem = builder.buildNode(content, doc.containers[containerIndex].data.root_splitter,
            containerIndex, "", counts, nodeRegistry)
        if (rootItem)
            rootItem.anchors.fill = content
        applyMax()
    }

    Connections {
        target: manager
        function onMaximizedAreaChanged() { applyMax() }
    }

    onClosing: function(close) {
        manager.dockFloating(cid)
    }
}
