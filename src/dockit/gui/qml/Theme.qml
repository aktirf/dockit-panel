pragma Singleton
import QtQuick

QtObject {
    readonly property color bg: "#0F1317"
    readonly property color panel: "#12181D"
    readonly property color card: "#171D23"
    readonly property color cardInner: "#1B222A"
    readonly property color border: "#232C35"
    readonly property color border2: "#26313B"
    readonly property color border3: "#2A343F"
    readonly property color btn: "#1F2830"
    readonly property color text: "#E6EBF0"
    readonly property color soft: "#C9D3DC"
    readonly property color muted: "#9AA7B4"
    readonly property color navText: "#AEBBC7"
    readonly property color navActive: "#1C2834"
    readonly property color accent: "#5AB0FF"
    readonly property color ok: "#4CC38A"
    readonly property color okText: "#7FE0AE"
    readonly property color warn: "#F5C56B"
    readonly property color info: "#B4BEFF"
    readonly property color err: "#FF9E9E"
    readonly property string sans: "IBM Plex Sans"
    readonly property string mono: "IBM Plex Mono"

    function statusColor(kind) {
        if (kind === "ok") return okText
        if (kind === "setup") return warn
        if (kind === "root") return info
        if (kind === "no") return err
        return soft
    }
    function statusBg(kind) {
        if (kind === "ok") return Qt.rgba(0.298, 0.765, 0.541, 0.14)
        if (kind === "setup") return Qt.rgba(0.961, 0.773, 0.420, 0.14)
        if (kind === "root") return Qt.rgba(0.557, 0.608, 1.0, 0.16)
        if (kind === "no") return Qt.rgba(1.0, 0.478, 0.478, 0.14)
        return "#1F2830"
    }
    function statusIcon(kind) {
        if (kind === "ok") return "check"
        if (kind === "setup") return "wrench"
        if (kind === "root") return "lock"
        if (kind === "no") return "x"
        return ""
    }
}
