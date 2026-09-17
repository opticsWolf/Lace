import QtQuick

// Shared imperative subtree builder: both the main view and the floating
// windows construct splitter/area items through here, so the two never drift.
Item {
    id: builder
    required property var manager
    visible: false

    property Component splitterComp: SplitterView {}
    property Component areaComp: AreaView {}
    property Component floatComp: FloatingView {}

    // Build `node` (a root_splitter-shaped dict) under `parent`.
    // `path` is the "/"-joined child indices of the node ("", "0", "0/1"...).
    // Counts areas/widgets into `counts` for the smoke log; registers every
    // created node item into `registry` as {item, key} for maximize.
    function buildNode(parent, node, containerIndex, path, counts, registry) {
        if (!node || node.type === undefined)
            return null
        var key = containerIndex + "/" + path
        if (node.type === "Splitter") {
            var orientation = node.orientation === "|" ? Qt.Vertical : Qt.Horizontal
            var splitter = splitterComp.createObject(parent, {
                splitOrientation: orientation,
                nodePath: key
            })
            registry.push({ item: splitter, key: key })
            var children = node.children || []
            for (var i = 0; i < children.length; ++i) {
                var childPath = path === "" ? ("" + i) : (path + "/" + i)
                buildNode(splitter, children[i], containerIndex, childPath, counts, registry)
            }
            splitter.applySizes(node.sizes || [])
            return splitter
        }
        if (node.type === "Area") {
            counts.areas++
            counts.widgets += (node.widgets || []).length
            var area = areaComp.createObject(parent, {
                manager: builder.manager,
                containerIndex: containerIndex,
                areaPath: path,
                area: node
            })
            registry.push({ item: area, key: key })
            return area
        }
        return null
    }

    // Maximize visibility: everything hides except the chain holding the
    // maximized area. Keys outside `ownIndex` belong to another window.
    function maxVisible(nodeKey, maxKey) {
        if (maxKey === "")
            return true
        return nodeKey === maxKey
            || maxKey.indexOf(nodeKey + "/") === 0
            || nodeKey.indexOf(maxKey + "/") === 0
    }

    function applyMaximize(registry, maxKey, ownIndex) {
        if (maxKey !== "" && maxKey.split("/")[0] !== String(ownIndex))
            return
        for (var e of registry)
            e.item.visible = maxVisible(e.key, maxKey)
    }
}
