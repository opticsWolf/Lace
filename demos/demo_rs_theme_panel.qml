import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// Panel for demos/demo_rs_theme_panel.py. All colours come from the
// `themeJson` context property (a `lace_rs.build_merged_theme` document),
// so this proves Rust theme data driving a Python-side Qt UI today.
ApplicationWindow {
    id: root
    width: 560
    height: 640
    visible: true
    title: qsTr("lace_rs theme panel")

    property var theme: ({})
    property string themeName: ""

    function rgba(tok) {
        var v = tok
        if (!v || v.length !== 4)
            return "transparent"
        return Qt.rgba(v[0] / 255, v[1] / 255, v[2] / 255, v[3] / 255)
    }
    function cat(name) {
        return theme[name] || {}
    }

    Component.onCompleted: reload()

    function reload() {
        try {
            theme = JSON.parse(themeJson)
        } catch (e) {
            theme = {}
        }
    }

    Connections {
        target: bridge
        function onThemeChanged() { reload() }
    }

    Rectangle {
        anchors.fill: parent
        color: rgba(cat("core").canvas_bg)

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 16
            spacing: 10

            RowLayout {
                Label {
                    text: themeName
                    color: rgba(cat("core").text_color)
                    font.bold: true
                    font.pointSize: 16
                    Layout.fillWidth: true
                }
                ComboBox {
                    id: themeBox
                    Layout.preferredWidth: 200
                    model: themeKeys
                    onActivated: bridge.applyTheme(currentText)
                }
            }

            GridLayout {
                columns: 2
                columnSpacing: 10
                rowSpacing: 8
                Layout.fillWidth: true

                Repeater {
                    model: [
                        ["Panel", cat("panel").bg_normal],
                        ["Accent", cat("core").accent_color],
                        ["Tab", cat("tab").bg_normal],
                        ["Tab active", cat("tab").bg_active],
                        ["Title bar", cat("title_bar").bg_normal],
                        ["Sidebar", cat("sidebar").bg_color],
                        ["Text", cat("core").text_color],
                        ["Tooltip", cat("core").tooltip_bg]
                    ]
                    delegate: RowLayout {
                        required property var modelData
                        Rectangle {
                            width: 48
                            height: 28
                            radius: 4
                            border.width: 1
                            border.color: rgba(cat("core").border_color)
                            color: rgba(modelData[1])
                        }
                        Label {
                            text: modelData[0]
                            color: rgba(cat("core").text_color)
                        }
                    }
                }
            }

            TextArea {
                Layout.fillWidth: true
                Layout.fillHeight: true
                placeholderText: qsTr("Rust-themed editor (panel background, theme text).")
            }

            Label {
                text: qsTr("Colours: lace_rs.build_merged_theme() — no Python theme code.")
                color: rgba(cat("tab").text_normal)
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
        }
    }
}
