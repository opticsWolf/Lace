import QtQuick
import QtQuick.Controls

import com.lace.dock 1.0

// Auto-hide sidebar strip for one window edge. The strip collapses when
// nothing is pinned (Shell binds `visible`); hovering a tab slides out a
// preview panel with the widget's content, like the QWidget version.
// Clicking a tab docks it back into the main container.
Item {
    id: strip
    required property var manager
    required property string side

    property var pinned: []
    property var closedMap: ({})
    // Shell reads this to collapse the empty strip.
    property int pinnedCount: pinned.length
    // Tab currently previewed in the slide-out panel.
    property string hoveredName: ""
    // Last previewed tab (restores the panel on slow tab->popup travel).
    property string lastName: ""
    // True while the pointer sits over the popup (grace for travel).
    property bool popupHover: false

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
            if (hoveredName !== "" && names.indexOf(hoveredName) < 0) {
                hoveredName = ""
                lastName = ""
            }
            var closed = {}
            var roster = doc.widget_states || {}
            for (var key in roster)
                closed[key] = !!roster[key].closed
            closedMap = closed
        } catch (e) {
            pinned = []
            closedMap = ({})
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
                    // Badge dot for closed widgets (badge_bg token).
                    Rectangle {
                        width: 8
                        height: 8
                        radius: 4
                        anchors.top: parent.top
                        anchors.right: parent.right
                        anchors.margins: 4
                        color: LaceTheme.color("sidebar.badge_bg") || "red"
                        visible: !!strip.closedMap[modelData]
                    }
                }
                onClicked: strip.manager.unpinWidget(modelData)
                // Leaving a tab starts the grace timer instead of hiding
                // at once (covers tab->tab, tab->popup and tab->void).
                onHoveredChanged: {
                    if (hovered) {
                        graceTimer.stop()
                        strip.lastName = modelData
                        strip.hoveredName = modelData
                    } else {
                        graceTimer.start()
                    }
                }
            }
        }
    }

    // Slide-out preview: the pinned widget's content beside the strip.
    // Unclipped overflow paints over the dock view (z below); a short
    // grace timer bridges the travel gap between tab and panel.
    Timer {
        id: graceTimer
        interval: 250
        repeat: false
        onTriggered: strip.hoveredName = ""
    }
    Rectangle {
        id: popup
        // Left strip opens rightwards, right strip leftwards.
        x: strip.side === "left" ? strip.width + 4 : -(popup.width + 4)
        y: 0
        width: 320
        height: strip.height
        z: 100
        visible: strip.hoveredName !== ""
        color: LaceTheme.color("sidebar.overlay_bg")
            || LaceTheme.color("panel.bg_normal") || "#2a2a2a"
        border.color: LaceTheme.color("sidebar.border_color") || "transparent"
        border.width: LaceTheme.num("sidebar.border_width") || 0
        radius: LaceTheme.num("core.corner_radius") || 0
        onVisibleChanged: {
            if (!visible)
                strip.popupHover = false
            else
                graceTimer.stop()
        }
        HoverHandler {
            id: popupHover
            onHoveredChanged: {
                strip.popupHover = hovered
                if (!hovered)
                    graceTimer.start()
                else {
                    graceTimer.stop()
                    if (strip.hoveredName === "" && strip.lastName !== "")
                        strip.hoveredName = strip.lastName
                }
            }
        }
        Label {
            id: popupTitle
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.margins: 8
            text: strip.hoveredName
            color: LaceTheme.color("title_bar.text_normal") || "white"
            elide: Text.ElideRight
        }
        WidgetCard {
            anchors.top: popupTitle.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.margins: 8
            manager: strip.manager
            widgetName: strip.hoveredName
            widgetClosed: !!strip.closedMap[strip.hoveredName]
        }
        MouseArea {
            anchors.fill: parent
            acceptedButtons: Qt.LeftButton
            onClicked: function(event) {
                if (strip.hoveredName !== "")
                    strip.manager.unpinWidget(strip.hoveredName)
                event.accepted = true
            }
        }
    }
}
