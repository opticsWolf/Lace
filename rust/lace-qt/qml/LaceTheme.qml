pragma Singleton
import QtQuick

// QML face of the Rust theme engine: `manager.themeJson` (schema defaults
// merged under the active preset, exactly like `get_all()`) parsed into
// `doc`, with typed accessors. Views bind `LaceTheme.color("tab.bg_active")`
// and re-evaluate whenever `doc` is replaced. Missing tokens yield
// `undefined` (never a crash); the smoke test pins the tokens it needs.
QtObject {
    id: theme

    property var doc: ({})
    property string presetName: ""

    function update(json, name) {
        try {
            doc = JSON.parse(json)
            presetName = name
        } catch (e) {
            console.warn("LaceTheme: theme snapshot did not parse: " + e)
        }
    }

    function raw(path) {
        var parts = path.split(".")
        if (parts.length !== 2)
            return undefined
        var category = doc[parts[0]]
        if (category === undefined)
            return undefined
        return category[parts[1]]
    }

    function color(path) {
        var v = raw(path)
        if (!v || v.length !== 4)
            return undefined
        return Qt.rgba(v[0] / 255, v[1] / 255, v[2] / 255, v[3] / 255)
    }

    function num(path) {
        var v = raw(path)
        return (typeof v === "number") ? v : undefined
    }

    function flag(path) {
        var v = raw(path)
        return (typeof v === "boolean") ? v : undefined
    }

    function str(path) {
        var v = raw(path)
        return (typeof v === "string") ? v : undefined
    }

    // PANEL.content_margin in scalar | [h, t] | [l, t, r] | [l, t, r, b]
    // form, expanded to explicit edges (mirrors the Python layout mapping:
    // (8, 2) -> (8, 2, 8, 8); (6, 4, 6) -> (6, 4, 6, 4)).
    function margins() {
        var v = raw("panel.content_margin")
        if (typeof v === "number")
            return { left: v, top: v, right: v, bottom: v }
        if (v && v.length === 2)
            return { left: v[0], top: v[1], right: v[0], bottom: v[0] }
        if (v && v.length === 3)
            return { left: v[0], top: v[1], right: v[2], bottom: v[1] }
        if (v && v.length === 4)
            return { left: v[0], top: v[1], right: v[2], bottom: v[3] }
        return { left: 0, top: 0, right: 0, bottom: 0 }
    }
}
