import QtQuick
import QtQuick.Layouts

PageFrame {
    title: "Периферия"
    subtitle: "Подключённые устройства и что DOCKIT умеет с ними делать"

    Txt {
        visible: !d.peripherals || d.peripherals.length === 0
        text: "USB-устройства не найдены."
        color: Theme.muted
    }
    Repeater {
        model: periphModel
        delegate: Card {
            Layout.fillWidth: true
            RowLayout {
                Layout.fillWidth: true
                spacing: 12
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2
                    Txt { text: model.name; font.pixelSize: 15; font.weight: Font.DemiBold }
                    Txt { text: model.kind + "  ·  USB " + model.usbId; color: Theme.muted; font.pixelSize: 12 }
                }
                Chip {
                    kind: model.known ? "ok" : "no"
                    text: model.known ? "Устройство известно" : "Нет в базе"
                    tip: model.known ? "Это устройство есть в базе DOCKIT." : "Устройства нет в базе. Его можно добавить в папку devices проекта."
                }
            }
            Txt {
                Layout.fillWidth: true
                visible: model.notes !== ""
                wrapMode: Text.WordWrap
                text: model.notes
                color: Theme.muted
                font.pixelSize: 13
            }
        }
    }
    SyncModel { id: periphModel }
    SyncModel { id: btModel }
    SyncModel { id: outModel }
    SyncModel { id: inModel }
    function syncAll() {
        periphModel.sync(d.peripherals)
        btModel.sync(d.bluetooth)
        outModel.sync(d.audio && d.audio.outputs ? d.audio.outputs.map(function (t) { return { text: t } }) : [])
        inModel.sync(d.audio && d.audio.inputs ? d.audio.inputs.map(function (t) { return { text: t } }) : [])
    }
    Connections { target: backend; function onStateChanged() { syncAll() } }
    Component.onCompleted: syncAll()

    Card {
        Layout.fillWidth: true
        Txt { text: "Bluetooth-устройства"; font.pixelSize: 16; font.weight: Font.DemiBold }
        Txt {
            visible: btModel.count === 0
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            color: Theme.muted
            font.pixelSize: 13
            text: "Подключённых Bluetooth-устройств нет."
        }
        Repeater {
            model: btModel
            delegate: Row2 { label: model.name; value: model.battery >= 0 ? "батарея " + model.battery + " %" : "батарея неизвестна" }
        }
    }

    Card {
        Layout.fillWidth: true
        Txt { text: "Звук: быстрый выбор"; font.pixelSize: 16; font.weight: Font.DemiBold }
        Txt { text: "Куда играет звук"; color: Theme.soft }
        Flow {
            Layout.fillWidth: true
            spacing: 8
            Repeater {
                model: outModel
                delegate: Pill {
                    text: model.text
                    sel: d.audio && d.audio.outputDefault === model.text
                    onClicked: backend.setAudio("output", model.text)
                }
            }
        }
        Txt { text: "Микрофон"; color: Theme.soft }
        Flow {
            Layout.fillWidth: true
            spacing: 8
            Repeater {
                model: inModel
                delegate: Pill {
                    text: model.text
                    sel: d.audio && d.audio.inputDefault === model.text
                    onClicked: backend.setAudio("input", model.text)
                }
            }
        }
        Txt {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            color: Theme.muted
            font.pixelSize: 12
            text: "Чтобы звук переключался сам при смене профиля, укажите устройства в профиле."
        }
        Btn { text: "Открыть профили"; onClicked: goto("profiles") }
    }
}
