import QtQuick
import QtQuick.Layouts

PageFrame {
    id: root
    title: "Охлаждение"
    subtitle: "Температуры, перегрев, графики и вентиляторы"

    SyncModel { id: tempsModel }
    SyncModel { id: fansModel }
    function syncAll() {
        tempsModel.sync(d.temps)
        fansModel.sync(d.fans)
    }
    Connections { target: backend; function onStateChanged() { syncAll() } }
    Component.onCompleted: syncAll()

    readonly property var cool: d.cooling ? d.cooling : ({})

    // Overheat alert banner
    Card {
        Layout.fillWidth: true
        visible: cool.hot === true
        GridLayout {
            Layout.fillWidth: true
            columns: root.width >= 620 ? 3 : 1
            columnSpacing: 12
            rowSpacing: 10
            Chip { kind: "setup"; text: "Горячо" }
            Txt {
                Layout.fillWidth: true
                Layout.minimumWidth: 0
                wrapMode: Text.WordWrap
                color: Theme.warn
                text: "Температура выше " + cool.warn + " °C. Включите режим «Баланс» или «Тишина» и проверьте вентиляцию."
            }
            Btn { text: "Сменить режим"; onClicked: goto("performance") }
        }
    }

    // Main 3 thermal cards with dynamic temperature colors & bounds on Spark
    GridLayout {
        Layout.fillWidth: true
        columns: width >= 720 ? 3 : (width >= 480 ? 2 : 1)
        columnSpacing: 16
        rowSpacing: 16

        Repeater {
            model: [
                { key: "cpu", icon: "cpu", name: "Процессор", note: "Частота снижается из-за жары" },
                { key: "gpu", icon: "monitor", name: "Видеокарта", note: "Видеокарта сбрасывает скорость из-за жары" },
                { key: "ssd", icon: "layers", name: "SSD", note: "" }
            ]
            delegate: Card {
                pad: 16
                Layout.fillWidth: true
                Layout.fillHeight: true
                readonly property var part: root.cool[modelData.key] ? root.cool[modelData.key] : ({})
                readonly property color tColor: part.throttled === true ? Theme.err : Theme.tempColor(part.now)

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    Icon { name: modelData.icon; size: 15; color: tColor }
                    Txt { Layout.fillWidth: true; text: modelData.name; font.pixelSize: 15; font.weight: Font.DemiBold }
                    Chip {
                        visible: part.throttled === true
                        kind: "setup"
                        text: "Троттлинг"
                        tip: modelData.note
                    }
                }
                RowLayout {
                    Txt { text: part.now ? part.now : "—"; font.pixelSize: 30; font.family: Theme.mono; color: tColor }
                    Txt { text: "°C"; color: Theme.muted; Layout.alignment: Qt.AlignBottom; bottomPadding: 6 }
                }
                Row2 { label: "Максимум за сессию"; value: (part.max ? part.max : "—") + " °C" }
                Spark {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 46
                    implicitHeight: 46
                    showBounds: true
                    unit: "°"
                    values: part.values ? part.values : []
                    lineColor: tColor
                }
                Txt {
                    visible: part.has === false
                    text: "Датчик не найден"
                    color: Theme.muted
                    font.pixelSize: 12
                }
            }
        }
    }

    // All hwmon sensors in a crisp 2-column mini-tile grid
    Card {
        Layout.fillWidth: true
        Txt { text: "Все датчики температуры"; font.pixelSize: 16; font.weight: Font.DemiBold }
        Txt {
            visible: tempsModel.count === 0
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            color: Theme.muted
            text: "Датчики температуры не найдены. Установите lm_sensors и запустите sensors-detect."
        }
        GridLayout {
            visible: tempsModel.count > 0
            Layout.fillWidth: true
            columns: root.width >= 580 ? 2 : 1
            columnSpacing: 10
            rowSpacing: 10
            Repeater {
                model: tempsModel
                delegate: Rectangle {
                    Layout.fillWidth: true
                    Layout.minimumWidth: 0
                    implicitHeight: 42
                    radius: 10
                    color: Theme.cardInner
                    border.width: 1
                    border.color: model.hot ? Theme.err : Theme.border2
                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 12
                        anchors.rightMargin: 12
                        spacing: 10
                        Rectangle {
                            width: 8; height: 8; radius: 4
                            color: model.hot ? Theme.err : Theme.tempColor(model.value)
                        }
                        Txt { Layout.fillWidth: true; Layout.minimumWidth: 0; elide: Text.ElideRight; text: model.name; color: Theme.soft; font.pixelSize: 13 }
                        Txt { text: model.value + " °C"; color: model.hot ? Theme.err : Theme.text; font.family: Theme.mono; font.pixelSize: 13; font.weight: Font.DemiBold }
                    }
                }
            }
        }
    }

    // Compact fan strip (expands cleanly when fan RPM sensors exist)
    Card {
        Layout.fillWidth: true
        pad: 16
        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            Icon { name: "fan"; size: 16; color: Theme.muted }
            Txt { Layout.fillWidth: true; text: "Вентиляторы"; font.pixelSize: 15; font.weight: Font.DemiBold }
            Chip { kind: fansModel.count > 0 ? "ok" : "no"; text: fansModel.count > 0 ? "Видны" : "Нет данных" }
        }
        Repeater {
            model: fansModel
            delegate: Row2 { label: model.name; value: model.rpm + " об/мин" }
        }
        Txt {
            visible: fansModel.count === 0
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            color: Theme.muted
            font.pixelSize: 12
            text: "Ядро не показывает обороты вентиляторов этого ноутбука. Скорость охлаждения зависит от режима мощности («Тишина» / «Баланс» / «Производительность»)."
        }
    }
}
