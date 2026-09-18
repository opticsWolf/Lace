import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import com.lace.dock 1.0

// One dock area: a themed frame, a single-row header (tabs menu, tab
// strip, pin / undock / maximize / close — no title text, the strip is
// just a container) over a StackLayout. Tab switches sync the document
// silently (no rebuild); closes, reopen toggles and pins re-emit (rebuild).
Item {
    id: root
    required property var manager
    required property var docksView
    required property int containerIndex
    required property string areaPath
    required property var area
    // Base share from the layout doc (see ContainerBuilder.nominalShares).
    property double prefW: 100
    property double prefH: 100
    implicitWidth: prefW
    implicitHeight: prefH
    SplitView.fillWidth: true
    SplitView.fillHeight: true

    property var widgets: area.widgets || []
    property string focusKey: containerIndex + "/" + areaPath
    property bool areaActive: manager.focusedArea === focusKey
    // True while the tab strip holds more tabs than fit: chevron buttons
    // appear and the current tab is auto-scrolled into view.
    property bool tabOverflow: false
    // DockFlags bits (mirrors rust/lace-core/src/config.rs — pinned).
    property int flagAlwaysShowTabs: 4
    property int flagShowTabClose: 8
    property int flagActiveTabClose: 16
    property int flagAreaClose: 32
    property int flagAreaCloseClosesTab: 64
    property int flagAreaUndock: 128
    property int flagAreaPin: 256
    property int flagAreaMaximize: 512
    property int flagAreaTabsMenu: 2048
    property int flagMiddleClose: 4096
    property int flagFloatableTabs: 8192
    property int flagPinnableTabs: 16384
    function hasFlag(f) { return (manager.dockFlags & f) !== 0 }
    // Resolved chrome tints (Python: title-bar `button_color` /
    // `button_disable_clr`, tab `close_btn_color`). Hex strings for
    // manager.iconSvg(); the "||" fallbacks match the provider default.
    property string chromeTint: LaceTheme.hex("title_bar.button_color") || "#C8CDD7"
    property string chromeDisabled: LaceTheme.hex("title_bar.button_disable_clr") || "#C8CDD7"
    property int chromeSize: LaceTheme.num("title_bar.button_icon_size") || 16
    property string tabCloseTint: LaceTheme.hex("tab.close_btn_color") || "#C8CDD7"
    property int tabCloseSize: LaceTheme.num("tab.close_btn_icon_size") || 14
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
    property string currentName: {
        var w = widgets[bar.currentIndex]
        return w ? w.name : ""
    }

    Rectangle {
        anchors.fill: parent
        color: "transparent"
        border.color: root.areaActive
            ? (LaceTheme.color("core.focus_border_color") || "blue")
            : (LaceTheme.color("core.border_color") || "transparent")
        border.width: LaceTheme.num("core.border_width") || 0
        radius: LaceTheme.num("core.corner_radius") || 0
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // Active-tab indicator strip: top, bottom, or absent for "none".
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: LaceTheme.num("tab.indicator_width") || 0
            visible: (LaceTheme.str("tab.indicator_position") || "bottom") === "top"
            color: LaceTheme.color("tab.indicator_color") || "transparent"
        }

        // Single-row header: the strip is just a container — tabs menu,
        // scroll chevrons, the tab strip itself, then pin / undock /
        // maximize / close. No title text (Python DockAreaTitleBar parity).
        // Button visibility follows the DockFlags mask (manager.dockFlags).
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 30
            color: root.areaActive
                ? (LaceTheme.color("title_bar.bg_active") || "grey")
                : (LaceTheme.color("title_bar.bg_normal") || "darkgrey")
            // Drag sensor FIRST (bottom of z-order): the buttons and tabs
            // above receive their presses; empty strip gaps fall through
            // here. Pure mouse tracker: hover is computed geometrically
            // (docksView.hoverMove) and the drop commits the proven move
            // ops on release.
            MouseArea {
                id: titleMouse
                anchors.fill: parent
                acceptedButtons: Qt.LeftButton
                property string pendingName: ""
                property var pressPos: null
                function viewPos(mx, my) {
                    return titleMouse.mapToItem(root.docksView, mx, my)
                }
                function endGesture() {
                    pendingName = ""
                    pressPos = null
                }
                onPressed: function(mouse) {
                    pressPos = Qt.point(mouse.x, mouse.y)
                    pendingName = root.currentName
                }
                onClicked: function(event) {
                    root.manager.focusedArea = root.focusKey
                    event.accepted = false
                }
                onDoubleClicked: root.manager.toggleMaximize(root.focusKey)
                function armDrag() {
                    if (pendingName !== "" && root.manager.beginDrag(pendingName))
                        root.docksView.dragName = pendingName
                }
                onPressAndHold: titleMouse.armDrag()
                onPositionChanged: function(mouse) {
                    if (!pressed || pressPos === null)
                        return
                    if (!root.manager.dragActive) {
                        var dx = mouse.x - pressPos.x
                        var dy = mouse.y - pressPos.y
                        if (dx * dx + dy * dy > 64)
                            titleMouse.armDrag()
                    } else {
                        var p = viewPos(mouse.x, mouse.y)
                        root.docksView.hoverMove(p.x, p.y)
                    }
                }
                onReleased: function(mouse) {
                    if (root.manager.dragActive) {
                        var p = viewPos(mouse.x, mouse.y)
                        var hit = root.docksView.hoverMove(p.x, p.y)
                        if (hit !== null) {
                            if (hit.kind === "C")
                                root.manager.commitContainerDrop(hit.container, hit.edge)
                            else
                                root.manager.commitSectionDrop(hit.container, hit.path, hit.edge)
                        } else {
                            root.manager.floatWidget(pendingName !== "" ? pendingName : root.currentName)
                            root.manager.cancelDrag()
                        }
                        root.docksView.clearHover()
                    }
                    endGesture()
                }
                onCanceled: {
                    if (root.manager.dragActive) {
                        root.manager.cancelDrag()
                        root.docksView.clearHover()
                    }
                    endGesture()
                }
            }
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 4
                anchors.rightMargin: 4
                spacing: 2
                Button {
                    id: menuBtn
                    flat: true
                    visible: root.hasFlag(root.flagAreaTabsMenu)
                    implicitHeight: 24
                    implicitWidth: 26
                    ToolTip.text: qsTr("Tabs menu")
                    ToolTip.visible: hovered
                    ToolTip.delay: 500
                    contentItem: ChromeIcon {
                        root_icon_manager: root.manager
                        iconName: "tabs_menu"
                        tint: root.chromeTint
                        iconSize: root.chromeSize
                    }
                    background: Rectangle {
                        color: parent.hovered
                            ? (LaceTheme.color("title_bar.button_hover_bg") || "grey")
                            : "transparent"
                        radius: 3
                    }
                    onClicked: tabsMenu.open()
                    Popup {
                        id: tabsMenu
                        x: 0
                        y: parent.height + 2
                        width: 220
                        modal: true
                        dim: false
                        focus: true
                        background: Rectangle {
                            color: LaceTheme.color("panel.bg_normal") || "#1e1e1e"
                            border.color: LaceTheme.color("core.border_color") || "#555"
                            border.width: 1
                            radius: 4
                        }
                        contentItem: ColumnLayout {
                            spacing: 0
                            Repeater {
                                model: root.widgets
                                delegate: Item {
                                    required property var modelData
                                    required property int index
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 26
                                    Label {
                                        anchors.fill: parent
                                        anchors.leftMargin: 10
                                        anchors.rightMargin: 6
                                        text: modelData.name + (modelData.closed ? " (closed)" : "")
                                        color: index === bar.currentIndex
                                            ? (LaceTheme.color("tab.indicator_color") || "white")
                                            : (LaceTheme.color("tab.text_normal") || "white")
                                        font.bold: index === bar.currentIndex
                                        elide: Text.ElideRight
                                        verticalAlignment: Text.AlignVCenter
                                    }
                                    MouseArea {
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        onClicked: {
                                            bar.currentIndex = index
                                            root.manager.setCurrentTab(root.containerIndex, root.areaPath, modelData.name)
                                            tabsMenu.close()
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            Rectangle {
                visible: root.tabOverflow && bar.visible
                Layout.preferredWidth: visible ? 20 : 0
                Layout.preferredHeight: 24
                color: tabPrev.containsMouse
                    ? (LaceTheme.color("title_bar.button_hover_bg") || "grey")
                    : (LaceTheme.color("tab.bg_normal") || "#2d2d2d")
                border.width: 1
                border.color: LaceTheme.color("tab.indicator_color") || "transparent"
                radius: 3
                Label {
                    anchors.centerIn: parent
                    text: "<"
                    color: LaceTheme.color("title_bar.text_normal") || "white"
                }
                MouseArea {
                    id: tabPrev
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: bar.currentIndex = Math.max(0, bar.currentIndex - 1)
                }
            }

        TabBar {
            id: bar
            objectName: "areaTabs_" + root.areaPath
            Layout.fillWidth: true
            visible: root.widgets.length > 1 || root.hasFlag(root.flagAlwaysShowTabs)
            currentIndex: root.initialIndex
            background: Rectangle {
                color: LaceTheme.color("tab.bg_normal") || "transparent"
            }
            // The strip is a Flickable ListView under the hood: reach in
            // (same technique as the big dock frameworks) to keep the
            // current tab scrolled into view when tabs overflow.
            function tabListView() {
                for (var i = 0; i < children.length; ++i) {
                    if (children[i].toString().indexOf("QQuickListView") === 0)
                        return children[i]
                }
                return null
            }
            function refreshOverflow() {
                var lv = tabListView()
                root.tabOverflow = !!lv && lv.width > 0 && lv.contentWidth > lv.width + 1
            }
            property int ensureTries: 0
            function ensureTabVisible() {
                var lv = tabListView()
                if (!lv) {
                    // The strip's internal ListView can lag behind bar
                    // completion (model populates async): retry a few ticks.
                    if (ensureTries < 10) {
                        ensureTries++
                        Qt.callLater(ensureTabVisible)
                    }
                    return
                }
                ensureTries = 0
                // The template enforces a highlight range on selection
                // changes and re-asserts it when the model repopulates,
                // which fights manual positioning: take over scrolling
                // entirely (no highlight is rendered anyway). Re-assert on
                // every change; our deferred call runs last and wins.
                lv.highlightRangeMode = ListView.NoHighlightRange
                lv.preferredHighlightBegin = 0
                lv.preferredHighlightEnd = lv.width
                // Unclipped, tabs scrolled out of view paint over the
                // flanking chevrons (paint order hides the left one).
                lv.clip = true
                lv.positionViewAtIndex(currentIndex, ListView.Contain)
                refreshOverflow()
            }
            onWidthChanged: Qt.callLater(ensureTabVisible)
            onCountChanged: Qt.callLater(ensureTabVisible)
            Component.onCompleted: Qt.callLater(ensureTabVisible)

            Repeater {
                model: root.widgets
                TabButton {
                    id: tabBtn
                    required property var modelData
                    required property int index
                    // Never let the strip compress tabs into unreadable
                    // stubs: keep full implicit width so real overflow (and
                    // the chevron + ensure-visible machinery) engages.
                    width: implicitWidth
                    // Sensor overlay over the label (the × stays on top and
                    // clickable): pure tracker like the title strip — hover is
                    // geometric, the drop commits on release. Clicks forward
                    // to the tab (selection); hold/move drags.
                    MouseArea {
                        id: tabSensor
                        anchors.fill: parent
                        anchors.rightMargin: 26
                        acceptedButtons: Qt.LeftButton | Qt.MiddleButton
                        property string pendingTab: ""
                        property var pressTabPos: null
                        function viewPos(mx, my) {
                            return tabSensor.mapToItem(root.docksView, mx, my)
                        }
                        function endGesture() {
                            pendingTab = ""
                            pressTabPos = null
                        }
                        onPressed: function(mouse) {
                            if (mouse.button !== Qt.LeftButton)
                                return
                            pendingTab = tabBtn.modelData.name
                            pressTabPos = Qt.point(mouse.x, mouse.y)
                        }
                        onClicked: function(mouse) {
                            if (mouse.button === Qt.MiddleButton) {
                                if (root.hasFlag(root.flagMiddleClose))
                                    root.manager.setWidgetClosed(tabBtn.modelData.name, true)
                                return
                            }
                            bar.currentIndex = tabBtn.index
                            root.manager.setCurrentTab(root.containerIndex, root.areaPath, tabBtn.modelData.name)
                        }
                        function armTabDrag() {
                            if (pendingTab !== "" && root.manager.beginDrag(pendingTab))
                                root.docksView.dragName = pendingTab
                        }
                        onPressAndHold: armTabDrag()
                        onPositionChanged: function(mouse) {
                            if (!pressed || pressTabPos === null)
                                return
                            if (!root.manager.dragActive) {
                                var dx = mouse.x - pressTabPos.x
                                var dy = mouse.y - pressTabPos.y
                                if (dx * dx + dy * dy > 64)
                                    armTabDrag()
                            } else {
                                var p = viewPos(mouse.x, mouse.y)
                                root.docksView.hoverMove(p.x, p.y)
                            }
                        }
                        onReleased: function(mouse) {
                            if (root.manager.dragActive) {
                                var p = viewPos(mouse.x, mouse.y)
                                var hit = root.docksView.hoverMove(p.x, p.y)
                                if (hit !== null) {
                                    if (hit.kind === "C")
                                        root.manager.commitContainerDrop(hit.container, hit.edge)
                                    else
                                        root.manager.commitSectionDrop(hit.container, hit.path, hit.edge)
                                } else {
                                    root.manager.floatWidget(pendingTab !== "" ? pendingTab : tabBtn.modelData.name)
                                    root.manager.cancelDrag()
                                }
                                root.docksView.clearHover()
                            }
                            endGesture()
                        }
                        onCanceled: {
                            if (root.manager.dragActive) {
                                root.manager.cancelDrag()
                                root.docksView.clearHover()
                            }
                            endGesture()
                        }
                    }
                    implicitWidth: tabRow.implicitWidth + 12
                    implicitHeight: 30
                    contentItem: RowLayout {
                        id: tabRow
                        spacing: 4
                        Label {
                            text: modelData.name + (modelData.closed ? " (closed)" : "")
                            color: parent.parent.checked
                                ? (LaceTheme.color("tab.text_active") || "white")
                                : (LaceTheme.color("tab.text_normal") || "white")
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                        }
                        Button {
                            flat: true
                            visible: root.hasFlag(root.flagShowTabClose)
                                && (!root.hasFlag(root.flagActiveTabClose) || tabBtn.index === bar.currentIndex)
                            implicitWidth: 22
                            implicitHeight: 22
                            contentItem: ChromeIcon {
                                root_icon_manager: root.manager
                                iconName: "close_tab"
                                tint: root.tabCloseTint
                                iconSize: root.tabCloseSize
                            }
                            background: Rectangle {
                                color: parent.hovered
                                    ? (LaceTheme.color("tab.close_btn_bg_hover") || "grey")
                                    : "transparent"
                                radius: 3
                            }
                            // Closed tabs reopen via their × (the footer toggle is gone).
                            onClicked: modelData.closed
                                ? root.manager.setWidgetClosed(modelData.name, false)
                                : root.manager.removeWidget(modelData.name)
                        }
                    }
                    background: Rectangle {
                        color: parent.checked
                            ? (LaceTheme.color("tab.bg_active") || "grey")
                            : (parent.hovered
                                ? (LaceTheme.color("tab.bg_hover") || "dimgrey")
                                : (LaceTheme.color("tab.bg_normal") || "darkgrey"))
                        radius: LaceTheme.num("tab.corner_radius") || 0
                    }
                    onClicked: {
                        root.manager.setCurrentTab(root.containerIndex, root.areaPath, modelData.name)
                    }
                }
            }

            onCurrentIndexChanged: {
                var w = root.widgets[currentIndex]
                if (w)
                    root.manager.setCurrentTab(root.containerIndex, root.areaPath, w.name)
                Qt.callLater(ensureTabVisible)
            }
        }

            Rectangle {
                visible: root.tabOverflow && bar.visible
                Layout.preferredWidth: visible ? 20 : 0
                Layout.preferredHeight: 24
                color: tabNext.containsMouse
                    ? (LaceTheme.color("title_bar.button_hover_bg") || "grey")
                    : (LaceTheme.color("tab.bg_normal") || "#2d2d2d")
                border.width: 1
                border.color: LaceTheme.color("tab.indicator_color") || "transparent"
                radius: 3
                Label {
                    anchors.centerIn: parent
                    text: ">"
                    color: LaceTheme.color("title_bar.text_normal") || "white"
                }
                MouseArea {
                    id: tabNext
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: bar.currentIndex = Math.min(bar.count - 1, bar.currentIndex + 1)
                }
            }
            Button {
                flat: true
                visible: root.hasFlag(root.flagAreaPin)
                enabled: root.currentName !== "" && root.hasFlag(root.flagPinnableTabs)
                implicitHeight: 24
                implicitWidth: 26
                ToolTip.text: qsTr("Pin to sidebar")
                ToolTip.visible: hovered
                ToolTip.delay: 500
                contentItem: ChromeIcon {
                    root_icon_manager: root.manager
                    iconName: "pin"
                    tint: parent.enabled ? root.chromeTint : root.chromeDisabled
                    iconSize: root.chromeSize
                }
                background: Rectangle {
                    color: parent.hovered
                        ? (LaceTheme.color("title_bar.button_hover_bg") || "grey")
                        : "transparent"
                    radius: 3
                }
                onClicked: root.manager.pinWidget(root.currentName, "left")
            }
            Button {
                flat: true
                visible: root.hasFlag(root.flagAreaUndock) && root.containerIndex === 0
                enabled: root.currentName !== "" && root.hasFlag(root.flagFloatableTabs)
                implicitHeight: 24
                implicitWidth: 26
                ToolTip.text: qsTr("Float")
                ToolTip.visible: hovered
                ToolTip.delay: 500
                contentItem: ChromeIcon {
                    root_icon_manager: root.manager
                    iconName: "float"
                    tint: parent.enabled ? root.chromeTint : root.chromeDisabled
                    iconSize: root.chromeSize
                }
                background: Rectangle {
                    color: parent.hovered
                        ? (LaceTheme.color("title_bar.button_hover_bg") || "grey")
                        : "transparent"
                    radius: 3
                }
                onClicked: root.manager.floatWidget(root.currentName)
            }
            Button {
                flat: true
                visible: root.hasFlag(root.flagAreaMaximize)
                implicitHeight: 24
                ToolTip.text: root.manager.maximizedArea === root.focusKey ? qsTr("Restore") : qsTr("Maximize")
                ToolTip.visible: hovered
                ToolTip.delay: 500
                contentItem: ChromeIcon {
                    root_icon_manager: root.manager
                    iconName: root.manager.maximizedArea === root.focusKey ? "restore" : "maximize"
                    tint: root.chromeTint
                    iconSize: root.chromeSize
                }
                background: Rectangle {
                    color: parent.hovered
                        ? (LaceTheme.color("title_bar.button_hover_bg") || "grey")
                        : "transparent"
                    radius: 3
                }
                onClicked: root.manager.toggleMaximize(root.focusKey)
            }
            Button {
                flat: true
                visible: root.hasFlag(root.flagAreaClose)
                enabled: root.currentName !== ""
                implicitHeight: 24
                implicitWidth: 26
                ToolTip.text: root.hasFlag(root.flagAreaCloseClosesTab) ? qsTr("Close tab") : qsTr("Close group")
                ToolTip.visible: hovered
                ToolTip.delay: 500
                contentItem: ChromeIcon {
                    root_icon_manager: root.manager
                    iconName: "close"
                    tint: parent.enabled ? root.chromeTint : root.chromeDisabled
                    iconSize: root.chromeSize
                }
                background: Rectangle {
                    color: parent.hovered
                        ? (LaceTheme.color("title_bar.button_hover_bg") || "grey")
                        : "transparent"
                    radius: 3
                }
                onClicked: {
                    if (root.hasFlag(root.flagAreaCloseClosesTab)) {
                        if (root.currentName !== "")
                            root.manager.setWidgetClosed(root.currentName, true)
                    } else {
                        root.manager.closeArea(root.containerIndex, root.areaPath)
                    }
                }
            }
            }
        }

        // Active-tab indicator strip (bottom by default, top on request,
        // absent for "none").
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: LaceTheme.num("tab.indicator_width") || 0
            visible: (LaceTheme.str("tab.indicator_position") || "bottom") === "bottom"
            color: LaceTheme.color("tab.indicator_color") || "transparent"
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: bar.currentIndex

            Repeater {
                model: root.widgets
                WidgetCard {
                    required property var modelData
                    manager: root.manager
                    widgetName: modelData.name
                    widgetClosed: !!modelData.closed
                }
            }
        }
    }
}
