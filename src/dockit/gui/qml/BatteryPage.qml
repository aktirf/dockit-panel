import QtQuick
import QtQuick.Layouts
import QtQuick.Controls

PageFrame {
    id: batPage
    title: "Питание и экран"
    subtitle: "Заряд, состояние батареи, яркость и частота экрана"

    function rateOptions() {
        var rates = d.display && d.display.rates ? d.display.rates : []
        return rates.map(function (r) {
            return { id: String(r), label: String(r) + " Гц", tip: "Меньше Гц — дольше батарея, больше — плавнее картинка." }
        })
    }

    // 2-column top grid: Battery + Display
    GridLayout {
        Layout.fillWidth: true
        columns: batPage.width >= 720 ? 2 : 1
        columnSpacing: 16
        rowSpacing: 16

        // Battery card
        Card {
            Layout.fillWidth: true
            Layout.fillHeight: true
            RowLayout {
                Layout.fillWidth: true
                Icon { name: "battery"; size: 17; color: Theme.batteryColor(d.battery ? d.battery.percent : 100) }
                Txt { Layout.fillWidth: true; text: "Батарея"; font.pixelSize: 16; font.weight: Font.DemiBold }
                Chip {
                    kind: d.battery && d.battery.percent !== null && d.battery.percent !== undefined ? "ok" : "no"
                    text: d.battery && d.battery.source ? String(d.battery.source) : "Нет данных"
                }
            }
            RowLayout {
                spacing: 8
                Txt {
                    text: (d.battery && d.battery.percent !== null && d.battery.percent !== undefined) ? String(d.battery.percent) : "—"
                    font.pixelSize: 42
                    font.family: Theme.mono
                    color: Theme.batteryColor(d.battery ? d.battery.percent : 100)
                }
                Txt { text: "%"; color: Theme.muted; Layout.alignment: Qt.AlignBottom; bottomPadding: 8 }
                Item { Layout.fillWidth: true }
                Txt {
                    visible: !!(d.battery && d.battery.left !== undefined && d.battery.left !== "")
                    text: d.battery ? String(d.battery.left) : ""
                    color: Theme.accent
                    font.pixelSize: 13
                    font.weight: Font.DemiBold
                    Layout.alignment: Qt.AlignBottom
                    bottomPadding: 8
                }
            }
            Bar { Layout.fillWidth: true; value: d.battery && d.battery.percent ? d.battery.percent : 0; fill: Theme.batteryColor(d.battery ? d.battery.percent : 100) }
            Txt { text: d.battery ? String(d.battery.text || "") : "—"; color: Theme.muted; font.pixelSize: 13 }

            // 3 compact stat tiles
            GridLayout {
                Layout.fillWidth: true
                columns: 3
                columnSpacing: 8
                rowSpacing: 8
                Rectangle {
                    Layout.fillWidth: true; Layout.minimumWidth: 0; implicitHeight: 54; radius: 10; color: Theme.cardInner
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 8; spacing: 2
                        Txt { text: "Ёмкость"; color: Theme.muted; font.pixelSize: 11 }
                        Txt { text: d.battery ? String(d.battery.health || "—") + " %" : "—"; font.family: Theme.mono; font.pixelSize: 14; font.weight: Font.DemiBold }
                    }
                }
                Rectangle {
                    Layout.fillWidth: true; Layout.minimumWidth: 0; implicitHeight: 54; radius: 10; color: Theme.cardInner
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 8; spacing: 2
                        Txt { text: "Циклы"; color: Theme.muted; font.pixelSize: 11 }
                        Txt { text: (d.battery && d.battery.cycles !== null && d.battery.cycles !== undefined) ? String(d.battery.cycles) : "—"; font.family: Theme.mono; font.pixelSize: 14; font.weight: Font.DemiBold }
                    }
                }
                Rectangle {
                    Layout.fillWidth: true; Layout.minimumWidth: 0; implicitHeight: 54; radius: 10; color: Theme.cardInner
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 8; spacing: 2
                        Txt { text: "Мощность"; color: Theme.muted; font.pixelSize: 11 }
                        Txt { text: d.battery && d.battery.power !== "—" ? String(d.battery.power) + " Вт" : "—"; font.family: Theme.mono; font.pixelSize: 14; font.weight: Font.DemiBold }
                    }
                }
            }
        }

        // Display card
        Card {
            Layout.fillWidth: true
            Layout.fillHeight: true
            RowLayout {
                Layout.fillWidth: true
                Icon { name: "monitor"; size: 17; color: Theme.accent }
                Txt { Layout.fillWidth: true; text: "Экран"; font.pixelSize: 16; font.weight: Font.DemiBold }
            }

            Row2 {
                label: "Яркость"
                value: brightnessSlider.pressed
                       ? Math.round(brightnessSlider.value) + " %"
                       : (d.display && d.display.brightness !== null && d.display.brightness !== undefined ? d.display.brightness + " %" : "—")
            }
            Slider {
                id: brightnessSlider
                Layout.fillWidth: true
                visible: !!(d.display && d.display.brightness !== null && d.display.brightness !== undefined)
                from: 5
                to: 100
                stepSize: 1
                value: (d.display && d.display.brightness !== null && d.display.brightness !== undefined) ? Number(d.display.brightness) : 50
                onPressedChanged: {
                    if (!pressed)
                        backend.setBrightness(Math.round(value))
                }
                background: Rectangle {
                    x: brightnessSlider.leftPadding
                    y: brightnessSlider.topPadding + brightnessSlider.availableHeight / 2 - height / 2
                    width: brightnessSlider.availableWidth
                    height: 6
                    radius: 3
                    color: Theme.border2
                    Rectangle {
                        width: brightnessSlider.visualPosition * parent.width
                        height: parent.height
                        radius: 3
                        color: Theme.accent
                    }
                }
                handle: Rectangle {
                    x: brightnessSlider.leftPadding + brightnessSlider.visualPosition * (brightnessSlider.availableWidth - width)
                    y: brightnessSlider.topPadding + brightnessSlider.availableHeight / 2 - height / 2
                    width: 18
                    height: 18
                    radius: 9
                    color: brightnessSlider.pressed ? "#FFFFFF" : Theme.accent
                    border.width: 2
                    border.color: Theme.card
                }
            }
            SegmentBar {
                visible: !!(d.display && d.display.brightness !== null && d.display.brightness !== undefined)
                options: [
                    { id: "25", label: "25 %", tip: "" },
                    { id: "50", label: "50 %", tip: "" },
                    { id: "75", label: "75 %", tip: "" },
                    { id: "100", label: "100 %", tip: "" }
                ]
                current: d.display && d.display.brightness !== null && d.display.brightness !== undefined ? String(d.display.brightness) : ""
                onPicked: function (val) { backend.setBrightness(Number(val)) }
            }
            Txt {
                visible: !!(!d.display || d.display.brightness === null || d.display.brightness === undefined)
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                color: Theme.muted
                font.pixelSize: 12
                text: "Яркость экрана не найдена в системе. Её можно менять клавишами Fn."
            }

            Rectangle { Layout.fillWidth: true; height: 1; color: Theme.border }

            Row2 { label: "Частота обновления"; value: d.display && d.display.refresh ? d.display.refresh + " Гц" : "—" }
            SegmentBar {
                visible: !!(d.display && d.display.rates && d.display.rates.length > 0)
                options: batPage.rateOptions()
                current: d.display && d.display.refresh ? String(d.display.refresh) : ""
                onPicked: function (val) { backend.setRefresh(Number(val)) }
            }
            Txt {
                visible: !!(!d.display || !d.display.rates || d.display.rates.length === 0)
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                color: Theme.muted
                font.pixelSize: 12
                text: "Смена частоты экрана работает в niri, Hyprland, Sway, KDE Plasma и X11."
            }
        }
    }

    // 24h charge graph
    Card {
        Layout.fillWidth: true
        RowLayout {
            Layout.fillWidth: true
            Txt { Layout.fillWidth: true; text: "Заряд за последние 24 часа"; font.pixelSize: 15; font.weight: Font.DemiBold }
            Txt { text: "шаг 5 мин"; color: Theme.muted; font.pixelSize: 12 }
        }
        Spark {
            Layout.fillWidth: true
            Layout.preferredHeight: 56
            implicitHeight: 56
            showBounds: true
            unit: "%"
            values: d.batteryHistory ? d.batteryHistory : []
            lineColor: Theme.ok
        }
    }

    // Compact charge limit strip
    Card {
        Layout.fillWidth: true
        pad: 16
        RowLayout {
            Layout.fillWidth: true
            spacing: 12
            Txt { Layout.fillWidth: true; text: "Лимит заряда (например, 80 %)"; font.pixelSize: 15; font.weight: Font.DemiBold }
            Chip { kind: d.limit ? d.limit.status : "no"; text: d.limit ? d.limit.statusText : "" }
        }
        Txt {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            visible: !!(d.limit && d.limit.status !== "ok")
            color: Theme.muted
            font.pixelSize: 12
            text: "Ядро пока не показывает лимит заряда для этой модели — его можно задать в BIOS или GiMATE (Windows)."
        }
        Txt {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            visible: !!(d.limit && d.limit.hint !== undefined && d.limit.hint !== "")
            color: Theme.warn
            font.pixelSize: 12
            text: "Подсказка: " + (d.limit ? d.limit.hint : "")
        }
    }
}
