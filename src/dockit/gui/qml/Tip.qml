import QtQuick
import QtQuick.Window
import QtQuick.Controls

// Lazy cursor-anchored tooltip: allocates nothing until hovered for 420 ms,
// captures cursor position once (no per-pixel redraws), and stays inside the window.
Item {
    id: root
    property string text: ""
    property bool showing: false
    property real anchorX: 0
    property real anchorY: 0
    anchors.fill: parent

    HoverHandler {
        id: hover
        enabled: root.text !== ""
        onHoveredChanged: {
            if (hovered) {
                showTimer.restart()
            } else {
                showTimer.stop()
                root.showing = false
            }
        }
    }

    Timer {
        id: showTimer
        interval: 420
        onTriggered: {
            if (hover.hovered && root.text !== "") {
                root.anchorX = hover.point.position.x + 14
                root.anchorY = hover.point.position.y + 18
                root.showing = true
            }
        }
    }

    Loader {
        active: root.showing && root.text !== ""
        sourceComponent: ToolTip {
            id: pop
            parent: root
            visible: true
            timeout: 8000
            enter: Transition {
                ParallelAnimation {
                    NumberAnimation { property: "opacity"; from: 0.0; to: 1.0; duration: 140; easing.type: Easing.OutCubic }
                    NumberAnimation { property: "scale"; from: 0.95; to: 1.0; duration: 140; easing.type: Easing.OutCubic }
                }
            }
            exit: Transition {
                NumberAnimation { property: "opacity"; from: 1.0; to: 0.0; duration: 100; easing.type: Easing.OutCubic }
            }
            x: {
                var w = root.Window.window
                var mapped = root.mapToItem(null, root.anchorX, 0)
                if (w && mapped.x + width + 12 > w.width)
                    return Math.max(-mapped.x + 8, root.anchorX - width - 22)
                return root.anchorX
            }
            y: {
                var w = root.Window.window
                var mapped = root.mapToItem(null, 0, root.anchorY)
                if (w && mapped.y + height + 12 > w.height)
                    return Math.max(-mapped.y + 8, root.anchorY - height - 26)
                return root.anchorY
            }
            text: root.text
            contentItem: Text {
                text: root.text
                wrapMode: Text.Wrap
                width: Math.min(implicitWidth, 300)
                color: Theme.text
                font.family: Theme.sans
                font.pixelSize: 13
            }
            background: Rectangle {
                color: Theme.cardInner
                radius: 8
                border.width: 1
                border.color: Theme.border3
            }
        }
    }
}
