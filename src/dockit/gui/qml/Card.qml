import QtQuick
import QtQuick.Layouts

Rectangle {
    id: root
    default property alias content: col.data
    property int pad: 20

    implicitWidth: 260
    implicitHeight: col.implicitHeight + pad * 2
    color: Theme.card
    radius: 16
    border.width: 1
    border.color: Theme.border

    ColumnLayout {
        id: col
        anchors.fill: parent
        anchors.leftMargin: root.pad + 2
        anchors.rightMargin: root.pad + 2
        anchors.topMargin: root.pad
        anchors.bottomMargin: root.pad
        spacing: 14
    }
}
