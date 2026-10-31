import QtQuick
import QtQuick.Layouts

Rectangle {
    id: root
    property string icon: ""
    property string text: ""
    property bool active: false
    property bool ready: true
    property int badge: 0
    signal clicked()

    Layout.fillWidth: true
    implicitHeight: 44
    radius: 10
    color: active ? Theme.navActive : (mouse.containsMouse ? "#161E26" : "transparent")
    opacity: ready ? 1 : 0.55

    RowLayout {
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
    MouseArea {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }
}
