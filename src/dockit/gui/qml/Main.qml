import QtQuick
import QtQuick.Window
import QtQuick.Layouts
import QtQuick.Controls

Window {
    id: win
    width: 1280
    height: 900
    minimumWidth: 760
    minimumHeight: 520
    visible: true
    title: "DOCKIT"
    color: Theme.bg

    property string page: "overview"
    readonly property var d: backend.state

    SyncModel { id: modesModel }
    SyncModel { id: scenariosModel }
    SyncModel { id: togglesModel }
    SyncModel { id: countsModel }
    SyncModel { id: featuresModel }
    function syncAll() {
        modesModel.sync(d.modes)
        scenariosModel.sync(d.scenarios)
        togglesModel.sync(d.toggles)
        countsModel.sync(d.counts)
        featuresModel.sync(d.features)
    }
    Connections { target: backend; function onStateChanged() { win.syncAll() } }
    Component.onCompleted: syncAll()
    readonly property int problems: d.features ? d.features.filter(function (f) { return f.status !== "ok" }).length : 0

    function modeName(id) {
        for (var i = 0; i < d.modes.length; i++)
            if (d.modes[i].id === id) return d.modes[i].name
        return "—"
    }
    function soon() { backend.say("Эта страница ещё в разработке") }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        // ---------- sidebar ----------
        Rectangle {
            Layout.preferredWidth: 240
            Layout.fillHeight: true
            color: Theme.panel

            Rectangle {
                width: 1
                height: parent.height
                anchors.right: parent.right
                color: Theme.border
            }

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 14
                anchors.topMargin: 24
                anchors.bottomMargin: 24
                spacing: 4

                RowLayout {
                    Layout.bottomMargin: 18
                    Layout.leftMargin: 10
                    spacing: 10
                    Rectangle {
                        implicitWidth: 34
                        implicitHeight: 34
                        radius: 10
                        color: "#1B2A3A"
                        Icon { anchors.centerIn: parent; name: "gauge"; size: 19; color: Theme.accent }
                    }
                    ColumnLayout {
                        spacing: 0
                        Txt { text: "DOCKIT"; font.pixelSize: 15; font.weight: Font.DemiBold }
                        Txt { text: d.model || "Ноутбук"; font.pixelSize: 12; color: Theme.muted }
                    }
                }

                NavItem { icon: "grid"; text: "Обзор"; active: win.page === "overview"; onClicked: win.page = "overview" }
                NavItem { icon: "gauge"; text: "Производительность"; active: win.page === "performance"; onClicked: win.page = "performance" }
                NavItem { icon: "battery"; text: "Питание и батарея"; active: win.page === "battery"; onClicked: win.page = "battery" }
                NavItem { icon: "fan"; text: "Охлаждение"; active: win.page === "cooling"; onClicked: win.page = "cooling" }
                NavItem { icon: "sun"; text: "Подсветка"; active: win.page === "backlight"; onClicked: win.page = "backlight" }
                NavItem { icon: "mouse"; text: "Периферия"; active: win.page === "peripherals"; onClicked: win.page = "peripherals" }
                NavItem { icon: "layers"; text: "Профили"; active: win.page === "profiles"; onClicked: win.page = "profiles" }

                Item { Layout.fillHeight: true }

                NavItem { icon: "pulse"; text: "Диагностика"; badge: win.problems; active: win.page === "diagnostics"; onClicked: win.page = "diagnostics" }
                NavItem { icon: "sliders"; text: "Настройки"; active: win.page === "settings"; onClicked: win.page = "settings" }
            }
        }

        // ---------- content ----------
        ProfilesPage {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: win.page === "profiles"
            onVisibleChanged: if (visible) fadeProfiles.restart()
            NumberAnimation on opacity { id: fadeProfiles; from: 0; to: 1; duration: 220; easing.type: Easing.OutCubic; running: false }
            d: win.d
        }

        PerformancePage {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: win.page === "performance"
            onVisibleChanged: if (visible) fadePerformance.restart()
            NumberAnimation on opacity { id: fadePerformance; from: 0; to: 1; duration: 220; easing.type: Easing.OutCubic; running: false }
            d: win.d
        }

        BatteryPage {
            id: batteryPage
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: win.page === "battery"
            onVisibleChanged: if (visible) batteryFade.restart()
            NumberAnimation on opacity { id: batteryFade; from: 0; to: 1; duration: 220; easing.type: Easing.OutCubic; running: false }
            onGoto: function (name) { win.page = name }
            d: win.d
        }

        CoolingPage {
            id: coolingPage
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: win.page === "cooling"
            onVisibleChanged: if (visible) coolingFade.restart()
            NumberAnimation on opacity { id: coolingFade; from: 0; to: 1; duration: 220; easing.type: Easing.OutCubic; running: false }
            onGoto: function (name) { win.page = name }
            d: win.d
        }

        BacklightPage {
            id: backlightPage
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: win.page === "backlight"
            onVisibleChanged: if (visible) backlightFade.restart()
            NumberAnimation on opacity { id: backlightFade; from: 0; to: 1; duration: 220; easing.type: Easing.OutCubic; running: false }
            onGoto: function (name) { win.page = name }
            d: win.d
        }

        PeripheralsPage {
            id: peripheralsPage
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: win.page === "peripherals"
            onVisibleChanged: if (visible) peripheralsFade.restart()
            NumberAnimation on opacity { id: peripheralsFade; from: 0; to: 1; duration: 220; easing.type: Easing.OutCubic; running: false }
            onGoto: function (name) { win.page = name }
            d: win.d
        }

        DiagnosticsPage {
            id: diagnosticsPage
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: win.page === "diagnostics"
            onVisibleChanged: if (visible) diagnosticsFade.restart()
            NumberAnimation on opacity { id: diagnosticsFade; from: 0; to: 1; duration: 220; easing.type: Easing.OutCubic; running: false }
            onGoto: function (name) { win.page = name }
            d: win.d
        }

        SettingsPage {
            id: settingsPage
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: win.page === "settings"
            onVisibleChanged: if (visible) settingsFade.restart()
            NumberAnimation on opacity { id: settingsFade; from: 0; to: 1; duration: 220; easing.type: Easing.OutCubic; running: false }
            onGoto: function (name) { win.page = name }
            d: win.d
        }

        Flickable {
            id: flick
            visible: win.page === "overview"
            onVisibleChanged: if (visible) fadeOverview.restart()
            NumberAnimation on opacity { id: fadeOverview; from: 0; to: 1; duration: 220; easing.type: Easing.OutCubic; running: false }
            Layout.fillWidth: true
            Layout.fillHeight: true
            contentWidth: width
            contentHeight: content.implicitHeight + 68
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar {}

            Txt {
                visible: !d.ready
                anchors.centerIn: parent
                text: "Проверяю ноутбук…"
                color: Theme.muted
                font.pixelSize: 16
            }

            ColumnLayout {
                id: content
                visible: d.ready
                x: 32
                y: 28
                width: flick.width - 64
                spacing: 24

                // header
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 16
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4
                        Txt { text: "Обзор"; font.pixelSize: 28; font.weight: Font.DemiBold }
                        Txt { text: "Всё важное о ноутбуке на одном экране"; color: Theme.muted }
                    }
                    Chip {
                        big: true
                        kind: d.service ? "ok" : "no"
                        text: d.service ? "Фоновая служба работает" : "Фоновая служба не запущена"
                    }
                    Chip {
                        big: true
                        text: d.okCount + " из " + d.total + " функций работают"
                    }
                }

                // mode + scenarios
                Card {
                    Layout.fillWidth: true
                    RowLayout {
                        Layout.fillWidth: true
                        Txt { Layout.fillWidth: true; text: "Сценарий"; font.pixelSize: 16; font.weight: Font.DemiBold }
                        Txt { text: "Режим сейчас: " + win.modeName(d.currentMode); color: Theme.muted; font.pixelSize: 13 }
                    }
                    Flow {
                        Layout.fillWidth: true
                        spacing: 8
                        Repeater {
                            model: scenariosModel
                            delegate: Rectangle {
                                readonly property bool sel: model.id === d.scenario
                                height: 44
                                width: pillText.implicitWidth + 36
                                radius: 22
                                color: sel ? Theme.accent : Theme.btn
                                border.width: 1
                                border.color: sel ? Theme.accent : Theme.border3
                                Behavior on color { ColorAnimation { duration: 160 } }
                                Txt {
                                    id: pillText
                                    anchors.centerIn: parent
                                    text: model.name
                                    color: sel ? "#0B1218" : Theme.soft
                                    font.weight: sel ? Font.DemiBold : Font.Medium
                                }
                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: backend.setScenario(model.id)
                                }
                            }
                        }
                    }
                }

                // battery and graphics mode
                GridLayout {
                    Layout.fillWidth: true
                    columns: Math.max(1, Math.min(2, Math.floor((width + 16) / 296)))
                    columnSpacing: 16
                    rowSpacing: 16



                    Card {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        RowLayout {
                            Layout.fillWidth: true
                            Txt { Layout.fillWidth: true; text: "Батарея"; font.pixelSize: 15; font.weight: Font.DemiBold }
                            Chip {
                                kind: d.battery.status || "no"
                                icon: Theme.statusIcon(d.battery.status || "no")
                                text: d.battery.statusText || "Нет данных"
                            }
                        }
                        Row {
                            spacing: 8
                            Txt {
                                text: d.battery.percent !== undefined && d.battery.percent !== null ? d.battery.percent : "—"
                                font.family: Theme.mono
                                font.pixelSize: 36
                                font.weight: Font.Medium
                            }
                            Txt { text: "%"; color: Theme.muted; anchors.baseline: parent.children[0].baseline }
                        }
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 6
                            RowLayout {
                                Layout.fillWidth: true
                                Txt { Layout.fillWidth: true; text: d.battery.text || ""; font.pixelSize: 13; color: Theme.muted }
                                Txt { text: d.battery.source || ""; font.pixelSize: 13 }
                            }
                            Bar { Layout.fillWidth: true; value: d.battery.percent || 0; fill: Theme.ok }
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            Txt { Layout.fillWidth: true; text: "Состояние батареи"; color: Theme.soft }
                            Txt { text: (d.battery.health || "—") + " %"; font.family: Theme.mono }
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            Txt { Layout.fillWidth: true; text: "Циклов зарядки"; color: Theme.soft }
                            Txt {
                                text: d.battery.cycles !== undefined && d.battery.cycles !== null ? d.battery.cycles : "—"
                                font.family: Theme.mono
                            }
                        }
                        Item { Layout.fillHeight: true }
                        Rectangle { Layout.fillWidth: true; height: 1; color: Theme.border }
                        RowLayout {
                            Layout.fillWidth: true
                            Txt { Layout.fillWidth: true; text: "Лимит заряда"; color: Theme.soft }
                            Chip {
                                kind: d.limit.status || "no"
                                icon: Theme.statusIcon(d.limit.status || "no")
                                text: d.limit.statusText || "Нет данных"
                            }
                        }
                    }

                    Card {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        RowLayout {
                            Layout.fillWidth: true
                            Txt { Layout.fillWidth: true; text: "Режим графики"; font.pixelSize: 15; font.weight: Font.DemiBold }
                            Chip { kind: "root"; icon: "lock"; text: "Только в BIOS" }
                        }
                        Txt { text: "Не определяется"; font.pixelSize: 22; font.weight: Font.DemiBold }
                        Txt {
                            Layout.fillWidth: true
                            text: "Переключатель MUX (дискретная или гибридная графика) DOCKIT пока не умеет ни читать, ни менять. Его можно поменять в BIOS или в GiMATE на Windows."
                            wrapMode: Text.WordWrap
                            color: Theme.muted
                            lineHeight: 1.25
                        }
                        Item { Layout.fillHeight: true }
                        Rectangle { Layout.fillWidth: true; height: 1; color: Theme.border }
                        Btn {
                            text: "Как это изменить"
                            onClicked: backend.say("MUX меняется в BIOS или в GiMATE (Windows), потом нужна перезагрузка")
                        }
                    }
                }

                // quick toggles
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 12
                    Txt { text: "Быстрые переключатели"; font.pixelSize: 16; font.weight: Font.DemiBold }
                    GridLayout {
                        Layout.fillWidth: true
                        columns: (width + 12) >= 4 * 222 ? 4 : ((width + 12) >= 2 * 222 ? 2 : 1)
                        columnSpacing: 12
                        rowSpacing: 12
                        Repeater {
                            model: togglesModel
                            delegate: ToggleCard {
                                Layout.fillWidth: true
                                label: model.label
                                on: model.on
                                can: model.can
                                tip: backend.describeToggle(model.id)
                                onToggled: backend.toggle(model.id)
                            }
                        }
                    }
                }

                // problems: details are on the Diagnostics page
                Card {
                    Layout.fillWidth: true
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 12
                        Chip { kind: win.problems > 0 ? "setup" : "ok"; text: win.problems > 0 ? "Не работает: " + win.problems : "Всё работает" }
                        Txt {
                            Layout.fillWidth: true
                            wrapMode: Text.WordWrap
                            color: Theme.muted
                            text: win.problems > 0 ? "Некоторые функции недоступны. Что именно и как исправить, написано в «Диагностике»." : "Все функции этого ноутбука, которые знает DOCKIT, работают."
                        }
                        Btn { text: "Открыть «Диагностику»"; onClicked: win.page = "diagnostics" }
                    }
                }
            }
        }
    }

    // ---------- message at the bottom ----------
    Rectangle {
        id: toastBox
        visible: backend.toast !== ""
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 28
        width: Math.min(parent.width - 48, toastText.implicitWidth + 40)
        height: 44
        radius: 12
        color: "#223140"
        border.width: 1
        border.color: "#2F5A80"
        Txt {
            id: toastText
            anchors.centerIn: parent
            width: parent.width - 32
            horizontalAlignment: Text.AlignHCenter
            elide: Text.ElideRight
            text: backend.toast
        }
    }
    Timer {
        id: toastTimer
        interval: 4500
        onTriggered: backend.clearToast()
    }
    Connections {
        target: backend
        function onToastChanged() { toastTimer.restart() }
    }
}
