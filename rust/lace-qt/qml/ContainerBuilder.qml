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
    // Plain Items take parented children; splitters take boxes via
    // addBox (they run a manual proportional layout, not SplitView).
    function attach(parent, item) {
        if (!parent)
            return
        item.parent = parent
    }
    // Base shares: uneven doc sizes restore proportions, even ones share
    // a nominal 100 (implicit 0/1 collapses dynamic items — probed).
    function nominalShares(sizes, count) {
        var out = []
        var even = true
        for (var i = 1; i < sizes.length; ++i) {
            if (sizes[i] !== sizes[0]) {
                even = false
                break
            }
        }
        for (var j = 0; j < count; ++j) {
            if (even || j >= sizes.length || typeof sizes[j] !== "number")
                out.push(100)
            else
                out.push(Math.max(1, sizes[j]))
        }
        return out
    }
    function buildNode(parent, node, containerIndex, path, counts, registry, share) {
        if (!node || node.type === undefined)
            return null
        var key = containerIndex + "/" + path
        if (share === undefined)
            share = 100
        if (node.type === "Splitter") {
            var orientation = node.orientation === "|" ? Qt.Vertical : Qt.Horizontal
            var splitter = splitterComp.createObject(null, {
                splitOrientation: orientation,
                nodePath: key
            })
            attach(parent, splitter)
            registry.push({ item: splitter, key: key })
            // Persist handle drags back into the doc (silent, no rebuild).
            var persistPath = path
            var persistContainer = containerIndex
            splitter.afterDrag = function(finalShares) {
                builder.manager.setSplitterSizes(persistContainer, persistPath, JSON.stringify(finalShares))
            }
            var children = node.children || []
            // Base shares: uneven doc sizes restore proportions, even ones
            // share a nominal 100.
            var shares = nominalShares(node.sizes || [], children.length)
            for (var i = 0; i < children.length; ++i) {
                var childPath = path === "" ? ("" + i) : (path + "/" + i)
                var child = buildNode(null, children[i], containerIndex, childPath, counts, registry, shares[i])
                if (child)
                    splitter.addBox(child, shares[i])
            }
            return splitter
        }
        if (node.type === "Area") {
            counts.areas++
            counts.widgets += (node.widgets || []).length
            var area = areaComp.createObject(null, {
                manager: builder.manager,
                containerIndex: containerIndex,
                areaPath: path,
                area: node,
                prefW: share,
                prefH: share
            })
            attach(parent, area)
            registry.push({ item: area, key: key })
            return area
        }
        return null
    }

    // Maximize visibility: everything hides except the chain holding the
    // maximized area. Keys outside `ownIndex` belong to another window.
    // (Root paths are "" so registry keys end in "/" — strip it, or the
    // prefix match below misses and a maximize hides the whole tree.)
    function maxVisible(nodeKey, maxKey) {
        if (maxKey === "")
            return true
        var n = nodeKey.endsWith("/") ? nodeKey.slice(0, -1) : nodeKey
        return n === maxKey
            || maxKey.indexOf(n + "/") === 0
            || n.indexOf(maxKey + "/") === 0
    }

    function applyMaximize(registry, maxKey, ownIndex) {
        if (maxKey !== "" && maxKey.split("/")[0] !== String(ownIndex))
            return
        for (var e of registry)
            e.item.visible = maxVisible(e.key, maxKey)
        // Manual splitters position children imperatively: hidden boxes
        // leave gaps unless every splitter re-runs its layout.
        for (var r of registry) {
            if (r.item && r.item.relayout)
                r.item.relayout()
        }
    }
}
