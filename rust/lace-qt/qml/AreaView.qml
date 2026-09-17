import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import com.lace.dock 1.0

// One dock area: a themed frame, a title strip (focus-aware, with float/pin
// actions) and a TabBar over a StackLayout. Tab switches sync the document
// silently (no rebuild); closes, reopen toggles and pins re-emit (rebuild).
Item {
    id: root
    required property var manager
    required property int containerIndex
    required property string areaPath
    required property var area

    property var widgets: area.widgets || []
    property string focusKey: containerIndex + "/" + areaPath
    property bool areaActive: manager.focusedArea === focusKey
    property int initialIndex: {
        var names = []
        for (var w of widgets)
            names.push(w.name)
        var i = names.indexOf(area.current)
        if (i >= 0)
            return i
        for (var j = 0; j < widgets.length; ++j) {
            if (!widgets[j].closed)
                return j
        }
        return 0
    }
    property string currentName: {
        var w = widgets[bar.currentIndex]
        return w ? w.name : ""
    }

    Rectangle {
        anchors.fill: parent
        color: "transparent"
        border.color: root.areaActive
            ? (LaceTheme.color("core.focus_border_color") || "blue")
            : (LaceTheme.color("core.border_color") || "transparent")
        border.width: LaceTheme.num("core.border_width") || 0
        radius: LaceTheme.num("core.corner_radius") || 0
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // Title strip: focused areas take the active background.
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 30
            color: root.areaActive
                ? (LaceTheme.color("title_bar.bg_active") || "grey")
                : (LaceTheme.color("title_bar.bg_normal") || "darkgrey")
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 8
                anchors.rightMargin: 4
                spacing: 4
                Label {
                    text: root.currentName
                    color: root.areaActive
                        ? (LaceTheme.color("title_bar.text_active") || "white")
                        : (LaceTheme.color("title_bar.text_normal") || "white")
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
                Button {
                    text: qsTr("Float")
                    flat: true
                    enabled: root.currentName !== ""
                    onClicked: root.manager.floatWidget(root.currentName)
                }
                Button {
                    text: qsTr("Pin")
                    flat: true
                    enabled: root.currentName !== ""
                    onClicked: root.manager.pinWidget(root.currentName, "left")
                }
                Button {
                    text: root.manager.maximizedArea === root.focusKey ? qsTr("[_]") : qsTr("[ ]")
                    flat: true
                    onClicked: root.manager.toggleMaximize(root.focusKey)
                }
            }
            MouseArea {
                id: titleMouse
                anchors.fill: parent
                acceptedButtons: Qt.LeftButton
                onClicked: function(event) {
                    root.manager.focusedArea = root.focusKey
                    event.accepted = false
                }
                onPressAndHold: {
                    if (root.currentName === "")
                        return
                    // A real QML drag (keys + payload) so DropAreas fire;
                    // the manager mirrors the session for the drop ops.
                    titleMouse.Drag.source = titleMouse
                    titleMouse.Drag.keys = ["lace-tab"]
                    titleMouse.Drag.mimeData = { "text/plain": root.currentName }
                    titleMouse.Drag.active = true
                    root.manager.beginDrag(root.currentName)
                }
                onReleased: {
                    titleMouse.Drag.active = false
                    if (root.manager.dragActive)
                        root.manager.cancelDrag()
                }
            }
        }

        // Active-tab indicator strip: top, bottom, or absent for "none".
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: LaceTheme.num("tab.indicator_width") || 0
            visible: (LaceTheme.str("tab.indicator_position") || "bottom") === "top"
            color: LaceTheme.color("tab.indicator_color") || "transparent"
        }

        TabBar {
            id: bar
            Layout.fillWidth: true
            currentIndex: root.initialIndex

            Repeater {
                model: root.widgets
                TabButton {
                    required property var modelData
                    required property int index
                    contentItem: RowLayout {
                        spacing: 4
                        Label {
                            text: modelData.name + (modelData.closed ? " (closed)" : "")
                            color: parent.parent.checked
                                ? (LaceTheme.color("tab.text_active") || "white")
                                : (LaceTheme.color("tab.text_normal") || "white")
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                        }
                        Button {
                            text: "×"
                            flat: true
                            implicitWidth: 22
                            implicitHeight: 22
                            onClicked: root.manager.removeWidget(modelData.name)
                        }
                    }
                    background: Rectangle {
                        color: parent.checked
                            ? (LaceTheme.color("tab.bg_active") || "grey")
                            : (parent.hovered
                                ? (LaceTheme.color("tab.bg_hover") || "dimgrey")
                                : (LaceTheme.color("tab.bg_normal") || "darkgrey"))
                        radius: LaceTheme.num("tab.corner_radius") || 0
                    }
                    onClicked: {
                        root.manager.setCurrentTab(root.containerIndex, root.areaPath, modelData.name)
                    }
                }
            }

            onCurrentIndexChanged: {
                var w = root.widgets[currentIndex]
                if (w)
                    root.manager.setCurrentTab(root.containerIndex, root.areaPath, w.name)
            }
        }

        // Active-tab indicator strip (bottom by default, top on request,
        // absent for "none").
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: LaceTheme.num("tab.indicator_width") || 0
            visible: (LaceTheme.str("tab.indicator_position") || "bottom") === "bottom"
            color: LaceTheme.color("tab.indicator_color") || "transparent"
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: bar.currentIndex

            Repeater {
                model: root.widgets
                WidgetCard {
                    required property var modelData
                    manager: root.manager
                    widgetName: modelData.name
                    widgetClosed: !!modelData.closed
                }
            }
        }
    }

    // Drop zones (section level). Visible only while dragging an offered
    // edge; the highlight follows `dragTargetKey`. Zones never intercept
    // the mouse when idle (`visible: false` disables them).
    function zoneVisible(edge) {
        if (!manager.dragActive)
            return false
        return manager.dropEdges(containerIndex).split(",").includes(edge)
    }
    function zoneKey(edge) {
        return "S:" + containerIndex + "/" + areaPath + "/" + edge
    }
    function zoneHighlight(edge) {
        return manager.dragTargetKey === zoneKey(edge)
    }

    DropArea {
        keys: ["lace-tab"]
        anchors.fill: parent
        z: 10
        visible: zoneVisible("center")
        onEntered: manager.overSectionDrop(containerIndex, areaPath, "center")
        onDropped: manager.commitSectionDrop(containerIndex, areaPath, "center")
        Rectangle {
            anchors.fill: parent
            color: LaceTheme.color("overlay.overlay_color") || "transparent"
            border.color: LaceTheme.color("overlay.frame_color") || "blue"
            border.width: 2
            visible: zoneHighlight("center")
        }
    }
    DropArea {
        keys: ["lace-tab"]
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: 56
        z: 11
        visible: zoneVisible("left")
        onEntered: manager.overSectionDrop(containerIndex, areaPath, "left")
        onDropped: manager.commitSectionDrop(containerIndex, areaPath, "left")
        Rectangle {
            anchors.fill: parent
            color: LaceTheme.color("overlay.overlay_color") || "transparent"
            border.color: LaceTheme.color("overlay.frame_color") || "blue"
            border.width: 2
            visible: zoneHighlight("left")
        }
    }
    DropArea {
        keys: ["lace-tab"]
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: 56
        z: 11
        visible: zoneVisible("right")
        onEntered: manager.overSectionDrop(containerIndex, areaPath, "right")
        onDropped: manager.commitSectionDrop(containerIndex, areaPath, "right")
        Rectangle {
            anchors.fill: parent
            color: LaceTheme.color("overlay.overlay_color") || "transparent"
            border.color: LaceTheme.color("overlay.frame_color") || "blue"
            border.width: 2
            visible: zoneHighlight("right")
        }
    }
    DropArea {
        keys: ["lace-tab"]
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: 56
        z: 11
        visible: zoneVisible("top")
        onEntered: manager.overSectionDrop(containerIndex, areaPath, "top")
        onDropped: manager.commitSectionDrop(containerIndex, areaPath, "top")
        Rectangle {
            anchors.fill: parent
            color: LaceTheme.color("overlay.overlay_color") || "transparent"
            border.color: LaceTheme.color("overlay.frame_color") || "blue"
            border.width: 2
            visible: zoneHighlight("top")
        }
    }
    DropArea {
        keys: ["lace-tab"]
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: 56
        z: 11
        visible: zoneVisible("bottom")
        onEntered: manager.overSectionDrop(containerIndex, areaPath, "bottom")
        onDropped: manager.commitSectionDrop(containerIndex, areaPath, "bottom")
        Rectangle {
            anchors.fill: parent
            color: LaceTheme.color("overlay.overlay_color") || "transparent"
            border.color: LaceTheme.color("overlay.frame_color") || "blue"
            border.width: 2
            visible: zoneHighlight("bottom")
        }
    }
}
