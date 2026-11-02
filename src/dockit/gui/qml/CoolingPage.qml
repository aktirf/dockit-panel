import QtQuick
import QtQuick.Layouts

PageFrame {
    id: root
    title: "Охлаждение"
    subtitle: "Температуры, перегрев и вентиляторы"

    SyncModel { id: tempsModel }
    SyncModel { id: fansModel }
    function syncAll() {
        tempsModel.sync(d.temps)
        fansModel.sync(d.fans)
    }
    Connections { target: backend; function onStateChanged() { syncAll() } }
    Component.onCompleted: syncAll()

    readonly property var cool: d.cooling ? d.cooling : ({})

    Card {
        Layout.fillWidth: true
        visible: cool.hot === true
        RowLayout {
            Layout.fillWidth: true
            spacing: 12
            Chip { kind: "setup"; text: "Горячо" }
            Txt {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                color: Theme.warn
                text: "Температура выше " + cool.warn + " °C. Включите режим «Баланс» или «Тишина», проверьте, не закрыты ли вентиляционные отверстия."
            }
            Btn { text: "Сменить режим"; onClicked: goto("performance") }
        }
    }

    GridLayout {
        Layout.fillWidth: true
        columns: width >= 700 ? 3 : 1
        columnSpacing: 16
        rowSpacing: 16

        Repeater {
            model: [
                { key: "cpu", name: "Процессор", note: "Частота снижается из-за жары" },
                { key: "gpu", name: "Видеокарта", note: "Видеокарта сбрасывает скорость из-за жары" },
                { key: "ssd", name: "SSD", note: "" }
            ]
            delegate: Card {
                pad: 14
                Layout.fillWidth: true
                Layout.fillHeight: true
                readonly property var part: root.cool[modelData.key] ? root.cool[modelData.key] : ({})
                RowLayout {
                    Layout.fillWidth: true
                    Txt { Layout.fillWidth: true; text: modelData.name; font.pixelSize: 15; font.weight: Font.DemiBold }
                    Chip {
                        visible: part.throttled === true
                        kind: "setup"
                        text: "Троттлинг"
                        tip: modelData.note
                    }
                }
                RowLayout {
                    Txt { text: part.now ? part.now : "—"; font.pixelSize: 28; font.family: Theme.mono }
                    Txt { text: "°C"; color: Theme.muted; Layout.alignment: Qt.AlignBottom; bottomPadding: 6 }
                }
                Row2 { label: "Максимум за сессию"; value: (part.max ? part.max : "—") + " °C" }
                Spark {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 36
                    implicitHeight: 36
                    values: part.values ? part.values : []
                    lineColor: part.throttled === true ? Theme.warn : Theme.accent
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

    Card {
        Layout.fillWidth: true
        Txt { text: "Все датчики"; font.pixelSize: 16; font.weight: Font.DemiBold }
        Txt {
            visible: tempsModel.count === 0
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            color: Theme.muted
            text: "Датчики температуры не найдены. Установите lm_sensors и запустите sensors-detect."
        }
        Repeater {
            model: tempsModel
            delegate: Row2 { label: model.name; value: model.value + " °C"; valueColor: model.hot ? Theme.err : Theme.text }
        }
    }

    Card {
        Layout.fillWidth: true
        RowLayout {
            Layout.fillWidth: true
            Txt { Layout.fillWidth: true; text: "Вентиляторы"; font.pixelSize: 16; font.weight: Font.DemiBold }
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
            text: "Ядро не показывает обороты вентиляторов этого ноутбука, поэтому DOCKIT их не видит и не меняет. Охлаждение зависит от режима: «Тишина» тише, «Производительность» охлаждает сильнее."
        }
        Btn { text: "Сменить режим"; onClicked: goto("performance") }
    }
}
