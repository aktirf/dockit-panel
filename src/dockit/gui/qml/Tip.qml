import QtQuick
import QtQuick.Controls

// Hover hint: put  Tip { text: "..." }  inside any item; it covers the item and never blocks clicks.
Item {
    id: root
    property string text: ""
    anchors.fill: parent

    HoverHandler { id: hover }

    ToolTip {
        parent: root
        x: Math.max(0, (root.width - width) / 2)
        y: root.height + 6
        text: root.text
        delay: 450
        timeout: 8000
        visible: root.text !== "" && hover.hovered
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
