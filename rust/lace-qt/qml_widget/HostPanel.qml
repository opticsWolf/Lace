import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// Plain panel for the widget-host spike: no com.lace.dock import, so the C++
// side needs no module registration to show it.
Rectangle {
    color: "#1e1e2e"
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 8
        Label {
            text: qsTr("QML TextArea (Qt Quick)")
            color: "#cdd6f4"
            font.bold: true
        }
        TextArea {
            Layout.fillWidth: true
            Layout.fillHeight: true
            placeholderText: qsTr("Type here — the QWidget editor lives next door.")
            wrapMode: TextArea.Wrap
        }
    }
}
