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
    function syncAll() {
        periphModel.sync(d.peripherals)
    }
    Connections { target: backend; function onStateChanged() { syncAll() } }
    Component.onCompleted: syncAll()

    Card {
        Layout.fillWidth: true
        Txt { text: "Звук"; font.pixelSize: 16; font.weight: Font.DemiBold }
        Txt {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            color: Theme.muted
            text: "Наушники и микрофон выбираются в профилях: при включении профиля DOCKIT переключает выход и вход звука."
        }
        Btn { text: "Открыть профили"; onClicked: goto("profiles") }
    }
}
