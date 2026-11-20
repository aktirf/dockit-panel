import QtQuick

Rectangle {
    id: root
    property string text: ""
    property bool sel: false
    property string tip: ""
    signal clicked()

    implicitHeight: 36
    implicitWidth: parent && parent.width > 0 ? Math.min(label.implicitWidth + 28, Math.max(64, parent.width)) : label.implicitWidth + 28
    height: implicitHeight
    width: implicitWidth
    radius: 18
    color: sel ? Theme.accent : Theme.btn
    border.width: 1
    border.color: sel ? Theme.accent : Theme.border3
    Behavior on color { ColorAnimation { duration: 160 } }
    Behavior on border.color { ColorAnimation { duration: 160 } }
    Tip { text: root.tip }

    Txt {
        id: label
        anchors.centerIn: parent
        width: Math.max(0, root.width - 24)
        horizontalAlignment: Text.AlignHCenter
        elide: Text.ElideRight
        text: root.text
        font.pixelSize: 13
        color: root.sel ? "#0B1218" : Theme.soft
        font.weight: root.sel ? Font.DemiBold : Font.Medium
    }
    MouseArea {
        anchors.fill: parent
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }
}
