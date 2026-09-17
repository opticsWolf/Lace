import QtQuick
import QtQuick.Controls

import com.lace.dock 1.0

// Auto-hide sidebar strip for one window edge. Lists the pinned widgets for
// `side`; clicking a tab docks it back into the main container (the overlay
// panel itself is a Phase-5 concern).
Item {
    id: strip
    required property var manager
    required property string side

    property var pinned: []

    function refresh() {
        try {
            var doc = JSON.parse(manager.layoutJson)
            var map = ((doc.sidebars || {}).pinned_widgets) || {}
            var names = []
            for (var name in map) {
                if (map[name] === side)
                    names.push(name)
            }
            names.sort()
            pinned = names
        } catch (e) {
            pinned = []
        }
    }

    Component.onCompleted: refresh()

    Connections {
        target: strip.manager
        function onLayoutJsonChanged() { strip.refresh() }
    }

    Rectangle {
        anchors.fill: parent
        color: LaceTheme.color("sidebar.bg_color") || "transparent"
        border.color: LaceTheme.color("sidebar.border_color") || "transparent"
        border.width: LaceTheme.num("sidebar.border_width") || 0
    }

    Column {
        anchors.fill: parent
        anchors.margins: 2
        spacing: 2

        Repeater {
            model: strip.pinned
            Button {
                required property string modelData
                width: strip.width - 4
                height: 96
                hoverEnabled: true
                contentItem: Text {
                    text: modelData
                    rotation: -90
                    anchors.centerIn: parent
                    color: LaceTheme.color("sidebar.tab_text_normal") || "white"
                    elide: Text.ElideRight
                    width: 88
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                background: Rectangle {
                    color: parent.hovered
                        ? (LaceTheme.color("sidebar.tab_bg_hover_start") || "grey")
                        : "transparent"
                    border.color: LaceTheme.color("sidebar.tab_border_normal_color") || "transparent"
                    border.width: LaceTheme.num("sidebar.tab_border_width") || 0
                }
                onClicked: strip.manager.unpinWidget(modelData)
            }
        }
    }
}
