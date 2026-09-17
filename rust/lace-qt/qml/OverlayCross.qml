import QtQuick
import QtQuick.Shapes

import com.lace.dock 1.0

// Drop crosses over the main view, shown while dragging. Two sets, like
// the reference implementations: four container icons pinned to the view
// edges (always visible during a drag) plus a five-part cross tracking the
// hovered area. The icons ARE the precise targets (hit-tested by geometry
// in DockManagerView); bands catch the rest. The rubber band in
// DockManagerView previews the future dock area and nothing else.
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
    // True while hovering an area zone: the compact cross shows then.
    required property bool showBox

    anchors.fill: parent
    z: 20
    visible: manager.dragActive

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

    // Miniature window mockup: shadow, panel with title strip, the
    // landing half tinted + dashed divider, and (container mode) an
    // arrow in the other half pointing at the drop side. Area mode
    // shows halves without arrows; center is a plain mockup (tab-in).
    // NOTE: Shape sub-contexts cannot see component-scope properties,
    // so every binding below uses the `mini`/`base` ids only.
    component MiniIcon: Item {
        id: mini
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
            border.width: cross.activeEdge === mini.edge ? 2 : 1
        }
        Rectangle {
            anchors.top: base.top
            anchors.left: base.left
            anchors.right: base.right
            height: 4
            color: frameColor()
        }
        Rectangle {
            visible: mini.edge !== "center"
            x: base.x + ((mini.edge === "right" || mini.edge === "bottom") ? base.width / 2 : 0)
            y: base.y + (mini.edge === "bottom" ? base.height / 2 : 0)
            width: (mini.edge === "left" || mini.edge === "right") ? base.width / 2 : base.width
            height: (mini.edge === "top" || mini.edge === "bottom") ? base.height / 2 : base.height
            color: LaceTheme.color("overlay.overlay_color") || "transparent"
        }
        Shape {
            visible: mini.edge !== "center"
            anchors.fill: parent
            ShapePath {
                strokeColor: frameColor()
                strokeWidth: 1
                strokeStyle: ShapePath.DashLine
                fillColor: "transparent"
                startX: (mini.edge === "left" || mini.edge === "right") ? base.x + base.width / 2 : base.x
                startY: (mini.edge === "top" || mini.edge === "bottom") ? base.y + base.height / 2 : base.y
                PathLine {
                    x: (mini.edge === "left" || mini.edge === "right") ? base.x + base.width / 2 : base.x + base.width
                    y: (mini.edge === "top" || mini.edge === "bottom") ? base.y + base.height / 2 : base.y + base.height
                }
            }
        }
        Shape {
            visible: mini.containerMode && mini.edge !== "center"
            anchors.fill: parent
            transform: Rotation {
                origin.x: 26
                origin.y: 26
                angle: mini.edge === "left" ? 180 : (mini.edge === "top" ? -90 : (mini.edge === "bottom" ? 90 : 0))
            }
            ShapePath {
                fillColor: arrowColor()
                strokeColor: "transparent"
                startX: (mini.edge === "left" ? base.x + base.width * 0.75 : (mini.edge === "right" ? base.x + base.width * 0.25 : base.x + base.width / 2)) - 7
                startY: (mini.edge === "top" ? base.y + base.height * 0.75 : (mini.edge === "bottom" ? base.y + base.height * 0.25 : base.y + base.height / 2)) - 6
                PathLine {
                    x: (mini.edge === "left" ? base.x + base.width * 0.75 : (mini.edge === "right" ? base.x + base.width * 0.25 : base.x + base.width / 2)) + 5
                    y: (mini.edge === "top" ? base.y + base.height * 0.75 : (mini.edge === "bottom" ? base.y + base.height * 0.25 : base.y + base.height / 2))
                }
                PathLine {
                    x: (mini.edge === "left" ? base.x + base.width * 0.75 : (mini.edge === "right" ? base.x + base.width * 0.25 : base.x + base.width / 2)) - 7
                    y: (mini.edge === "top" ? base.y + base.height * 0.75 : (mini.edge === "bottom" ? base.y + base.height * 0.25 : base.y + base.height / 2)) + 6
                }
                PathLine {
                    x: (mini.edge === "left" ? base.x + base.width * 0.75 : (mini.edge === "right" ? base.x + base.width * 0.25 : base.x + base.width / 2)) - 7
                    y: (mini.edge === "top" ? base.y + base.height * 0.75 : (mini.edge === "bottom" ? base.y + base.height * 0.25 : base.y + base.height / 2)) - 6
                }
            }
        }
    }

    // Compact cross tracking the hovered area (area mode: no arrows).
    Item {
        id: crossBox
        visible: cross.showBox
        x: Math.round(cross.hoverRect.x + (cross.hoverRect.width - crossBox.width) / 2)
        y: Math.round(cross.hoverRect.y + (cross.hoverRect.height - crossBox.height) / 2)
        width: 168
        height: 168

        MiniIcon {
            edge: "top"
            containerMode: false
            anchors.top: parent.top
            anchors.horizontalCenter: parent.horizontalCenter
        }
        MiniIcon {
            edge: "left"
            containerMode: false
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
        }
        MiniIcon {
            edge: "center"
            containerMode: false
            anchors.centerIn: parent
        }
        MiniIcon {
            edge: "right"
            containerMode: false
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
        }
        MiniIcon {
            edge: "bottom"
            containerMode: false
            anchors.bottom: parent.bottom
            anchors.horizontalCenter: parent.horizontalCenter
        }
    }

    // Container icons pinned to the view edges (container mode: arrows).
    MiniIcon {
        edge: "top"
        containerMode: true
        anchors.top: parent.top
        anchors.topMargin: 12
        anchors.horizontalCenter: parent.horizontalCenter
    }
    MiniIcon {
        edge: "left"
        containerMode: true
        anchors.left: parent.left
        anchors.leftMargin: 12
        anchors.verticalCenter: parent.verticalCenter
    }
    MiniIcon {
        edge: "right"
        containerMode: true
        anchors.right: parent.right
        anchors.rightMargin: 12
        anchors.verticalCenter: parent.verticalCenter
    }
    MiniIcon {
        edge: "bottom"
        containerMode: true
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 12
        anchors.horizontalCenter: parent.horizontalCenter
    }
}
