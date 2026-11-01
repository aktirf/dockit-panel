import QtQuick

Rectangle {
    id: root
    property string kind: "neutral"
    property string text: ""
    property string icon: ""
    property bool big: false
    property string tip: ""

    implicitHeight: big ? 34 : 26
    implicitWidth: row.implicitWidth + (big ? 28 : 20)
    radius: height / 2
    color: big ? Theme.card : Theme.statusBg(kind)
    border.width: big ? 1 : 0
    border.color: Theme.border2
    Behavior on color { ColorAnimation { duration: 200 } }
    Tip { text: root.tip }

    Row {
        id: row
        anchors.centerIn: parent
        spacing: 6
        Rectangle {
            visible: root.big && root.kind !== "neutral"
            width: 8
            height: 8
            radius: 4
            color: root.kind === "ok" ? Theme.ok : Theme.err
            anchors.verticalCenter: parent.verticalCenter
        }
        Icon {
            visible: root.icon !== ""
            name: root.icon
            size: 13
            stroke: 2.2
            color: Theme.statusColor(root.kind)
            anchors.verticalCenter: parent.verticalCenter
        }
        Txt {
            text: root.text
            font.pixelSize: root.big ? 13 : 12
            font.weight: root.big ? Font.Normal : Font.Medium
            color: root.big ? Theme.soft : Theme.statusColor(root.kind)
            anchors.verticalCenter: parent.verticalCenter
        }
    }
}
