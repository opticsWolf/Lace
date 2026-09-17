import QtQuick

import com.lace.dock 1.0

// Container-level drop cross over the main view, shown while dragging.
// Pure visual: hover is computed geometrically by DockManagerView.hoverMove,
// highlights follow `dragTargetKey`. A five-part cross tracks the hovered
// area (or the whole view for container zones); the live icon and the
// rubber band in DockManagerView mark the active drop.
Item {
    id: cross
    required property var manager
    required property int mainIndex
    required property rect hoverRect
    required property string activeEdge

    anchors.fill: parent
    z: 20
    visible: manager.dragActive

    function zoneKey(zone) {
        return "C:" + mainIndex + "/" + zone
    }
    function frameColor() {
        return LaceTheme.color("overlay.frame_color") || "blue"
    }
    function fillColor() {
        return LaceTheme.color("overlay.overlay_color") || "transparent"
    }
    function arrowColor() {
        return LaceTheme.color("overlay.arrow_color") || "white"
    }

    Rectangle {
        anchors.fill: parent
        color: "transparent"
        border.color: frameColor()
        border.width: 2
    }

    component RimBand: Rectangle {
        property string zone: ""
        color: fillColor()
        border.color: frameColor()
        border.width: 2
        opacity: 0.22
    }

    RimBand {
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: 72
    }
    RimBand {
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: 72
    }
    RimBand {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: 72
    }
    RimBand {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: 72
    }

    // Five-part cross tracking the hovered area.
    Item {
        id: crossBox
        x: Math.round(cross.hoverRect.x + (cross.hoverRect.width - crossBox.width) / 2)
        y: Math.round(cross.hoverRect.y + (cross.hoverRect.height - crossBox.height) / 2)
        width: 132
        height: 132

        component CrossIcon: Rectangle {
            property string edge: ""
            property string glyph: ""
            width: 40
            height: 40
            radius: 6
            color: cross.activeEdge === edge ? frameColor() : fillColor()
            border.color: frameColor()
            border.width: cross.activeEdge === edge ? 3 : 1
            opacity: cross.activeEdge === edge ? 1.0 : 0.85
            Text {
                anchors.centerIn: parent
                text: parent.glyph
                font.pointSize: 16
                color: arrowColor()
            }
        }

        CrossIcon {
            edge: "top"
            glyph: "▲"
            anchors.top: parent.top
            anchors.horizontalCenter: parent.horizontalCenter
        }
        CrossIcon {
            edge: "left"
            glyph: "◀"
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
        }
        CrossIcon {
            edge: "center"
            glyph: "●"
            anchors.centerIn: parent
        }
        CrossIcon {
            edge: "right"
            glyph: "▶"
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
        }
        CrossIcon {
            edge: "bottom"
            glyph: "▼"
            anchors.bottom: parent.bottom
            anchors.horizontalCenter: parent.horizontalCenter
        }
    }
}
