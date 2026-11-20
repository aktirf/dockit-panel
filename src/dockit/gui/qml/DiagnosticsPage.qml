import QtQuick
import QtQuick.Layouts

PageFrame {
    id: diagPage
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

    Flow {
        Layout.fillWidth: true
        spacing: 10
        Repeater {
            model: countsModel
            delegate: Chip { kind: model.status; text: model.text }
        }
        Btn { text: "Скопировать отчёт"; implicitHeight: 34; tip: "Копирует список функций и данные о системе, чтобы вставить в сообщение об ошибке."; onClicked: backend.copyReport() }
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
            GridLayout {
                id: rowLayout
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                anchors.leftMargin: 16
                anchors.rightMargin: 16
                columns: diagPage.width >= 640 ? 2 : 1
                columnSpacing: 14
                rowSpacing: 10
                RowLayout {
                    Layout.fillWidth: true
                    Layout.minimumWidth: 0
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
                        Layout.minimumWidth: 0
                        spacing: 2
                        Txt { Layout.fillWidth: true; wrapMode: Text.WordWrap; text: model.name; font.weight: Font.Medium }
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
                }
                Flow {
                    Layout.alignment: diagPage.width >= 640 ? Qt.AlignRight | Qt.AlignVCenter : Qt.AlignLeft
                    spacing: 8
                    Btn {
                        visible: model.fix !== ""
                        text: "Установить"
                        implicitHeight: 34
                        tip: "Установит пакеты: " + model.fix + ". Попросит пароль."
                        onClicked: backend.installFix(model.id)
                    }
                    Chip { kind: model.status; text: model.statusText }
                }
            }
        }
    }

    Card {
        Layout.fillWidth: true
        RowLayout {
            Layout.fillWidth: true
            Txt { Layout.fillWidth: true; text: "Журнал фоновой службы"; font.pixelSize: 16; font.weight: Font.DemiBold }
            Btn { text: "Показать"; implicitHeight: 34; tip: "Последние 40 строк журнала службы DOCKIT: помогает понять, почему что-то не работает."; onClicked: backend.loadLog() }
        }
        Txt {
            visible: backend.logText !== ""
            Layout.fillWidth: true
            text: backend.logText
            wrapMode: Text.WrapAnywhere
            font.family: Theme.mono
            font.pixelSize: 11
            color: Theme.muted
        }
    }
}
