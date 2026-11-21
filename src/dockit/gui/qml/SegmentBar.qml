import QtQuick
import QtQuick.Layouts

// Clean segmented bar for 2-5 mutually exclusive choices; wraps gracefully on narrow widths.
Rectangle {
    id: root
    property var options: []     // [{ id: "...", label: "...", tip: "..." }]
    property string current: ""
    signal picked(string value)

    Layout.fillWidth: true
    Layout.minimumWidth: 0
    implicitHeight: flowWrap.implicitHeight + 8
    radius: 12
    color: Theme.panel
    border.width: 1
    border.color: Theme.border

    Flow {
        id: flowWrap
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 4
        spacing: 4

        Repeater {
            id: segRepeater
            model: root.options ? root.options.length : 0
            delegate: Rectangle {
                id: segItem
                readonly property var opt: root.options && index < root.options.length ? root.options[index] : ({ id: "", label: "", tip: "" })
                readonly property bool sel: String(opt.id) === String(root.current)
                readonly property int count: Math.max(1, root.options ? root.options.length : 1)
                readonly property real evenW: (flowWrap.width - (count - 1) * flowWrap.spacing) / count
                readonly property real minNeeded: segLbl.implicitWidth + 24

                height: 34
                width: evenW >= minNeeded ? Math.floor(evenW) : Math.min(minNeeded, Math.max(64, flowWrap.width))
                radius: 9
                color: sel ? Theme.accent : (segHover.hovered ? Theme.btn : "transparent")
                scale: segMouse.pressed ? 0.96 : 1.0
                Behavior on color { ColorAnimation { duration: 160; easing.type: Easing.OutCubic } }
                Behavior on scale { NumberAnimation { duration: 100; easing.type: Easing.OutCubic } }

                HoverHandler { id: segHover }

                Txt {
                    id: segLbl
                    anchors.centerIn: parent
                    width: Math.max(0, parent.width - 16)
                    horizontalAlignment: Text.AlignHCenter
                    elide: Text.ElideRight
                    text: String(segItem.opt.label || "")
                    font.pixelSize: 13
                    font.weight: segItem.sel ? Font.DemiBold : Font.Medium
                    color: segItem.sel ? "#0B1218" : Theme.soft
                    Behavior on color { ColorAnimation { duration: 150 } }
                }
                MouseArea {
                    id: segMouse
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.picked(String(segItem.opt.id))
                }
                Tip { text: String(segItem.opt.tip || "") }
            }
        }
    }
}
