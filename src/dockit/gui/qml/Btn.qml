import QtQuick

Rectangle {
    id: root
    property string text: ""
    property bool primary: false
    signal clicked()

    implicitHeight: 44
    implicitWidth: label.implicitWidth + 36
    radius: 10
    color: primary ? Theme.accent : Theme.btn
    border.width: 1
    border.color: primary ? Theme.accent : Theme.border3
    opacity: !enabled ? 0.45 : (mouse.containsMouse ? 0.88 : 1)

    Txt {
        id: label
        anchors.centerIn: parent
        text: root.text
        color: root.primary ? "#0B1218" : Theme.text
        font.weight: Font.DemiBold
    }
    MouseArea {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }
}
