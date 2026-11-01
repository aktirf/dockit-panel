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
        Txt { text: "Перегрев"; font.pixelSize: 16; font.weight: Font.DemiBold }
        Txt {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            color: Theme.muted
            font.pixelSize: 13
            text: "Предупреждать, когда процессор или видеокарта горячее этой температуры."
        }
        Flow {
            Layout.fillWidth: true
            spacing: 8
            Repeater {
                model: [0, 80, 85, 90, 95]
                delegate: Pill {
                    text: modelData === 0 ? "Не предупреждать" : modelData + " °C"
                    sel: d.settings && d.settings.warn_temp === modelData
                    onClicked: backend.setWarnTemp(modelData)
                }
            }
        }
    }

    Card {
        Layout.fillWidth: true
        Txt { text: "Уведомления и запуск"; font.pixelSize: 16; font.weight: Font.DemiBold }
        ToggleCard {
            Layout.fillWidth: true
            label: "Уведомления"
            tip: "Сообщения о смене профиля и о перегреве. Нужна программа notify-send (пакет libnotify)."
            on: d.settings ? d.settings.notify === true : false
            can: d.settings ? d.settings.notifyAvailable === true : false
            onToggled: backend.setNotify(!on)
        }
        ToggleCard {
            Layout.fillWidth: true
            label: "Запускать при входе в систему"
            tip: "Окно DOCKIT откроется само после входа. В niri может понадобиться строка spawn-at-startup в конфиге."
            on: d.settings ? d.settings.autostart === true : false
            onToggled: backend.setAutostart(!on)
        }
        ToggleCard {
            Layout.fillWidth: true
            label: "Значок в трее, закрытие сворачивает окно"
            tip: "Окно не закрывается, а прячется в трей. Нужна панель с поддержкой значков в трее."
            on: d.settings ? d.settings.tray === true : false
            can: d.settings ? d.settings.trayAvailable === true : false
            onToggled: backend.setTray(!on)
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
