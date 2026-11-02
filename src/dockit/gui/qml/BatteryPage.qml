import QtQuick
import QtQuick.Layouts

PageFrame {
    title: "Питание и батарея"
    subtitle: "Заряд, износ и лимит зарядки"

    Card {
        Layout.fillWidth: true
        RowLayout {
            Layout.fillWidth: true
            Txt { Layout.fillWidth: true; text: "Батарея"; font.pixelSize: 16; font.weight: Font.DemiBold }
            Chip { kind: d.battery && d.battery.percent !== null && d.battery.percent !== undefined ? "ok" : "no"; text: d.battery && d.battery.percent !== null && d.battery.percent !== undefined ? "Работает" : "Нет данных" }
        }
        RowLayout {
            Txt { text: d.battery && d.battery.percent !== null ? d.battery.percent : "—"; font.pixelSize: 44; font.family: Theme.mono }
            Txt { text: "%"; color: Theme.muted; Layout.alignment: Qt.AlignBottom; bottomPadding: 10 }
        }
        Bar { Layout.fillWidth: true; value: d.battery && d.battery.percent ? d.battery.percent : 0; fill: Theme.ok }
        Row2 { label: "Состояние"; value: d.battery ? d.battery.text : "—" }
        Row2 { label: "Питание"; value: d.battery && d.battery.source ? d.battery.source : "—" }
        Row2 { label: "Износ (остаток ёмкости)"; value: d.battery ? d.battery.health + " %" : "—" }
        Row2 { label: "Циклов зарядки"; value: d.battery && d.battery.cycles !== null ? d.battery.cycles : "—" }
        Row2 { label: "Потребление сейчас"; value: d.battery && d.battery.power !== "—" ? d.battery.power + " Вт" : "—" }
        Txt {
            visible: d.battery && d.battery.left !== undefined && d.battery.left !== ""
            text: d.battery ? d.battery.left : ""
            color: Theme.accent
            font.pixelSize: 15
            font.weight: Font.DemiBold
        }
        Txt { text: "Заряд за последние сутки"; color: Theme.muted; font.pixelSize: 12 }
        Spark { Layout.fillWidth: true; Layout.preferredHeight: 40; implicitHeight: 40; values: d.batteryHistory ? d.batteryHistory : []; lineColor: Theme.ok }
    }

    Card {
        Layout.fillWidth: true
        RowLayout {
            Layout.fillWidth: true
            Txt { Layout.fillWidth: true; text: "Лимит заряда"; font.pixelSize: 16; font.weight: Font.DemiBold }
            Chip { kind: d.limit ? d.limit.status : "no"; text: d.limit ? d.limit.statusText : "" }
        }
        Txt {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            color: Theme.muted
            text: "Лимит (например, 80 %) продлевает жизнь батареи, если ноутбук почти всегда подключён к розетке."
        }
        Txt {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            visible: d.limit && d.limit.hint !== undefined && d.limit.hint !== ""
            color: Theme.warn
            text: "Как исправить: " + (d.limit ? d.limit.hint : "")
        }
        Txt {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            visible: d.limit && d.limit.status !== "ok"
            color: Theme.muted
            text: "Пока ядро не показывает лимит для этой модели, DOCKIT его не меняет. Лимит можно поставить в BIOS или в GiMATE на Windows."
        }
    }

    Card {
        Layout.fillWidth: true
        Txt { text: "Режим питания"; font.pixelSize: 16; font.weight: Font.DemiBold }
        Txt {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            color: Theme.muted
            text: "Режим «Тишина» экономит заряд. Профили могут переключать его сами при отключении зарядки."
        }
        RowLayout {
            spacing: 10
            Btn { text: "Режимы мощности"; onClicked: goto("performance") }
            Btn { text: "Автопереключение"; onClicked: goto("profiles") }
        }
    }

    Card {
        Layout.fillWidth: true
        Txt { text: "Экран"; font.pixelSize: 16; font.weight: Font.DemiBold }
        Row2 { label: "Яркость сейчас"; value: d.display && d.display.brightness !== null && d.display.brightness !== undefined ? d.display.brightness + " %" : "—" }
        Flow {
            Layout.fillWidth: true
            spacing: 8
            Repeater {
                model: [20, 40, 60, 80, 100]
                delegate: Pill {
                    text: modelData + " %"
                    sel: d.display && d.display.brightness !== null && Math.abs(d.display.brightness - modelData) < 10
                    tip: "Меньше яркость — дольше работа от батареи."
                    onClicked: backend.setBrightness(modelData)
                }
            }
        }
        Txt {
            visible: !d.display || d.display.brightness === null || d.display.brightness === undefined
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            color: Theme.muted
            font.pixelSize: 12
            text: "Яркость экрана не найдена в системе. Её можно менять клавишами Fn."
        }
        Row2 { label: "Частота экрана сейчас"; value: d.display && d.display.refresh ? d.display.refresh + " Гц" : "—" }
        Flow {
            Layout.fillWidth: true
            spacing: 8
            Repeater {
                model: d.display && d.display.rates ? d.display.rates : []
                delegate: Pill {
                    text: modelData + " Гц"
                    sel: d.display && d.display.refresh === modelData
                    tip: "Меньшая частота экономит заряд, большая даёт более плавную картинку."
                    onClicked: backend.setRefresh(modelData)
                }
            }
        }
        Txt {
            visible: !d.display || !d.display.rates || d.display.rates.length === 0
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            color: Theme.muted
            font.pixelSize: 12
            text: "Смена частоты экрана работает в niri и Hyprland."
        }
    }
}
