import QtQuick
import QtQuick.Layouts
import QtQuick.Controls

// Common frame of a page: scrolling area, title and subtitle. Put the content inside it.
Flickable {
    id: page
    property string title: ""
    property string subtitle: ""
    property var d: ({})
    readonly property int sidePad: page.width < 560 ? 16 : 32
    signal goto(string name)
    default property alias content: col.data

    contentWidth: width
    contentHeight: col.implicitHeight + 68
    clip: true
    boundsBehavior: Flickable.StopAtBounds
    ScrollBar.vertical: ScrollBar {}

    ColumnLayout {
        id: col
        width: Math.min(Math.max(200, page.width - page.sidePad * 2), 1020)
        x: Math.max(page.sidePad, (page.width - width) / 2)
        y: 28
        spacing: 20

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 4
            Txt { Layout.fillWidth: true; wrapMode: Text.WordWrap; text: page.title; font.pixelSize: page.width < 560 ? 22 : 28; font.weight: Font.DemiBold }
            Txt { Layout.fillWidth: true; wrapMode: Text.WordWrap; text: page.subtitle; color: Theme.muted }
        }
    }
}
