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
    // Node registry for maximize + the main container's index.
    property var nodeRegistry: []
    property int mainIndex: 0

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

    // Reconcile float windows with the document by container id: windows
    // whose container survives are kept (no flicker, no close storms) and
    // asked to refresh their own tree; removed ones are torn down with the
    // guard set so their onClosing does NOT dock anything back.
    // (Unconditional destroy used to close every float on every rebuild —
    // the close handler then docked each float back, so floats could never
    // survive a structural op and lastError filled with stale failures.)
    function syncFloats() {
        var wanted = {}
        for (var c = 0; c < doc.containers.length; ++c) {
            if (!doc.containers[c].is_main)
                wanted[doc.containers[c].id || ("float-" + c)] = c
        }
        var keep = []
        for (var w of floats) {
            if (w && wanted[w.cid] !== undefined) {
                keep.push(w)
                delete wanted[w.cid]
            } else if (w) {
                w.teardown = true
                w.close()
                w.destroy()
            }
        }
        floats = keep
        for (var cid in wanted) {
            var win = builder.floatComp.createObject(null, {
                manager: view.manager,
                doc: view.doc,
                containerIndex: wanted[cid],
                builder: builder,
                cid: cid
            })
            if (win)
                floats.push(win)
        }
        floats = floats
        for (var k of floats) {
            if (k.refreshContent)
                k.refreshContent()
        }
        return floats.length
    }

    function rebuild() {
        clearChildren(mainArea)
        view.nodeRegistry = []
        if (!doc || !doc.containers)
            return
        var counts = { areas: 0, widgets: 0, floats: 0 }
        for (var c = 0; c < doc.containers.length; ++c) {
            var container = doc.containers[c]
            if (container.is_main) {
                view.mainIndex = c
                var rootItem = builder.buildNode(mainArea, container.data.root_splitter, c, "", counts, view.nodeRegistry)
                // Plain Items don't lay out children: the root fills manually
                // (nested items are positioned by the manual SplitterView).
                if (rootItem)
                    rootItem.anchors.fill = mainArea
            }
        }
        counts.floats = syncFloats()
        console.log("lace dock: areas=" + counts.areas
            + " widgets=" + counts.widgets + " floats=" + counts.floats)
        view.lastCounts = counts
        builder.applyMaximize(view.nodeRegistry, manager.maximizedArea, view.mainIndex)
    }

    OverlayCross {
        manager: view.manager
        mainIndex: view.mainIndex
    }

    Component.onCompleted: refresh()

    Connections {
        target: view.manager
        function onLayoutJsonChanged() { view.refresh() }
        function onMaximizedAreaChanged() {
            builder.applyMaximize(view.nodeRegistry, view.manager.maximizedArea, view.mainIndex)
        }
    }
}
