import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// One dock area: a TabBar over a StackLayout. Tab switches sync the document
// silently (no rebuild); closes and reopen toggles re-emit (rebuild).
Item {
    id: root
    required property var manager
    required property int containerIndex
    required property string areaPath
    required property var area

    property var widgets: area.widgets || []
    property int initialIndex: {
        var names = []
        for (var w of widgets)
            names.push(w.name)
        var i = names.indexOf(area.current)
        if (i >= 0)
            return i
        for (var j = 0; j < widgets.length; ++j) {
            if (!widgets[j].closed)
                return j
        }
        return 0
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        TabBar {
            id: bar
            Layout.fillWidth: true
            currentIndex: area.initialIndex

            Repeater {
                model: area.widgets
                TabButton {
                    required property var modelData
                    required property int index
                    contentItem: RowLayout {
                        spacing: 4
                        Label {
                            text: modelData.name + (modelData.closed ? " (closed)" : "")
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                        }
                        Button {
                            text: "×"
                            flat: true
                            implicitWidth: 22
                            implicitHeight: 22
                            onClicked: area.manager.removeWidget(modelData.name)
                        }
                    }
                    onClicked: {
                        // TabButton already switched currentIndex; sync doc.
                        area.manager.setCurrentTab(area.containerIndex, area.areaPath, modelData.name)
                    }
                }
            }

            onCurrentIndexChanged: {
                var w = area.widgets[currentIndex]
                if (w)
                    area.manager.setCurrentTab(area.containerIndex, area.areaPath, w.name)
            }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: bar.currentIndex

            Repeater {
                model: area.widgets
                WidgetCard {
                    required property var modelData
                    manager: area.manager
                    widgetName: modelData.name
                    widgetClosed: !!modelData.closed
                }
            }
        }
    }
}
