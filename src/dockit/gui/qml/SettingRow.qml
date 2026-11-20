import QtQuick
import QtQuick.Layouts

// Switch-driven setting row: compact single line when OFF, expands its control when ON.
Rectangle {
    id: root
    property string icon: ""
    property string title: ""
    property string valueText: ""
    property string offText: Theme.tr("unchanged")
    property string tip: ""
    property bool checked: false
    property bool enabledSwitch: true
    default property alias body: bodyCol.data
    signal toggled(bool nextValue)

    Layout.fillWidth: true
    Layout.minimumWidth: 0
    implicitHeight: mainCol.implicitHeight + 24
    radius: 14
    color: checked ? "#19222C" : Theme.cardInner
    border.width: 1
    border.color: checked ? Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.42) : Theme.border2
    Behavior on color { ColorAnimation { duration: 160 } }
    Behavior on border.color { ColorAnimation { duration: 160 } }

    ColumnLayout {
        id: mainCol
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 12
        anchors.leftMargin: 14
        anchors.rightMargin: 14
        spacing: 12

        // Header row (clickable to toggle)
        Item {
            id: headerArea
            Layout.fillWidth: true
            implicitHeight: Math.max(36, headerRow.implicitHeight)

            RowLayout {
                id: headerRow
                anchors.fill: parent
                spacing: 12

                Rectangle {
                    visible: root.icon !== ""
                    implicitWidth: 34
                    implicitHeight: 34
                    radius: 10
                    color: root.checked ? Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.16) : Theme.card
                    Behavior on color { ColorAnimation { duration: 160 } }
                    Icon {
                        anchors.centerIn: parent
                        name: root.icon
                        size: 17
                        color: root.checked ? Theme.accent : Theme.muted
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.minimumWidth: 0
                    spacing: 1
                    Txt {
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                        text: root.title
                        font.pixelSize: 14
                        font.weight: Font.Medium
                        color: root.checked ? "#FFFFFF" : Theme.text
                    }
                    Txt {
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                        text: root.checked ? (root.valueText !== "" ? root.valueText : Theme.tr("enabled_word")) : root.offText
                        font.pixelSize: 12
                        color: root.checked ? Theme.accent : Theme.muted
                    }
                }

                // Tactile switch pill
                Rectangle {
                    id: swTrack
                    implicitWidth: 44
                    implicitHeight: 24
                    radius: 12
                    opacity: root.enabledSwitch ? 1 : 0.45
                    color: root.checked ? Theme.accent : "#2A343F"
                    Behavior on color { ColorAnimation { duration: 180 } }
                    Rectangle {
                        y: 3
                        x: root.checked ? 23 : 3
                        width: 18
                        height: 18
                        radius: 9
                        color: root.checked ? "#0B1218" : Theme.muted
                        Behavior on x { NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }
                        Behavior on color { ColorAnimation { duration: 180 } }
                    }
                }
            }

            MouseArea {
                anchors.fill: parent
                enabled: root.enabledSwitch
                cursorShape: Qt.PointingHandCursor
                onClicked: root.toggled(!root.checked)
            }
            Tip { text: root.tip }
        }

        // Expanded control area (only visible when switched ON)
        Rectangle {
            visible: root.checked && bodyCol.children.length > 0
            Layout.fillWidth: true
            height: 1
            color: Theme.border
        }
        ColumnLayout {
            id: bodyCol
            visible: root.checked && children.length > 0
            Layout.fillWidth: true
            Layout.minimumWidth: 0
            spacing: 10
        }
    }
}
