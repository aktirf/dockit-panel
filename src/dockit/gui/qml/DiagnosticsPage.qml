import QtQuick
import QtQuick.Layouts

PageFrame {
    title: "Диагностика"
    subtitle: "Что работает на этом ноутбуке, что нет и как это исправить"

    SyncModel { id: countsModel }
    SyncModel { id: featuresModel }
    function syncAll() {
        countsModel.sync(d.counts)
        featuresModel.sync(d.features)
    }
    Connections { target: backend; function onStateChanged() { syncAll() } }
    Component.onCompleted: syncAll()

    RowLayout {
        Layout.fillWidth: true
        spacing: 10
        Repeater {
            model: countsModel
            delegate: Chip { kind: model.status; text: model.text }
        }
        Item { Layout.fillWidth: true }
        Btn { text: "Скопировать отчёт"; tip: "Копирует список функций и данные о системе, чтобы вставить в сообщение об ошибке."; onClicked: backend.copyReport() }
    }

    Card {
        Layout.fillWidth: true
        Txt { text: "Система"; font.pixelSize: 16; font.weight: Font.DemiBold }
        Row2 { label: "Модель"; value: d.model ? d.model : "—" }
        Row2 { label: "Система"; value: d.system && d.system.distro ? d.system.distro : "—" }
        Row2 { label: "Ядро"; value: d.system && d.system.kernel ? d.system.kernel : "—" }
        Row2 { label: "BIOS"; value: d.system && d.system.bios ? d.system.bios : "—" }
    }

    Repeater {
        model: featuresModel
        delegate: Rectangle {
            Layout.fillWidth: true
            implicitHeight: rowLayout.implicitHeight + 28
            radius: 12
            color: Theme.card
            border.width: 1
            border.color: Theme.border
            RowLayout {
                id: rowLayout
                anchors.fill: parent
                anchors.leftMargin: 16
                anchors.rightMargin: 16
                spacing: 14
                Rectangle {
                    implicitWidth: 36
                    implicitHeight: 36
                    radius: 10
                    color: Theme.statusBg(model.status)
                    Icon { anchors.centerIn: parent; size: 18; name: Theme.statusIcon(model.status); color: Theme.statusColor(model.status) }
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2
                    Txt { text: model.name; font.weight: Font.Medium }
                    Txt { Layout.fillWidth: true; text: model.detail; wrapMode: Text.WordWrap; font.pixelSize: 13; color: Theme.muted }
                    Txt {
                        Layout.fillWidth: true
                        visible: model.hint !== ""
                        text: "Как исправить: " + model.hint
                        wrapMode: Text.WordWrap
                        font.pixelSize: 13
                        color: Theme.warn
                    }
                }
                Chip { kind: model.status; text: model.statusText }
            }
        }
    }
}
