import QtQuick
import QtQuick.Layouts

// One line "name ........ value" used in cards. Never overlaps even in narrow tiled windows.
Item {
    id: root
    property string label: ""
    property string value: ""
    property color valueColor: Theme.text

    implicitHeight: 24
    Layout.fillWidth: true
    Layout.minimumWidth: 0

    Txt {
        id: valueTxt
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        width: Math.min(implicitWidth, Math.max(80, root.width * 0.58))
        text: root.value
        color: root.valueColor
        font.family: Theme.mono
        font.pixelSize: 13
        elide: Text.ElideRight
        horizontalAlignment: Text.AlignRight
    }
    Txt {
        id: labelTxt
        anchors.left: parent.left
        anchors.right: valueTxt.left
        anchors.rightMargin: 12
        anchors.verticalCenter: parent.verticalCenter
        text: root.label
        color: Theme.muted
        font.pixelSize: 13
        elide: Text.ElideRight
    }
}
