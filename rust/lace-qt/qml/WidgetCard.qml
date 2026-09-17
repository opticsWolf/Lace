import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import com.lace.dock 1.0

// One tab page: a label, a real multi-line editor (proves Quick text input
// inside docked tabs), and a close/reopen toggle. Padded by the panel's
// content margin.
Item {
    id: card
    required property var manager
    required property string widgetName
    required property bool widgetClosed

    Rectangle {
        anchors.fill: parent
        color: LaceTheme.color("panel.bg_normal") || "transparent"
        radius: LaceTheme.num("panel.corner_radius") || 0
    }

    ColumnLayout {
        id: layout
        anchors.fill: parent
        anchors.leftMargin: LaceTheme.margins().left
        anchors.topMargin: LaceTheme.margins().top
        anchors.rightMargin: LaceTheme.margins().right
        anchors.bottomMargin: LaceTheme.margins().bottom
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
