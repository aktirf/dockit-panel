import QtQuick
import QtQuick.Layouts

PageFrame {
    title: "Охлаждение"
    subtitle: "Температуры и вентиляторы"

    SyncModel { id: tempsModel }
    SyncModel { id: fansModel }
    function syncAll() {
        tempsModel.sync(d.temps)
        fansModel.sync(d.fans)
    }
    Connections { target: backend; function onStateChanged() { syncAll() } }
    Component.onCompleted: syncAll()

    Card {
        Layout.fillWidth: true
        Txt { text: "Температуры"; font.pixelSize: 16; font.weight: Font.DemiBold }
        Txt {
            visible: !d.temps || d.temps.length === 0
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
            Chip { kind: d.fans && d.fans.length > 0 ? "ok" : "no"; text: d.fans && d.fans.length > 0 ? "Видны" : "Нет данных" }
        }
        Repeater {
            model: fansModel
            delegate: Row2 { label: model.name; value: model.rpm + " об/мин" }
        }
        Txt {
            visible: !d.fans || d.fans.length === 0
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            color: Theme.muted
            text: "Ядро не показывает обороты вентиляторов этого ноутбука, поэтому DOCKIT их не видит и не меняет. Как они работают, зависит от режима: «Тишина» тише, «Производительность» охлаждает сильнее."
        }
        Btn { text: "Сменить режим"; onClicked: goto("performance") }
    }
}
