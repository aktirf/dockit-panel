import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// Styled dark dropdown that never overflows cards and only fires `picked` on user selection.
ComboBox {
    id: root
    property var items: []          // [{ id: "...", label: "..." }]
    property string currentId: ""
    property string placeholder: "Выберите…"
    signal picked(string itemId)

    Layout.fillWidth: true
    Layout.minimumWidth: 0
    implicitHeight: 40

    model: items ? items.length : 0
    currentIndex: {
        if (!items) return -1
        for (var i = 0; i < items.length; i++)
            if (String(items[i].id) === String(currentId))
                return i
        return -1
    }

    onActivated: function (idx) {
        if (items && idx >= 0 && idx < items.length)
            root.picked(String(items[idx].id))
    }

    background: Rectangle {
        radius: 10
        color: Theme.panel
        border.width: 1
        border.color: root.popup.visible || root.hovered ? Theme.accent : Theme.border2
        Behavior on border.color { ColorAnimation { duration: 140 } }
    }

    indicator: Icon {
        x: root.width - width - 12
        y: (root.height - height) / 2
        name: "chevron"
        size: 16
        color: Theme.muted
    }

    contentItem: Txt {
        leftPadding: 12
        rightPadding: 34
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
        font.pixelSize: 13
        color: root.currentIndex >= 0 ? Theme.text : Theme.muted
        text: (root.items && root.currentIndex >= 0 && root.currentIndex < root.items.length)
              ? String(root.items[root.currentIndex].label)
              : root.placeholder
    }

    delegate: ItemDelegate {
        id: optDel
        readonly property var entry: root.items && index < root.items.length ? root.items[index] : ({ id: "", label: "" })
        readonly property bool isCur: index === root.currentIndex
        width: ListView.view ? ListView.view.width : Math.max(80, root.width - 8)
        height: 36
        highlighted: root.highlightedIndex === index
        contentItem: Txt {
            text: String(optDel.entry.label || "")
            font.pixelSize: 13
            font.weight: optDel.isCur ? Font.DemiBold : Font.Normal
            color: optDel.isCur ? Theme.accent : Theme.text
            elide: Text.ElideRight
            verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle {
            radius: 8
            color: optDel.highlighted ? Theme.navActive : "transparent"
        }
    }

    popup: Popup {
        y: root.height + 4
        width: root.width
        implicitHeight: Math.min(contentItem.implicitHeight + 10, 260)
        padding: 4
        contentItem: ListView {
            clip: true
            implicitHeight: contentHeight
            model: root.popup.visible ? root.delegateModel : null
            currentIndex: root.highlightedIndex
            ScrollIndicator.vertical: ScrollIndicator {}
        }
        background: Rectangle {
            radius: 12
            color: Theme.card
            border.width: 1
            border.color: Theme.border3
        }
    }
}
