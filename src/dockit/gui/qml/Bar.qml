import QtQuick

Rectangle {
    id: root
    property real value: 0      // percent, 0-100
    property color fill: Theme.accent

    implicitHeight: 6
    radius: 3
    color: Theme.border2
    clip: true

    Rectangle {
        width: root.width * Math.max(0, Math.min(100, root.value)) / 100
        height: parent.height
        color: root.fill
        Behavior on width { NumberAnimation { duration: 300 } }
    }
}
