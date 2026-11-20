import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// Styled dark slider that never flashes the old value on release and stays synced with external changes (Fn keys).
Slider {
    id: root
    property real targetValue: 50
    property color fillColor: Theme.accent
    property color handleColor: Theme.accent
    property int handleSize: 18
    property bool holding: false
    property real committedValue: 50
    readonly property int displayValue: Math.round(pressed ? value : (holding ? committedValue : targetValue))
    signal committed(int val)

    Layout.fillWidth: true
    from: 5
    to: 100
    stepSize: 1

    onTargetValueChanged: {
        if (holding && Math.abs(targetValue - committedValue) <= 1)
            holding = false
    }

    // Keep synced with hardware/backend when not dragging or waiting for a just-committed change.
    Binding {
        target: root
        property: "value"
        value: root.targetValue
        when: !root.pressed && !root.holding
    }

    Timer {
        id: holdTimer
        interval: 1500
        onTriggered: root.holding = false
    }

    onPressedChanged: {
        if (pressed) {
            holdTimer.stop()
            holding = false
        } else {
            var v = Math.round(value)
            committedValue = v
            holding = true
            holdTimer.restart()
            root.committed(v)
        }
    }

    background: Rectangle {
        x: root.leftPadding
        y: root.topPadding + root.availableHeight / 2 - height / 2
        width: root.availableWidth
        height: 6
        radius: 3
        color: Theme.border2
        Rectangle {
            width: root.visualPosition * parent.width
            height: parent.height
            radius: 3
            color: root.fillColor
            Behavior on color { ColorAnimation { duration: 180; easing.type: Easing.OutCubic } }
        }
    }

    HoverHandler { id: sliderHover }

    handle: Rectangle {
        x: root.leftPadding + root.visualPosition * (root.availableWidth - width)
        y: root.topPadding + root.availableHeight / 2 - height / 2
        width: root.handleSize
        height: root.handleSize
        radius: root.handleSize / 2
        scale: root.pressed ? 1.18 : (sliderHover.hovered ? 1.08 : 1.0)
        color: root.pressed ? "#FFFFFF" : root.handleColor
        border.width: 2
        border.color: Theme.card
        Behavior on scale { NumberAnimation { duration: 120; easing.type: Easing.OutCubic } }
        Behavior on color { ColorAnimation { duration: 150; easing.type: Easing.OutCubic } }
    }
}
