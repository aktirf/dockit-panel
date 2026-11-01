import QtQuick

Rectangle {
    id: root
    property string text: ""
    property bool sel: false
    signal clicked()

    height: 36
    width: label.implicitWidth + 28
    radius: 18
    color: sel ? Theme.accent : Theme.btn
    border.width: 1
    border.color: sel ? Theme.accent : Theme.border3

    Txt {
        id: label
        anchors.centerIn: parent
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
