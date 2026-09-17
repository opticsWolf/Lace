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
            placeholderText: card.placeholderFor(card.widgetName)
            text: card.initialTextFor(card.widgetName)
            wrapMode: TextArea.Wrap
            font.family: card.isCodeCard(card.widgetName) ? "monospace" : ""
            color: card.isTerminalCard(card.widgetName)
                ? (LaceTheme.color("core.success_color") || "lightgreen")
                : (LaceTheme.color("panel.text_color")
                    || LaceTheme.color("core.text_color") || "white")
        }
        Button {
            text: card.widgetClosed ? qsTr("Reopen") : qsTr("Close")
            onClicked: card.manager.setWidgetClosed(card.widgetName, !card.widgetClosed)
        }
    }

    function isCodeCard(name) {
        return name === "Editor" || name === "Terminal" || name === "Output"
    }
    function isTerminalCard(name) {
        return name === "Terminal" || name === "Output"
    }
    function placeholderFor(name) {
        if (name === "Editor")
            return qsTr("Type here. Tab switches keep this text (no rebuild).")
        if (name === "Terminal")
            return qsTr("$ type commands… (demo console, not a real shell)")
        if (name === "Notes")
            return qsTr("Scratch notes…")
        if (name === "Outline")
            return qsTr("Symbols, files, chapters…")
        if (name === "Properties")
            return qsTr("key = value…")
        if (name === "Output")
            return qsTr("Build log lands here…")
        if (name === "Toolbox")
            return qsTr("Tools…")
        return qsTr("Type here.")
    }
    function initialTextFor(name) {
        if (name === "Editor")
            return "fn dock(widget: &str, edge: DockEdge) {\n    dock_widget(doc, widget, edge, None, false);\n}\n"
        if (name === "Terminal")
            return "$ lace_demo --theme dracula\nloaded 27 presets in 0.4s\n$ "
        if (name === "Output")
            return "[build] lace-qt compiled clean\n[smoke] dock_demo exit 0\n"
        if (name === "Notes")
            return "- Try: drag a title bar onto a tab edge\n- Maximize from the title bar\n- Escape restores first, then defocuses\n"
        if (name === "Outline")
            return "workspace\n  lace-core (theme, layout, ops)\n  lace-qt (bridges, QML shell)\n  lace-py (bindings)\n"
        if (name === "Toolbox")
            return "pin - float - maximize - snapshot\n"
        return ""
    }
}
