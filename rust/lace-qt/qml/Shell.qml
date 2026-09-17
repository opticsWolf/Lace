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
    title: qsTr("Lace dock demo — Tier 0 native frames")

    LaceManager {
        id: manager
    }

    property int tabCounter: 0

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

        DockManagerView {
            id: dockView
            manager: manager
            Layout.fillWidth: true
            Layout.fillHeight: true
        }
    }

    Component.onCompleted: manager.seedDemo()

    // Headless self-test: seed (tabs + split + float), add a tab, remove
    // it again — the verdict is the exit code (Qt.exit), because QML
    // console output is not captured reliably on every platform.
    function smokeCounts() {
        return dockView.lastCounts
    }
    function smokeCheck(areas, widgets, floats) {
        var c = smokeCounts()
        return c.areas === areas && c.widgets === widgets && c.floats === floats
    }
    Timer {
        interval: 1500
        running: Qt.application.arguments.includes("--smoke")
        onTriggered: {
            if (!smokeCheck(2, 5, 1))
                Qt.exit(11)
            manager.dockWidget("SmokeTab", "right", "", false)
            if (!smokeCheck(3, 6, 1))
                Qt.exit(12)
            manager.removeWidget("SmokeTab")
            if (!smokeCheck(2, 5, 1))
                Qt.exit(13)
            Qt.quit()
        }
    }
}
