import QtQuick
import QtQuick.Layouts

PageFrame {
    title: "Подсветка"
    subtitle: "Подсветка клавиатуры"

    Card {
        Layout.fillWidth: true
        RowLayout {
            Layout.fillWidth: true
            Txt { Layout.fillWidth: true; text: "Подсветка клавиатуры"; font.pixelSize: 16; font.weight: Font.DemiBold }
            Chip { kind: d.backlight && d.backlight.length > 0 ? "ok" : "no"; text: d.backlight && d.backlight.length > 0 ? "Видна системе" : "Недоступно" }
        }
        Txt {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            color: Theme.muted
            visible: d.backlight && d.backlight.length > 0
            text: "Система видит подсветку (" + (d.backlight ? d.backlight.join(", ") : "") + "). Управление из DOCKIT появится позже."
        }
        Txt {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            color: Theme.muted
            visible: !d.backlight || d.backlight.length === 0
            text: "Подсветка этой клавиатуры не видна через стандартный интерфейс ядра, поэтому DOCKIT пока не может её менять. Она включается и меняется клавишами ноутбука (Fn + стрелки или Fn + пробел)."
        }
        Txt {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            color: Theme.warn
            text: "Что можно проверить: цвет и яркость часто задаются отдельным устройством клавиатуры (USB 0414:8104). Это в планах, когда найдём рабочий способ."
        }
    }
}
