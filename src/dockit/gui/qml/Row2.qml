import QtQuick
import QtQuick.Layouts

// One line "name ........ value" used in cards.
Item {
    id: root
    property string label: ""
    property string value: ""
    property color valueColor: Theme.text
    implicitHeight: 24
    Layout.fillWidth: true
    Txt { anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter; text: root.label; color: Theme.muted; font.pixelSize: 13 }
    Txt { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; text: root.value; color: root.valueColor; font.family: Theme.mono; font.pixelSize: 13 }
}
