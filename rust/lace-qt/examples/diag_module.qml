import QtQuick
import QtQuick.Window

import com.lace.dock 1.0

Window {
    width: 320
    height: 200
    visible: true
    title: "module"

    LaceManager {
        id: manager
    }

    Component.onCompleted: console.log("module qml completed, counter=" + manager.counter)

    Timer {
        interval: 500
        running: true
        onTriggered: Qt.quit()
    }
}
