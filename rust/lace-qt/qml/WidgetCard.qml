import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

import com.lace.dock 1.0

// Demo widget sampler: one tab page per dock, each showing a different
// QtQuick widget family (lists, tables, forms, canvas plots, dialogs,
// calendar, sampler controls). Unknown names fall back to a plain editor.
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

    function ink() {
        return LaceTheme.color("panel.text_color")
            || LaceTheme.color("core.text_color") || "white"
    }
    function inputBg() {
        return LaceTheme.color("panel.input_bg")
            || LaceTheme.color("panel.bg_normal") || "transparent"
    }
    function accent() {
        return LaceTheme.color("overlay.frame_color") || "steelblue"
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.leftMargin: LaceTheme.margins().left
        anchors.topMargin: LaceTheme.margins().top
        anchors.rightMargin: LaceTheme.margins().right
        anchors.bottomMargin: LaceTheme.margins().bottom
        spacing: 6

        Label {
            text: qsTr("Closed — click the tab × to dock it back in.")
            visible: card.widgetClosed
        }

        // ---- Outline: file-tree style list ----
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: card.widgetName === "Outline"
            ListView {
                anchors.fill: parent
                clip: true
                model: ListModel {
                    ListElement { name: "lace-core"; detail: "theme · layout · ops" }
                    ListElement { name: "lace-qt"; detail: "bridges · QML shell" }
                    ListElement { name: "lace-py"; detail: "bindings" }
                    ListElement { name: "docs"; detail: "plans · migration" }
                    ListElement { name: "demos"; detail: "showcase panels" }
                }
                delegate: ColumnLayout {
                    width: ListView.view.width
                    spacing: 0
                    Label {
                        text: "▸ " + name
                        color: card.ink()
                        font.bold: true
                    }
                    Label {
                        text: "     " + detail
                        color: card.ink()
                        opacity: 0.65
                        font.pointSize: 8
                    }
                }
                ScrollBar.vertical: ScrollBar {}
            }
        }

        // ---- Editor / Notes: multi-line editors ----
        TextArea {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: card.widgetName === "Editor" || card.widgetName === "Notes"
            placeholderText: card.widgetName === "Editor"
                ? qsTr("Type here. Tab switches keep this text (no rebuild).")
                : qsTr("Scratch notes…")
            text: card.widgetName === "Editor"
                ? "fn dock(widget: &str, edge: DockEdge) {\n    dock_widget(doc, widget, edge, None, false);\n}\n"
                : "- Try: drag a title bar onto a tab edge\n- Maximize from the title bar\n- Escape restores first, then defocuses\n"
            wrapMode: TextArea.Wrap
            font.family: card.widgetName === "Editor" ? "monospace" : ""
            color: card.ink()
            background: Rectangle { color: card.inputBg(); radius: 3 }
        }

        // ---- Terminal: console look ----
        TextArea {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: card.widgetName === "Terminal"
            placeholderText: qsTr("$ type commands… (demo console, not a real shell)")
            text: "$ lace_demo --theme dracula\nloaded 27 presets in 0.4s\n$ "
            wrapMode: TextArea.Wrap
            font.family: "monospace"
            color: LaceTheme.color("core.success_color") || "lightgreen"
            background: Rectangle { color: card.inputBg(); radius: 3 }
        }

        // ---- Files: list browser with sizes ----
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: card.widgetName === "Files"
            ListView {
                anchors.fill: parent
                clip: true
                model: ListModel {
                    ListElement { fname: "Cargo.toml"; fsize: "2 kb" }
                    ListElement { fname: "layout_ops.rs"; fsize: "48 kb" }
                    ListElement { fname: "manager.rs"; fsize: "61 kb" }
                    ListElement { fname: "DockManagerView.qml"; fsize: "22 kb" }
                    ListElement { fname: "OverlayCross.qml"; fsize: "14 kb" }
                    ListElement { fname: "WidgetCard.qml"; fsize: "18 kb" }
                    ListElement { fname: "demo-visible.log"; fsize: "9 kb" }
                }
                delegate: RowLayout {
                    width: ListView.view.width
                    Label { text: fname; color: card.ink(); Layout.fillWidth: true }
                    Label { text: fsize; color: card.ink(); opacity: 0.6; font.pointSize: 8 }
                }
                ScrollBar.vertical: ScrollBar {}
            }
        }

        // ---- Search: filter-as-you-type ----
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: card.widgetName === "Search"
            ColumnLayout {
                anchors.fill: parent
                spacing: 6
                TextField {
                    id: query
                    Layout.fillWidth: true
                    placeholderText: qsTr("Filter widgets… (try 'tab' or 'dock')")
                }
                ListView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    property var all: ["Button", "CheckBox", "Slider", "TableView",
                        "Calendar", "Dial", "Tumbler", "Canvas plot", "ColorDialog",
                        "TabBar", "ComboBox", "ProgressBar", "DockArea", "Splitter"]
                    model: query.text === "" ? all
                        : all.filter(function(w) { return w.toLowerCase().indexOf(query.text.toLowerCase()) >= 0 })
                    delegate: Label {
                        width: ListView.view.width
                        text: modelData
                        color: card.ink()
                    }
                    ScrollBar.vertical: ScrollBar {}
                }
            }
        }

        // ---- Table: TableView + header over a TableModel ----
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: card.widgetName === "Table"
            ColumnLayout {
                anchors.fill: parent
                spacing: 2
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 0
                    Label {
                        Layout.preferredWidth: 130
                        text: qsTr("Widget")
                        color: card.ink()
                        font.bold: true
                        padding: 4
                    }
                    Label {
                        Layout.preferredWidth: 70
                        text: qsTr("Areas")
                        color: card.ink()
                        font.bold: true
                        padding: 4
                    }
                    Label {
                        Layout.fillWidth: true
                        text: qsTr("Size")
                        color: card.ink()
                        font.bold: true
                        padding: 4
                    }
                }
                ListView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    model: ListModel {
                        ListElement { widget: "Outline"; areas: "1"; size: "190" }
                        ListElement { widget: "Editor"; areas: "3"; size: "412" }
                        ListElement { widget: "Properties"; areas: "2"; size: "356" }
                        ListElement { widget: "Output"; areas: "1"; size: "128" }
                        ListElement { widget: "Toolbox"; areas: "float"; size: "96" }
                    }
                    delegate: RowLayout {
                        width: ListView.view.width
                        spacing: 0
                        Label {
                            Layout.preferredWidth: 130
                            text: widget
                            color: card.ink()
                            padding: 4
                        }
                        Label {
                            Layout.preferredWidth: 70
                            text: areas
                            color: card.ink()
                            padding: 4
                        }
                        Label {
                            Layout.fillWidth: true
                            text: size
                            color: card.ink()
                            padding: 4
                        }
                    }
                    ScrollBar.vertical: ScrollBar {}
                }
            }
        }

        // ---- Properties: live form controls ----
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: card.widgetName === "Properties"
            ScrollView {
                anchors.fill: parent
                clip: true
                ColumnLayout {
                    width: parent.width
                    spacing: 8
                    GroupBox {
                        title: qsTr("Build")
                        Layout.fillWidth: true
                        ColumnLayout {
                            CheckBox { text: qsTr("Optimize"); checked: true }
                            CheckBox { text: qsTr("Debug symbols") }
                            Switch { text: qsTr("Verbose") }
                        }
                    }
                    GroupBox {
                        title: qsTr("Options")
                        Layout.fillWidth: true
                        ColumnLayout {
                            ComboBox {
                                Layout.fillWidth: true
                                model: ["Debug", "Release", "RelWithDebInfo"]
                            }
                            RowLayout {
                                Label { text: qsTr("Jobs"); color: card.ink() }
                                Slider {
                                    id: jobs
                                    Layout.fillWidth: true
                                    from: 1
                                    to: 16
                                    value: 8
                                    stepSize: 1
                                }
                                Label { text: Math.round(jobs.value); color: card.ink() }
                            }
                            RowLayout {
                                Label { text: qsTr("Cache MB"); color: card.ink() }
                                SpinBox {
                                    from: 0
                                    to: 4096
                                    value: 512
                                }
                            }
                        }
                    }
                }
            }
        }

        // ---- Plots: Canvas chart + frequency ----
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: card.widgetName === "Plots"
            ColumnLayout {
                anchors.fill: parent
                spacing: 6
                Canvas {
                    id: plot
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    onPaint: {
                        var ctx = getContext("2d")
                        ctx.clearRect(0, 0, width, height)
                        ctx.strokeStyle = "#888"
                        ctx.beginPath()
                        ctx.moveTo(0, height / 2)
                        ctx.lineTo(width, height / 2)
                        ctx.stroke()
                        ctx.strokeStyle = card.accent()
                        ctx.lineWidth = 2
                        ctx.beginPath()
                        for (var x = 0; x < width; x += 2) {
                            var y = height / 2 - Math.sin(x / width * Math.PI * 2 * freq.value) * height * 0.38
                            if (x === 0)
                                ctx.moveTo(x, y)
                            else
                                ctx.lineTo(x, y)
                        }
                        ctx.stroke()
                    }
                }
                RowLayout {
                    Label { text: qsTr("Frequency"); color: card.ink() }
                    Slider {
                        id: freq
                        Layout.fillWidth: true
                        from: 1
                        to: 8
                        value: 2
                        stepSize: 1
                        onValueChanged: plot.requestPaint()
                    }
                    Label { text: "×" + Math.round(freq.value); color: card.ink() }
                }
            }
        }

        // ---- Palette: RGB sliders + system color dialog ----
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: card.widgetName === "Palette"
            ColumnLayout {
                anchors.fill: parent
                spacing: 6
                Rectangle {
                    id: swatch
                    Layout.fillWidth: true
                    Layout.preferredHeight: 64
                    radius: 4
                    border.color: card.accent()
                    color: Qt.rgba(rS.value / 255, gS.value / 255, bS.value / 255, 1)
                }
                GridLayout {
                    columns: 2
                    Label { text: "R"; color: card.ink() }
                    Slider { id: rS; Layout.fillWidth: true; from: 0; to: 255; value: 70 }
                    Label { text: "G"; color: card.ink() }
                    Slider { id: gS; Layout.fillWidth: true; from: 0; to: 255; value: 130 }
                    Label { text: "B"; color: card.ink() }
                    Slider { id: bS; Layout.fillWidth: true; from: 0; to: 255; value: 180 }
                }
                Button {
                    Layout.fillWidth: true
                    text: qsTr("System color…")
                    onClicked: colorDlg.open()
                }
                ColorDialog {
                    id: colorDlg
                    title: qsTr("Pick a swatch color")
                    onAccepted: {
                        rS.value = Math.round(selectedColor.r * 255)
                        gS.value = Math.round(selectedColor.g * 255)
                        bS.value = Math.round(selectedColor.b * 255)
                    }
                }
            }
        }

        // ---- Calendar ----
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: card.widgetName === "Calendar"
            ColumnLayout {
                anchors.fill: parent
                spacing: 6
                Label {
                    text: qsTr("September 2026")
                    color: card.ink()
                    font.bold: true
                }
                GridLayout {
                    Layout.fillWidth: true
                    columns: 7
                    rowSpacing: 2
                    columnSpacing: 2
                    Repeater {
                        model: ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
                        Label {
                            Layout.fillWidth: true
                            text: modelData
                            color: card.ink()
                            opacity: 0.6
                            font.pointSize: 8
                            horizontalAlignment: Text.AlignHCenter
                        }
                    }
                    // September 2026 starts on a Tuesday: one blank first.
                    Item { Layout.preferredWidth: 1; Layout.preferredHeight: 1 }
                    Repeater {
                        model: 30
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 24
                            radius: 4
                            color: (index + 1) === 17 ? card.accent() : "transparent"
                            border.color: (index + 1) === 17 ? "transparent" : card.ink()
                            opacity: (index + 1) === 17 ? 1.0 : 0.25
                            Label {
                                anchors.centerIn: parent
                                text: index + 1
                                color: (index + 1) === 17 ? "white" : card.ink()
                            }
                        }
                    }
                }
            }
        }

        // ---- Output: build log + progress ----
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: card.widgetName === "Output"
            ColumnLayout {
                anchors.fill: parent
                spacing: 6
                TextArea {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    readOnly: true
                    wrapMode: TextArea.Wrap
                    font.family: "monospace"
                    text: "[build] lace-qt compiled clean\n[smoke] dock_demo exit 0\n[test] 110 cargo green\n"
                    color: LaceTheme.color("core.success_color") || "lightgreen"
                    background: Rectangle { color: card.inputBg(); radius: 3 }
                }
                RowLayout {
                    BusyIndicator {
                        running: true
                        implicitWidth: 20
                        implicitHeight: 20
                    }
                    ProgressBar {
                        Layout.fillWidth: true
                        from: 0
                        to: 100
                        value: 72
                    }
                    Label { text: "72%"; color: card.ink() }
                }
            }
        }

        // ---- Console: prompt + run button ----
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: card.widgetName === "Console"
            ColumnLayout {
                anchors.fill: parent
                spacing: 6
                TextArea {
                    id: consoleLog
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    readOnly: true
                    wrapMode: TextArea.Wrap
                    font.family: "monospace"
                    text: "$ lace_demo --list\nOutline Editor Notes Terminal Files\n"
                    color: card.ink()
                    background: Rectangle { color: card.inputBg(); radius: 3 }
                }
                RowLayout {
                    TextField {
                        id: consoleCmd
                        Layout.fillWidth: true
                        placeholderText: qsTr("command…")
                        onAccepted: runBtn.clicked()
                    }
                    Button {
                        id: runBtn
                        text: qsTr("Run")
                        onClicked: {
                            consoleLog.text += "$ " + consoleCmd.text + "\n(ok)\n"
                            consoleCmd.text = ""
                        }
                    }
                }
            }
        }

        // ---- Toolbox (float): small control sampler ----
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: card.widgetName === "Toolbox"
            RowLayout {
                anchors.fill: parent
                spacing: 10
                Dial {
                    Layout.preferredWidth: 84
                    Layout.preferredHeight: 84
                    from: 0
                    to: 100
                    value: 42
                }
                Tumbler {
                    Layout.preferredWidth: 60
                    Layout.fillHeight: true
                    model: 12
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    Switch { text: qsTr("Pin") }
                    Switch { text: qsTr("Float"); checked: true }
                    BusyIndicator {
                        running: true
                        implicitWidth: 24
                        implicitHeight: 24
                    }
                }
            }
        }

        // ---- Fallback: plain editor for any other name ----
        TextArea {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: card.isFallback(card.widgetName)
            placeholderText: qsTr("Type here.")
            wrapMode: TextArea.Wrap
            color: card.ink()
            background: Rectangle { color: card.inputBg(); radius: 3 }
        }
    }

    function isFallback(name) {
        return ["Outline", "Editor", "Notes", "Terminal", "Files", "Search",
            "Table", "Properties", "Plots", "Palette", "Calendar",
            "Output", "Console", "Toolbox"].indexOf(name) < 0
    }
}
