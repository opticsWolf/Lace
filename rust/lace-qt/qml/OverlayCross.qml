import QtQuick

import com.lace.dock 1.0

// Container-level drop cross over the main view, shown while dragging.
// Edges split the root directionally; the centre follows the solo-tabs /
// multi-splits fallback. Uses the overlay_* tokens; the per-area zones in
// AreaView handle section-level drops.
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
        visible: manager.dragActive
    }

    DropArea {
        keys: ["lace-tab"]
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: 72
        onEntered: manager.overContainerDrop(mainIndex, "left")
        onDropped: manager.commitContainerDrop(mainIndex, "left")
        Rectangle {
            anchors.fill: parent
            color: fillColor()
            border.color: frameColor()
            border.width: 2
            visible: highlighted("left")
        }
    }
    DropArea {
        keys: ["lace-tab"]
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: 72
        onEntered: manager.overContainerDrop(mainIndex, "right")
        onDropped: manager.commitContainerDrop(mainIndex, "right")
        Rectangle {
            anchors.fill: parent
            color: fillColor()
            border.color: frameColor()
            border.width: 2
            visible: highlighted("right")
        }
    }
    DropArea {
        keys: ["lace-tab"]
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: 72
        onEntered: manager.overContainerDrop(mainIndex, "top")
        onDropped: manager.commitContainerDrop(mainIndex, "top")
        Rectangle {
            anchors.fill: parent
            color: fillColor()
            border.color: frameColor()
            border.width: 2
            visible: highlighted("top")
        }
    }
    DropArea {
        keys: ["lace-tab"]
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: 72
        onEntered: manager.overContainerDrop(mainIndex, "bottom")
        onDropped: manager.commitContainerDrop(mainIndex, "bottom")
        Rectangle {
            anchors.fill: parent
            color: fillColor()
            border.color: frameColor()
            border.width: 2
            visible: highlighted("bottom")
        }
    }
    DropArea {
        keys: ["lace-tab"]
        anchors.centerIn: parent
        width: 200
        height: 140
        onEntered: manager.overContainerDrop(mainIndex, "center")
        onDropped: manager.commitContainerDrop(mainIndex, "center")
        Rectangle {
            anchors.fill: parent
            color: fillColor()
            border.color: frameColor()
            border.width: 3
            visible: highlighted("center")
            Text {
                anchors.centerIn: parent
                text: qsTr("Drop to tab / split")
                color: LaceTheme.color("overlay.arrow_color") || "white"
            }
        }
    }
}
