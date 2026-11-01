import QtQuick
import QtQuick.Layouts
import QtQuick.Controls

// Common frame of a page: scrolling area, title and subtitle. Put the content inside it.
Flickable {
    id: page
    property string title: ""
    property string subtitle: ""
    property var d: ({})
    signal goto(string name)
    default property alias content: col.data

    contentWidth: width
    contentHeight: col.implicitHeight + 68
    clip: true
    boundsBehavior: Flickable.StopAtBounds
    ScrollBar.vertical: ScrollBar {}

    ColumnLayout {
        id: col
        x: 32
        y: 28
        width: page.width - 64
        spacing: 20

        ColumnLayout {
            spacing: 4
            Txt { text: page.title; font.pixelSize: 28; font.weight: Font.DemiBold }
            Txt { text: page.subtitle; color: Theme.muted }
        }
    }
}
