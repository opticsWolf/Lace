import QtQuick

// Renders the main container of the manager's layout snapshot and owns the
// floating windows. Rebuilds everything on `layoutJsonChanged`; per-tab
// current switches are silent (see LaceManager.setCurrentTab) so tab-local
// state such as typed text survives them.
Item {
    id: view
    required property var manager
    property var doc: null
    property var floats: []
    // Last rebuild tally, for the headless smoke self-test.
    property var lastCounts: ({ areas: 0, widgets: 0, floats: 0 })

    ContainerBuilder {
        id: builder
        manager: view.manager
    }

    Item {
        id: mainArea
        anchors.fill: parent
    }

    function refresh() {
        try {
            doc = JSON.parse(manager.layoutJson)
        } catch (e) {
            console.warn("lace dock: layout snapshot did not parse: " + e)
            return
        }
        rebuild()
    }

    function clearChildren(item) {
        for (var i = item.children.length - 1; i >= 0; --i)
            item.children[i].destroy()
    }

    function destroyFloats() {
        for (var w of floats) {
            w.close()
            w.destroy()
        }
        floats = []
    }

    function rebuild() {
        clearChildren(mainArea)
        destroyFloats()
        if (!doc || !doc.containers)
            return
        var counts = { areas: 0, widgets: 0, floats: 0 }
        for (var c = 0; c < doc.containers.length; ++c) {
            var container = doc.containers[c]
            if (container.is_main) {
                builder.buildNode(mainArea, container.data.root_splitter, c, "", counts)
            } else {
                var win = builder.floatComp.createObject(null, {
                    manager: view.manager,
                    doc: view.doc,
                    containerIndex: c,
                    builder: builder,
                    cid: container.id || ("float-" + c)
                })
                floats.push(win)
                counts.floats++
            }
        }
        console.log("lace dock: areas=" + counts.areas
            + " widgets=" + counts.widgets + " floats=" + counts.floats)
        view.lastCounts = counts
    }

    Component.onCompleted: refresh()

    Connections {
        target: view.manager
        function onLayoutJsonChanged() { view.refresh() }
    }
}
