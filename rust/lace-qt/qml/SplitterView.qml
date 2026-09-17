import QtQuick
import QtQuick.Controls

// A splitter node: children are created imperatively by ContainerBuilder and
// picked up as SplitView items. `applySizes` restores proportions; all-equal
// sizes (fresh splits) mean "distribute evenly" and are left alone.
SplitView {
    id: splitter
    property int splitOrientation: Qt.Horizontal
    orientation: splitOrientation

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
