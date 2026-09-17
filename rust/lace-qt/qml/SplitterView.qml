import QtQuick
import QtQuick.Controls

import com.lace.dock 1.0

// A splitter node: children are created imperatively by ContainerBuilder and
// picked up as SplitView items. `applySizes` restores proportions; all-equal
// sizes (fresh splits) mean "distribute evenly" and are left alone.
SplitView {
    id: splitter
    property int splitOrientation: Qt.Horizontal
    orientation: splitOrientation

    handle: Rectangle {
        implicitWidth: LaceTheme.num("splitter.total_width") || 7
        implicitHeight: LaceTheme.num("splitter.total_width") || 7
        color: handleHover.hovered
            ? (LaceTheme.color("splitter.handle_hover_color") || "grey")
            : (LaceTheme.color("splitter.handle_color") || "darkgrey")
        HoverHandler {
            id: handleHover
        }
    }

    function applySizes(sizes) {
        if (sizes.length !== splitter.count || splitter.count === 0)
            return
        var even = true
        for (var i = 1; i < sizes.length; ++i) {
            if (sizes[i] !== sizes[0]) {
                even = false
                break
            }
        }
        if (even)
            return
        for (var j = 0; j < sizes.length; ++j) {
            var child = splitter.itemAt(j)
            if (splitter.orientation === Qt.Horizontal)
                child.SplitView.preferredWidth = sizes[j]
            else
                child.SplitView.preferredHeight = sizes[j]
        }
    }
}
