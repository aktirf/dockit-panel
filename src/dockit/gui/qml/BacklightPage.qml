import QtQuick
import QtQuick.Layouts

PageFrame {
    title: Theme.tr("kbd_backlight")
    subtitle: Theme.tr("periph_sub")

    Card {
        Layout.fillWidth: true
        RowLayout {
            Layout.fillWidth: true
            Txt { Layout.fillWidth: true; text: Theme.tr("kbd_backlight"); font.pixelSize: 16; font.weight: Font.DemiBold }
            Chip { kind: d.backlight && d.backlight.length > 0 ? "ok" : "no"; text: d.backlight && d.backlight.length > 0 ? Theme.tr("kbd_visible") : Theme.tr("status_no") }
        }
        Txt {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            color: Theme.muted
            visible: !!(d.backlight && d.backlight.length > 0)
            text: Theme.tr("kbd_visible_text").replace("{devs}", d.backlight ? d.backlight.join(", ") : "")
        }
        Txt {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            color: Theme.muted
            visible: !!(!d.backlight || d.backlight.length === 0)
            text: Theme.tr("kbd_missing_text")
        }
    }
}
