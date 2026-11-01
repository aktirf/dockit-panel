import QtQuick

Rectangle {
    id: root
    property string text: ""
    property bool sel: false
    property string tip: ""
    signal clicked()

    height: 36
    width: label.implicitWidth + 28
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
