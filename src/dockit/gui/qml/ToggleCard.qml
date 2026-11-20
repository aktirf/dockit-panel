import QtQuick

Rectangle {
    id: root
    property string label: ""
    property string icon: ""
    property bool on: false
    property bool can: true
    property string tip: ""
    signal toggled()

    implicitHeight: 64
    implicitWidth: 210
    radius: 14
    color: Theme.card
    border.width: 1
    border.color: on ? Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.45) : Theme.border2
    opacity: can ? 1 : 0.6
    Behavior on border.color { ColorAnimation { duration: 180 } }

    Rectangle {
        id: iconBadge
        visible: root.icon !== ""
        width: 34
        height: 34
        radius: 10
        anchors.left: parent.left
        anchors.leftMargin: 14
        anchors.verticalCenter: parent.verticalCenter
        color: root.on ? Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.16) : Theme.cardInner
        Behavior on color { ColorAnimation { duration: 180 } }
        Icon {
            anchors.centerIn: parent
            name: root.icon
            size: 18
            color: root.on ? Theme.accent : Theme.muted
        }
    }

    // text sits on the left, the switch always on the same spot at the right edge
    Column {
        anchors.left: iconBadge.visible ? iconBadge.right : parent.left
        anchors.leftMargin: iconBadge.visible ? 12 : 16
        anchors.right: sw.left
        anchors.rightMargin: 12
        anchors.verticalCenter: parent.verticalCenter
        spacing: 2
        Txt { width: parent.width; elide: Text.ElideRight; text: root.label; font.weight: Font.Medium }
        Txt {
            width: parent.width
            elide: Text.ElideRight
            text: (root.on ? "Включено" : "Выключено") + (root.can ? "" : " · только просмотр")
            font.pixelSize: 12
            color: root.on ? Theme.accent : Theme.muted
            Behavior on color { ColorAnimation { duration: 180 } }
        }
    }
    Rectangle {
        id: sw
        width: 42
        height: 24
        radius: 12
        anchors.right: parent.right
        anchors.rightMargin: 16
        anchors.verticalCenter: parent.verticalCenter
        color: root.on ? Theme.accent : "#2A343F"
        Behavior on color { ColorAnimation { duration: 180 } }
        Rectangle {
            y: 3
            x: root.on ? 21 : 3
            width: 18
            height: 18
            radius: 9
            color: root.on ? "#0B1218" : Theme.muted
            Behavior on x { NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }
            Behavior on color { ColorAnimation { duration: 180 } }
        }
    }
    MouseArea {
        anchors.fill: parent
        enabled: root.can
        cursorShape: Qt.PointingHandCursor
        onClicked: root.toggled()
    }
    Tip { text: root.tip }
}
