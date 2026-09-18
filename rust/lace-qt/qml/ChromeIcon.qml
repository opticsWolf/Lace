import QtQuick

// One themed chrome glyph: a bundled SVG tinted via `manager.iconSvg()`.
// Callers pass an already-resolved "#rrggbb" tint (see `LaceTheme.hex`),
// exactly like the Python provider's `color=` override — so the icon and
// its neighbouring label always come from the same theme token, and
// re-tint for free on theme switches and enabled-state changes. Qt's
// image loader caches by data-URL, so the steady state costs nothing.
Image {
    required property string iconName
    required property string tint
    property int iconSize: 16

    source: (iconName === "" || tint === "")
        ? ""
        : root_icon_manager.iconSvg(iconName, tint)

    // The bridge object — set wherever the glyph is instantiated
    // (`manager: root.manager`); kept behind a plain property because
    // component files have no access to the instantiating scope's ids.
    required property var root_icon_manager

    width: iconSize
    height: iconSize
    fillMode: Image.PreserveAspectFit
    smooth: true
    anchors.centerIn: parent
}
