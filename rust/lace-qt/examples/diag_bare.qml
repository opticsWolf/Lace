import QtQuick
import QtQuick.Window

Window {
    width: 320
    height: 200
    visible: true
    title: "bare"

    Component.onCompleted: console.log("bare qml completed")

    Timer {
        interval: 500
        running: true
        onTriggered: Qt.quit()
    }
}
