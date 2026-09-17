import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// Must match the uri/version in the qml_module in rust/lace-qt/build.rs.
import com.lace.dock 1.0

ApplicationWindow {
    id: root
    width: 1280
    height: 800
    visible: true
    title: qsTr("Lace — Rust dock demo")

    LaceManager {
        id: manager
    }

    property int tabCounter: 0

    function refreshTheme() {
        LaceTheme.update(manager.themeJson, manager.themeName)
        themeBox.currentIndex = themeBox.indexOfValue(manager.themeName)
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        ToolBar {
            Layout.fillWidth: true
            RowLayout {
                anchors.fill: parent
                Button {
                    text: qsTr("Add tab")
                    onClicked: {
                        root.tabCounter += 1
                        manager.dockWidget("Tab" + root.tabCounter, "center", "", false)
                    }
                }
                Button {
                    text: qsTr("Split right")
                    onClicked: {
                        root.tabCounter += 1
                        manager.dockWidget("Tab" + root.tabCounter, "right", "", false)
                    }
                }
                Button {
                    text: qsTr("Float Alpha")
                    onClicked: manager.floatWidget("Alpha")
                }
                Button {
                    text: qsTr("Reset demo")
                    onClicked: manager.seedDemo()
                }
                Button {
                    text: qsTr("Showcase")
                    onClicked: manager.seedShowcase()
                }
                Button {
                    text: qsTr("Save")
                    onClicked: manager.saveDemoLayout()
                }
                Button {
                    text: qsTr("Load")
                    onClicked: manager.loadDemoLayout()
                }
                ComboBox {
                    id: themeBox
                    Layout.preferredWidth: 220
                    textRole: "label"
                    valueRole: "key"
                    model: ListModel {
                        id: themeModel
                    }
                    onActivated: manager.applyThemeName(currentValue)
                }
                Button {
                    text: qsTr("Quit")
                    onClicked: Qt.quit()
                }
                Label {
                    text: manager.lastError
                    color: "red"
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            SidebarView {
                manager: manager
                side: "left"
                Layout.preferredWidth: 34
                Layout.fillHeight: true
            }

            DockManagerView {
                id: dockView
                manager: manager
                Layout.fillWidth: true
                Layout.fillHeight: true
            }

            SidebarView {
                manager: manager
                side: "right"
                Layout.preferredWidth: 34
                Layout.fillHeight: true
            }
        }
    }

    Connections {
        target: manager
        function onThemeJsonChanged() { root.refreshTheme() }
    }

    // Escape backs out: restore a maximized area first, otherwise defocus.
    // (The QWidget sidebar-overlay gating lives here once the overlay does.)
    Shortcut {
        sequence: "Escape"
        onActivated: {
            if (manager.maximizedArea !== "")
                manager.toggleMaximize("")
            else
                manager.focusedArea = ""
        }
    }

    Component.onCompleted: {
        for (var i = 0; i < manager.presetCount(); ++i) {
            var key = manager.presetNameAt(i)
            var label = key.charAt(0).toUpperCase() + key.slice(1).replace(/_/g, " ")
            themeModel.append({ label: label, key: key })
        }
        // Interactive runs open the showcase; the headless smoke seeds the
        // small layout its counters assert.
        if (Qt.application.arguments.includes("--smoke"))
            manager.seedDemo()
        else
            manager.seedShowcase()
        root.refreshTheme()
    }

    // Headless self-test: layout ops, then every preset through the theme
    // verifier. The verdict is the exit code (Qt.exit), because QML console
    // output is not captured reliably on every platform.
    function verifyTheme(expectedName) {
        if (LaceTheme.presetName !== expectedName)
            return false
        var tokens = [
            "core.canvas_bg", "core.accent_color", "core.text_color", "core.tooltip_bg",
            "panel.bg_normal", "panel.input_bg", "panel.border_width",
            "tab.bg_normal", "tab.bg_hover", "tab.bg_active",
            "tab.text_normal", "tab.text_active", "tab.indicator_color",
            "tab.close_btn_color", "tab.font_family", "tab.indicator_position",
            "title_bar.bg_normal", "title_bar.text_normal", "title_bar.button_color",
            "title_bar.height", "title_bar.font_size",
            "sidebar.bg_color", "sidebar.tab_bg_hover_start", "sidebar.indicator_color",
            "sidebar.badge_bg", "sidebar.width", "sidebar.tab_flat_edge",
            "sidepanel.bg_normal", "sidepanel.border_width",
            "splitter.handle_color", "splitter.handle_hover_color", "splitter.handle_width",
            "overlay.frame_color", "overlay.arrow_color"
        ]
        for (var t of tokens) {
            if (LaceTheme.raw(t) === undefined)
                return false
        }
        return true
    }

    function smokeCheck(areas, widgets, floats) {
        var c = dockView.lastCounts
        return c.areas === areas && c.widgets === widgets && c.floats === floats
    }

    // Ground truth (verified against the Rust ops directly): the seed is
    // 2 areas / 4 main widgets / 1 float — NOT (2, 5, 1); Epsilon floats.
    function smokeDragRoundtrip() {
        manager.floatWidget("Alpha")
        if (!smokeCheck(2, 3, 2))
            return 16
        if (!manager.beginDrag("Alpha"))
            return 17
        if (!manager.commitSectionDrop(0, "0", "center"))
            return 18
        if (!smokeCheck(2, 4, 1))
            return 19
        if (!manager.toggleMaximize("0/0"))
            return 30
        if (manager.maximizedArea !== "0/0")
            return 31
        if (!manager.toggleMaximize("0/0"))
            return 32
        if (manager.maximizedArea !== "")
            return 33
        if (manager.dropEdges(0) !== "left,right,top,bottom,center")
            return 34
        return 0
    }

    Timer {
        interval: 1500
        running: Qt.application.arguments.includes("--smoke")
        onTriggered: {
            if (!smokeCheck(2, 4, 1))
                Qt.exit(11)
            manager.dockWidget("SmokeTab", "right", "", false)
            if (!smokeCheck(3, 5, 1))
                Qt.exit(12)
            manager.removeWidget("SmokeTab")
            if (!smokeCheck(2, 4, 1))
                Qt.exit(13)
            var dragCode = smokeDragRoundtrip()
            if (dragCode !== 0)
                Qt.exit(dragCode)
            manager.pinWidget("Gamma", "left")
            if (!smokeCheck(2, 3, 1))
                Qt.exit(14)
            manager.unpinWidget("Gamma")
            if (!smokeCheck(2, 4, 1))
                Qt.exit(15)
            if (manager.presetCount() !== 27)
                Qt.exit(35)
            for (var i = 0; i < manager.presetCount(); ++i) {
                var key = manager.presetNameAt(i)
                if (!manager.applyThemeName(key))
                    Qt.exit(36)
                if (!verifyTheme(key))
                    Qt.exit(20 + (i % 100))
            }
            if (!manager.applyThemeName("default"))
                Qt.exit(37)
            Qt.quit()
        }
    }
}
