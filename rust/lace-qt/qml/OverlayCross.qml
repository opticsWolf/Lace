import QtQuick

import com.lace.dock 1.0

// Container-level drop cross over the main view, shown while dragging.
// Pure visual: hover is computed geometrically by DockManagerView.hoverMove
// (no system DnD involved), highlights follow `dragTargetKey`. Edges split
// the root directionally; the centre follows the solo-tabs / multi-splits
// fallback. The rubber band in DockManagerView shows the result rect.
Item {
    id: cross
    required property var manager
    required property int mainIndex

    anchors.fill: parent
    z: 20
    visible: manager.dragActive

    function zoneKey(zone) {
        return "C:" + mainIndex + "/" + zone
    }
    function highlighted(zone) {
        return manager.dragTargetKey === zoneKey(zone)
    }
    function frameColor() {
        return LaceTheme.color("overlay.frame_color") || "blue"
    }
    function fillColor() {
        return LaceTheme.color("overlay.overlay_color") || "transparent"
    }

    Rectangle {
        anchors.fill: parent
        color: "transparent"
        border.color: frameColor()
        border.width: 2
    }

    component ZoneBand: Rectangle {
        property string zone: ""
        color: fillColor()
        border.color: frameColor()
        border.width: 2
        opacity: highlighted(zone) ? 0.65 : 0.22
    }

    ZoneBand {
        zone: "left"
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: 72
    }
    ZoneBand {
        zone: "right"
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: 72
    }
    ZoneBand {
        zone: "top"
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: 72
    }
    ZoneBand {
        zone: "bottom"
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: 72
    }
    Rectangle {
        anchors.centerIn: parent
        width: 200
        height: 140
        color: fillColor()
        border.color: frameColor()
        border.width: 3
        opacity: highlighted("center") ? 0.65 : 0.22
        Text {
            anchors.centerIn: parent
            text: qsTr("Drop to tab / split")
            color: LaceTheme.color("overlay.arrow_color") || "white"
        }
    }
}
