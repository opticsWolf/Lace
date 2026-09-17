import QtQuick
import QtQuick.Controls
import QtQuick.Window

// Must match the uri/version in the qml_module in rust/lace-qt/build.rs.
import com.lace.dock 1.0

ApplicationWindow {
    id: root
    width: 640
    height: 480
    visible: true
    title: qsTr("Lace QML hello")

    LaceManager {
        id: manager
    }

    Column {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 10

        Label {
            text: qsTr("Counter: %1").arg(manager.counter)
        }
        Label {
            text: qsTr("Theme: %1").arg(manager.theme)
        }
        Button {
            text: qsTr("Increment")
            onClicked: manager.increment()
        }
        Button {
            text: qsTr("Dark theme")
            onClicked: manager.applyTheme("dark")
        }
        Button {
            text: qsTr("Quit")
            onClicked: Qt.quit()
        }
    }

    Component.onCompleted: {
        console.log("lace hello completed; args=" + JSON.stringify(Qt.application.arguments))
    }

    // CI smoke: `qml_minimal --smoke` quits right after load.
    Timer {
        interval: 500
        running: Qt.application.arguments.includes("--smoke")
        onTriggered: Qt.quit()
    }
}
