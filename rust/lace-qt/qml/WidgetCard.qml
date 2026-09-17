import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// One tab page: a label, a real multi-line editor (proves Quick text input
// inside docked tabs), and a close/reopen toggle.
Item {
    id: card
    required property var manager
    required property string widgetName
    required property bool widgetClosed

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 8
        spacing: 6

        Label {
            text: card.widgetName
            font.bold: true
            font.pointSize: 14
        }
        Label {
            text: qsTr("Closed — reopen to dock it back into the tab.")
            visible: card.widgetClosed
        }
        TextArea {
            Layout.fillWidth: true
            Layout.fillHeight: true
            placeholderText: qsTr("Type here. Tab switches keep this text (no rebuild).")
            wrapMode: TextArea.Wrap
        }
        Button {
            text: card.widgetClosed ? qsTr("Reopen") : qsTr("Close")
            onClicked: card.manager.setWidgetClosed(card.widgetName, !card.widgetClosed)
        }
    }
}
