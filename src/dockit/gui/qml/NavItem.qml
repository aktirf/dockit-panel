import QtQuick
import QtQuick.Layouts

Rectangle {
    id: root
    property string icon: ""
    property string text: ""
    property bool active: false
    property bool ready: true
    property bool compact: false
    property int badge: 0
    signal clicked()

    Layout.fillWidth: true
    implicitHeight: 44
    radius: 10
    color: active ? Theme.navActive : (navHover.hovered ? "#161E26" : "transparent")
    scale: mouse.pressed ? 0.97 : 1.0
    Behavior on color { ColorAnimation { duration: 160; easing.type: Easing.OutCubic } }
    Behavior on scale { NumberAnimation { duration: 100; easing.type: Easing.OutCubic } }
    opacity: ready ? 1 : 0.55

    HoverHandler { id: navHover }

    // Subtle accent indicator pill on the left edge when active
    Rectangle {
        width: 3
        height: root.active ? 20 : 0
        radius: 2
        color: Theme.accent
        anchors.left: parent.left
        anchors.leftMargin: 3
        anchors.verticalCenter: parent.verticalCenter
        opacity: root.active ? 1 : 0
        Behavior on height { NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }
        Behavior on opacity { NumberAnimation { duration: 160; easing.type: Easing.OutCubic } }
    }

    // Dead-center icon in compact rail mode (never stretched by RowLayout)
    Icon {
        visible: root.compact
        anchors.centerIn: parent
        name: root.icon
        size: 20
        color: root.active ? Theme.accent : Theme.navText
    }

    RowLayout {
        visible: !root.compact
        anchors.fill: parent
        anchors.leftMargin: 12
        anchors.rightMargin: 12
        spacing: 12
        Icon {
            name: root.icon
            size: 20
            color: root.active ? Theme.accent : Theme.navText
        }
        Txt {
            Layout.fillWidth: true
            Layout.minimumWidth: 0
            elide: Text.ElideRight
            text: root.text
            color: root.active ? "#FFFFFF" : Theme.navText
            font.weight: Font.Medium
        }
        Rectangle {
            visible: root.badge > 0
            implicitWidth: Math.max(20, badgeText.implicitWidth + 12)
            implicitHeight: 20
            radius: 10
            color: Theme.warn
            Txt {
                id: badgeText
                anchors.centerIn: parent
                text: root.badge
                color: "#1A1405"
                font.pixelSize: 12
                font.weight: Font.DemiBold
            }
        }
    }
    // Compact mode badge dot on top-right of the icon
    Rectangle {
        visible: root.compact && root.badge > 0
        width: 8
        height: 8
        radius: 4
        color: Theme.warn
        anchors.top: parent.top
        anchors.topMargin: 8
        anchors.right: parent.right
        anchors.rightMargin: 8
    }
    MouseArea {
        id: mouse
        anchors.fill: parent
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }
    Tip { text: root.compact ? root.text : "" }
}
