import QtQuick
import QtQuick.Layouts

PageFrame {
    id: diagPage
    title: "Диагностика"
    subtitle: "Что работает на этом ноутбуке, что нет и как это исправить"

    property string filter: "all"   // "all" | "issues" | "ok"

    SyncModel { id: countsModel }
    SyncModel { id: featuresModel }

    readonly property int totalCount: d.features ? d.features.length : 0
    readonly property int issueCount: d.features ? d.features.filter(function (f) { return f.status !== "ok" }).length : 0
    readonly property int okCount: totalCount - issueCount

    function filteredFeatures() {
        var arr = d.features ? d.features : []
        if (filter === "issues")
            return arr.filter(function (f) { return f.status !== "ok" })
        if (filter === "ok")
            return arr.filter(function (f) { return f.status === "ok" })
        return arr
    }
    function syncAll() {
        countsModel.sync(d.counts)
        featuresModel.sync(filteredFeatures())
    }
    onFilterChanged: syncAll()
    Connections { target: backend; function onStateChanged() { syncAll() } }
    Component.onCompleted: syncAll()

    // Filter bar + copy report button
    GridLayout {
        Layout.fillWidth: true
        columns: diagPage.width >= 660 ? 2 : 1
        columnSpacing: 12
        rowSpacing: 10

        SegmentBar {
            id: diagFilterBar
            current: diagPage.filter
            options: [
                { id: "all", label: "Все (" + diagPage.totalCount + ")", tip: "" },
                { id: "issues", label: "Проблемы (" + diagPage.issueCount + ")", tip: "" },
                { id: "ok", label: "Работают (" + diagPage.okCount + ")", tip: "" }
            ]
            onPicked: function (val) { diagPage.filter = val }
        }
        Btn {
            Layout.alignment: diagPage.width >= 660 ? Qt.AlignRight : Qt.AlignLeft
            text: "Скопировать отчёт"
            implicitHeight: 42
            tip: "Копирует список функций и данные о системе, чтобы вставить в сообщение об ошибке."
            onClicked: backend.copyReport()
        }
    }

    // System info card in 2-column grid
    Card {
        Layout.fillWidth: true
        pad: 16
        Txt { text: "Система"; font.pixelSize: 15; font.weight: Font.DemiBold }
        GridLayout {
            Layout.fillWidth: true
            columns: diagPage.width >= 620 ? 2 : 1
            columnSpacing: 20
            rowSpacing: 6
            Row2 { label: "Модель"; value: d.model ? d.model : "—" }
            Row2 { label: "Система"; value: d.system && d.system.distro ? d.system.distro : "—" }
            Row2 { label: "Ядро"; value: d.system && d.system.kernel ? d.system.kernel : "—" }
            Row2 { label: "BIOS"; value: d.system && d.system.bios ? d.system.bios : "—" }
        }
    }

    // Empty state for "Проблемы" when everything works
    Card {
        visible: featuresModel.count === 0 && diagPage.filter === "issues"
        Layout.fillWidth: true
        RowLayout {
            Layout.fillWidth: true
            spacing: 12
            Chip { kind: "ok"; icon: "check"; text: "Всё отлично" }
            Txt { Layout.fillWidth: true; wrapMode: Text.WordWrap; text: "Проблемных функций не найдено — всё, что поддерживает этот ноутбук, работает."; color: Theme.muted }
        }
    }

    // Feature list
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

    // Service log viewer in dark console box
    Card {
        Layout.fillWidth: true
        GridLayout {
            Layout.fillWidth: true
            columns: diagPage.width >= 600 ? 2 : 1
            columnSpacing: 12
            rowSpacing: 8
            Txt { Layout.fillWidth: true; text: "Журнал фоновой службы"; font.pixelSize: 16; font.weight: Font.DemiBold }
            Flow {
                Layout.alignment: diagPage.width >= 600 ? Qt.AlignRight : Qt.AlignLeft
                spacing: 8
                Btn {
                    text: backend.logText !== "" ? "Обновить" : "Показать"
                    implicitHeight: 34
                    tip: "Загрузить последние 40 строк журнала службы DOCKIT."
                    onClicked: backend.loadLog()
                }
                Btn {
                    visible: backend.logText !== ""
                    text: "Скопировать"
                    implicitHeight: 34
                    tip: "Скопировать журнал в буфер обмена."
                    onClicked: backend.copyLog()
                }
            }
        }
        Rectangle {
            visible: backend.logText !== ""
            Layout.fillWidth: true
            implicitHeight: logTxt.implicitHeight + 24
            radius: 10
            color: Theme.panel
            border.width: 1
            border.color: Theme.border
            Txt {
                id: logTxt
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: 12
                text: backend.logText
                wrapMode: Text.WrapAnywhere
                font.family: Theme.mono
                font.pixelSize: 11
                color: Theme.soft
            }
        }
    }
}
