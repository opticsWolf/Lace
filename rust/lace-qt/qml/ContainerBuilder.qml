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
    // Counts areas/widgets into `counts` for the smoke log.
    function buildNode(parent, node, containerIndex, path, counts) {
        if (!node || node.type === undefined)
            return null
        if (node.type === "Splitter") {
            var orientation = node.orientation === "|" ? Qt.Vertical : Qt.Horizontal
            var splitter = splitterComp.createObject(parent, { splitOrientation: orientation })
            var children = node.children || []
            for (var i = 0; i < children.length; ++i) {
                var childPath = path === "" ? ("" + i) : (path + "/" + i)
                buildNode(splitter, children[i], containerIndex, childPath, counts)
            }
            splitter.applySizes(node.sizes || [])
            return splitter
        }
        if (node.type === "Area") {
            counts.areas++
            counts.widgets += (node.widgets || []).length
            return areaComp.createObject(parent, {
                manager: builder.manager,
                containerIndex: containerIndex,
                areaPath: path,
                area: node
            })
        }
        return null
    }
}
