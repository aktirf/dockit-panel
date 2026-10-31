import QtQuick
import QtQuick.Layouts

Rectangle {
    id: root
    property string label: ""
    property bool on: false
    property bool can: true
    signal toggled()

    implicitHeight: 64
    implicitWidth: 210
    radius: 14
    color: Theme.card
    border.width: 1
    border.color: on ? "#2F5A80" : Theme.border2
    opacity: can ? 1 : 0.6

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 16
        anchors.rightMargin: 16
        spacing: 12
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 2
            Txt { text: root.label; font.weight: Font.Medium }
            Txt {
                text: (root.on ? "Включено" : "Выключено") + (root.can ? "" : " · только просмотр")
                font.pixelSize: 12
                color: root.on ? "#7FC4FF" : Theme.muted
            }
        }
        Rectangle {
            implicitWidth: 42
            implicitHeight: 24
            radius: 12
            color: root.on ? Theme.accent : "#2A343F"
            Rectangle {
                y: 3
                x: root.on ? 21 : 3
                width: 18
                height: 18
                radius: 9
                color: root.on ? "#0B1218" : Theme.muted
                Behavior on x { NumberAnimation { duration: 120 } }
            }
        }
    }
    MouseArea {
        anchors.fill: parent
        enabled: root.can
        cursorShape: Qt.PointingHandCursor
        onClicked: root.toggled()
    }
}
