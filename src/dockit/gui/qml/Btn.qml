import QtQuick

Rectangle {
    id: root
    property string text: ""
    property bool primary: false
    property string tip: ""
    signal clicked()

    implicitHeight: 44
    implicitWidth: label.implicitWidth + 36
    radius: 10
    color: primary ? Theme.accent : (btnHover.hovered ? Theme.cardInner : Theme.btn)
    border.width: 1
    border.color: primary ? Theme.accent : (btnHover.hovered ? Theme.accent : Theme.border3)
    opacity: !enabled ? 0.45 : (mouse.pressed ? 0.85 : (btnHover.hovered ? 0.94 : 1))
    scale: enabled && mouse.pressed ? 0.97 : 1.0
    Behavior on color { ColorAnimation { duration: 150; easing.type: Easing.OutCubic } }
    Behavior on border.color { ColorAnimation { duration: 150; easing.type: Easing.OutCubic } }
    Behavior on opacity { NumberAnimation { duration: 130; easing.type: Easing.OutCubic } }
    Behavior on scale { NumberAnimation { duration: 110; easing.type: Easing.OutCubic } }
    HoverHandler { id: btnHover; enabled: root.enabled }
    Tip { text: root.tip }

    Txt {
        id: label
        anchors.centerIn: parent
        width: Math.max(0, root.width - 20)
        horizontalAlignment: Text.AlignHCenter
        elide: Text.ElideRight
        text: root.text
        color: root.primary ? "#0B1218" : Theme.text
        font.weight: Font.DemiBold
        Behavior on color { ColorAnimation { duration: 150 } }
    }
    MouseArea {
        id: mouse
        anchors.fill: parent
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }
}
