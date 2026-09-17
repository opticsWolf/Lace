import QtQuick
import QtQuick.Shapes

import com.lace.dock 1.0

// Container-level drop cross over the main view, shown while dragging.
// Pure visual: hover is computed geometrically by DockManagerView.hoverMove,
// highlights follow `dragTargetKey`. A five-part cross tracks the hovered
// area (or the whole view for container zones); the live icon and the
// rubber band in DockManagerView mark the active drop.
Item {
    id: cross
    objectName: "overlayCross"
    required property var manager
    required property int mainIndex
    required property rect hoverRect
    required property string activeEdge
    // Edges the current container offers (disallowed icons hide, so the
    // cross never offers a drop the preview would refuse).
    required property var allowedEdges
    // True while hovering a container-level zone (arrows draw then).
    required property bool containerMode

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
        visible: cross.allowedEdges.indexOf(zone) >= 0
        color: fillColor()
        border.color: frameColor()
        border.width: 2
        opacity: 0.22
    }

    RimBand {
        zone: "left"
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: 72
    }
    RimBand {
        zone: "right"
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: 72
    }
    RimBand {
        zone: "top"
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: 72
    }
    RimBand {
        zone: "bottom"
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
        width: 168
        height: 168

        // Miniature window mockup: shadow, panel with title strip, the
        // landing half tinted + dashed divider, and (container mode) an
        // arrow in the other half pointing at the drop side. Area mode
        // shows halves without arrows; center is a plain mockup (tab-in).
        component MiniIcon: Item {
            property string edge: ""
            property bool containerMode: false
            width: 52
            height: 52
            visible: cross.allowedEdges.indexOf(edge) >= 0
            opacity: cross.activeEdge === edge ? 1.0 : 0.85
            Rectangle {
                anchors.fill: parent
                color: "black"
                opacity: 0.35
                radius: 5
            }
            Rectangle {
                id: base
                anchors.centerIn: parent
                width: 36
                height: 36
                radius: 3
                color: LaceTheme.color("panel.bg_normal") || "#2a2a2a"
                border.color: frameColor()
                border.width: cross.activeEdge === parent.edge ? 2 : 1
            }
            Rectangle {
                anchors.top: base.top
                anchors.left: base.left
                anchors.right: base.right
                height: 4
                color: frameColor()
            }
            Rectangle {
                id: half
                visible: parent.edge !== "center"
                x: base.x + ((parent.edge === "right" || parent.edge === "bottom") ? base.width / 2 : 0)
                y: base.y + (parent.edge === "bottom" ? base.height / 2 : 0)
                width: (parent.edge === "left" || parent.edge === "right") ? base.width / 2 : base.width
                height: (parent.edge === "top" || parent.edge === "bottom") ? base.height / 2 : base.height
                color: LaceTheme.color("overlay.overlay_color") || "transparent"
            }
            Shape {
                visible: parent.edge !== "center"
                anchors.fill: parent
                ShapePath {
                    strokeColor: frameColor()
                    strokeWidth: 1
                    strokeStyle: ShapePath.DashLine
                    fillColor: "transparent"
                    startX: dividerX1
                    startY: dividerY1
                    PathLine { x: dividerX2; y: dividerY2 }
                }
                property real dividerX1: base.x + ((parent.edge === "left" || parent.edge === "right") ? base.width / 2 : 0)
                property real dividerY1: base.y + ((parent.edge === "top" || parent.edge === "bottom") ? base.height / 2 : 0)
                property real dividerX2: base.x + ((parent.edge === "left" || parent.edge === "right") ? base.width / 2 : base.width)
                property real dividerY2: base.y + ((parent.edge === "top" || parent.edge === "bottom") ? base.height / 2 : base.height)
            }
            Shape {
                visible: parent.containerMode && parent.edge !== "center"
                anchors.fill: parent
                transform: Rotation {
                    origin.x: 26
                    origin.y: 26
                    angle: parent.edge === "left" ? 180 : (parent.edge === "top" ? -90 : (parent.edge === "bottom" ? 90 : 0))
                }
                ShapePath {
                    fillColor: arrowColor()
                    strokeColor: "transparent"
                    startX: arrowCX - 7
                    startY: arrowCY - 6
                    PathLine { x: arrowCX + 5; y: arrowCY }
                    PathLine { x: arrowCX - 7; y: arrowCY + 6 }
                    PathLine { x: arrowCX - 7; y: arrowCY - 6 }
                }
                // Center of the non-landing half (base-local arrow, drawn
                // pointing right then rotated per edge).
                property real arrowCX: parent.edge === "left" ? base.x + base.width * 0.75 : (parent.edge === "right" ? base.x + base.width * 0.25 : base.x + base.width / 2)
                property real arrowCY: parent.edge === "top" ? base.y + base.height * 0.75 : (parent.edge === "bottom" ? base.y + base.height * 0.25 : base.y + base.height / 2)
            }
        }

        MiniIcon {
            edge: "top"
            containerMode: cross.containerMode
            anchors.top: parent.top
            anchors.horizontalCenter: parent.horizontalCenter
        }
        MiniIcon {
            edge: "left"
            containerMode: cross.containerMode
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
        }
        MiniIcon {
            edge: "center"
            containerMode: cross.containerMode
            anchors.centerIn: parent
        }
        MiniIcon {
            edge: "right"
            containerMode: cross.containerMode
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
        }
        MiniIcon {
            edge: "bottom"
            containerMode: cross.containerMode
            anchors.bottom: parent.bottom
            anchors.horizontalCenter: parent.horizontalCenter
        }
    }
}
