import QtQuick
import QtQuick.Layouts

PageFrame {
    title: "Настройки"
    subtitle: "Как работает окно DOCKIT"

    Card {
        Layout.fillWidth: true
        Txt { text: "Как часто обновлять данные"; font.pixelSize: 16; font.weight: Font.DemiBold }
        Txt {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            color: Theme.muted
            font.pixelSize: 13
            text: "Реже — меньше нагрузка на процессор и мягче картинка. Чаще — быстрее видны изменения."
        }
        Flow {
            Layout.fillWidth: true
            spacing: 8
            Repeater {
                model: [1, 3, 5, 10]
                delegate: Pill {
                    text: modelData + " с"
                    sel: backend.interval === modelData
                    onClicked: backend.setInterval(modelData)
                }
            }
        }
    }

    Card {
        Layout.fillWidth: true
        Txt { text: "О программе"; font.pixelSize: 16; font.weight: Font.DemiBold }
        Row2 { label: "Версия"; value: backend.version + " (альфа)" }
        Row2 { label: "Лицензия"; value: "GPL-3.0-or-later" }
        Row2 { label: "Проект"; value: "github.com/aktirf/dockit-panel" }
        Txt {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            color: Theme.muted
            font.pixelSize: 13
            text: "Проверено на Gigabyte Gaming A16 3VH. На других ноутбуках часть функций может не работать, это видно в «Диагностике»."
        }
    }
}
