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
    color: active ? Theme.navActive : (mouse.containsMouse ? "#161E26" : "transparent")
    Behavior on color { ColorAnimation { duration: 160 } }
    opacity: ready ? 1 : 0.55

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: root.compact ? 0 : 12
        anchors.rightMargin: root.compact ? 0 : 12
        spacing: root.compact ? 0 : 12
        Icon {
            Layout.alignment: Qt.AlignCenter
            Layout.fillWidth: root.compact
            name: root.icon
            size: 20
            color: root.active ? Theme.accent : Theme.navText
        }
        Txt {
            visible: !root.compact
            Layout.fillWidth: true
            Layout.minimumWidth: 0
            elide: Text.ElideRight
            text: root.text
            color: root.active ? "#FFFFFF" : Theme.navText
            font.weight: Font.Medium
        }
        Rectangle {
            visible: !root.compact && root.badge > 0
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
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }
    Tip { text: root.compact ? root.text : "" }
}
