import QtQuick
import QtQuick.Window
import QtQuick.Layouts
import QtQuick.Controls

Window {
    id: win
    width: 1280
    height: 900
    minimumWidth: 500
    minimumHeight: 460
    visible: true
    title: "DOCKIT"
    readonly property bool compactNav: win.width < 860 || !!(d.settings && d.settings.compact_nav === true)
    property bool journalExpanded: false
    onClosing: function (close) {
        if (backend.trayActive) { close.accepted = false; win.hide() } else Qt.quit()
    }
    color: Theme.bg

    property string page: "overview"
    readonly property var d: backend.state

    SyncModel { id: modesModel }
    SyncModel { id: scenariosModel }
    SyncModel { id: togglesModel }
    SyncModel { id: countsModel }
    SyncModel { id: featuresModel }
    SyncModel { id: journalModel }
    function syncAll() {
        modesModel.sync(d.modes)
        scenariosModel.sync(d.scenarios)
        togglesModel.sync(d.toggles)
        countsModel.sync(d.counts)
        featuresModel.sync(d.features)
        journalModel.sync(d.journal)
    }
    function syncAccent() {
        if (backend && backend.accentColor)
            Theme.accent = backend.accentColor
    }
    Connections {
        target: backend
        function onStateChanged() { win.syncAll() }
        function onSettingsChanged() { win.syncAccent() }
    }
    Component.onCompleted: { syncAll(); syncAccent() }
    readonly property int problems: d.features ? d.features.filter(function (f) { return f.status !== "ok" }).length : 0

    function modeName(id) {
        for (var i = 0; i < d.modes.length; i++)
            if (d.modes[i].id === id) return d.modes[i].name
        return "—"
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        // ---------- sidebar ----------
        Rectangle {
            Layout.preferredWidth: win.compactNav ? 68 : 232
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
                anchors.margins: win.compactNav ? 10 : 14
                anchors.topMargin: 24
                anchors.bottomMargin: 24
                spacing: 4

                RowLayout {
                    Layout.fillWidth: true
                    Layout.bottomMargin: 18
                    Layout.leftMargin: win.compactNav ? 0 : 10
                    spacing: 10
                    Rectangle {
                        Layout.alignment: Qt.AlignHCenter
                        implicitWidth: 34
                        implicitHeight: 34
                        radius: 10
                        color: "#1B2A3A"
                        Icon { anchors.centerIn: parent; name: "gauge"; size: 19; color: Theme.accent }
                        Tip { text: win.compactNav ? ("DOCKIT — " + (d.model || "Ноутбук")) : "" }
                    }
                    ColumnLayout {
                        visible: !win.compactNav
                        Layout.fillWidth: true
                        Layout.minimumWidth: 0
                        spacing: 0
                        Txt { Layout.fillWidth: true; elide: Text.ElideRight; text: "DOCKIT"; font.pixelSize: 15; font.weight: Font.DemiBold }
                        Txt { Layout.fillWidth: true; elide: Text.ElideRight; text: d.model || "Ноутбук"; font.pixelSize: 12; color: Theme.muted }
                    }
                }

                NavItem { compact: win.compactNav; icon: "grid"; text: "Обзор"; active: win.page === "overview"; onClicked: win.page = "overview" }
                NavItem { compact: win.compactNav; icon: "gauge"; text: "Производительность"; active: win.page === "performance"; onClicked: win.page = "performance" }
                NavItem { compact: win.compactNav; icon: "battery"; text: "Питание и батарея"; active: win.page === "battery"; onClicked: win.page = "battery" }
                NavItem { compact: win.compactNav; icon: "fan"; text: "Охлаждение"; active: win.page === "cooling"; onClicked: win.page = "cooling" }
                NavItem { compact: win.compactNav; icon: "mouse"; text: "Периферия"; active: win.page === "peripherals"; onClicked: win.page = "peripherals" }
                NavItem { compact: win.compactNav; icon: "layers"; text: "Профили"; active: win.page === "profiles"; onClicked: win.page = "profiles" }

                Item { Layout.fillHeight: true }

                NavItem { compact: win.compactNav; icon: "pulse"; text: "Диагностика"; badge: win.problems; active: win.page === "diagnostics"; onClicked: win.page = "diagnostics" }
                NavItem { compact: win.compactNav; icon: "sliders"; text: "Настройки"; active: win.page === "settings"; onClicked: win.page = "settings" }
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
            readonly property int sidePad: flick.width < 560 ? 16 : 32
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
                width: Math.min(Math.max(200, flick.width - flick.sidePad * 2), 1020)
                x: Math.max(flick.sidePad, (flick.width - width) / 2)
                y: 28
                spacing: 24

                // header (wraps chips cleanly on narrow tiled windows)
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 12
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4
                        Txt { Layout.fillWidth: true; wrapMode: Text.WordWrap; text: "Обзор"; font.pixelSize: flick.width < 560 ? 22 : 28; font.weight: Font.DemiBold }
                        Txt { Layout.fillWidth: true; wrapMode: Text.WordWrap; text: "Всё важное о ноутбуке на одном экране"; color: Theme.muted }
                    }
                    Flow {
                        Layout.fillWidth: true
                        spacing: 10
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
                }

                // mode + scenarios
                Card {
                    Layout.fillWidth: true
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 12
                        Txt { Layout.fillWidth: true; Layout.minimumWidth: 0; elide: Text.ElideRight; text: "Сценарий"; font.pixelSize: 16; font.weight: Font.DemiBold }
                        Txt { text: "Режим: " + win.modeName(d.currentMode); color: Theme.muted; font.pixelSize: 13; elide: Text.ElideRight }
                    }
                    Flow {
                        Layout.fillWidth: true
                        spacing: 8
                        Repeater {
                            model: scenariosModel
                            delegate: Rectangle {
                                readonly property bool sel: model.id === d.scenario
                                height: 40
                                width: parent && parent.width > 0 ? Math.min(pillText.implicitWidth + 32, Math.max(72, parent.width)) : pillText.implicitWidth + 32
                                radius: 20
                                color: sel ? Theme.accent : Theme.btn
                                border.width: 1
                                border.color: sel ? Theme.accent : Theme.border3
                                Behavior on color { ColorAnimation { duration: 160 } }
                                Txt {
                                    id: pillText
                                    anchors.centerIn: parent
                                    width: Math.max(0, parent.width - 24)
                                    horizontalAlignment: Text.AlignHCenter
                                    elide: Text.ElideRight
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

                // battery and hardware status
                GridLayout {
                    Layout.fillWidth: true
                    columns: width >= 660 ? 2 : 1
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
                            Bar { Layout.fillWidth: true; value: d.battery.percent || 0; fill: Theme.batteryColor(d.battery.percent) }
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
                        id: overviewHardwareCard
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        RowLayout {
                            Layout.fillWidth: true
                            Txt { Layout.fillWidth: true; text: "Процессор и видеокарта"; font.pixelSize: 15; font.weight: Font.DemiBold }
                            Chip {
                                id: overviewGpuChip
                                visible: !!(d.gpu && d.gpu.sleepText && d.gpu.sleepText !== "—")
                                kind: !!(d.gpu && d.gpu.asleep) ? "ok" : ((d.gpu && d.gpu.sleepText === "не засыпает") ? "setup" : "info")
                                text: d.gpu ? "GPU: " + String(d.gpu.sleepText || "—") : ""
                            }
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 12
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                Txt { text: "CPU"; color: Theme.muted; font.pixelSize: 12 }
                                Row {
                                    spacing: 4
                                    Txt { text: d.cpu ? String(d.cpu.temp || "—") : "—"; font.family: Theme.mono; font.pixelSize: 30; font.weight: Font.Medium }
                                    Txt { text: "°C"; color: Theme.muted; anchors.baseline: parent.children[0].baseline }
                                }
                                Txt {
                                    text: (d.cpu && d.cpu.load !== null && d.cpu.load !== undefined) ? ("Загрузка " + String(d.cpu.load) + " %") : "—"
                                    color: Theme.muted; font.pixelSize: 12; font.family: Theme.mono
                                }
                            }
                            Rectangle { width: 1; Layout.fillHeight: true; color: Theme.border }
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                Txt { text: "GPU"; color: Theme.muted; font.pixelSize: 12 }
                                Row {
                                    spacing: 4
                                    Txt {
                                        text: !!(d.gpu && d.gpu.asleep) ? "Спит" : (d.gpu ? String(d.gpu.temp || "—") : "—")
                                        color: !!(d.gpu && d.gpu.asleep) ? Theme.okText : Theme.text
                                        font.family: Theme.mono; font.pixelSize: 30; font.weight: Font.Medium
                                    }
                                    Txt {
                                        visible: !!(d.gpu && !d.gpu.asleep)
                                        text: "°C"; color: Theme.muted; anchors.baseline: parent.children[0].baseline
                                    }
                                }
                                Txt {
                                    text: !!(d.gpu && d.gpu.asleep)
                                          ? "Не тратит батарею"
                                          : ((d.gpu && d.gpu.power && d.gpu.power !== "—") ? (String(d.gpu.power) + " Вт") : "—")
                                    color: Theme.muted; font.pixelSize: 12; font.family: Theme.mono
                                }
                            }
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            Txt { Layout.fillWidth: true; text: "Частота CPU"; color: Theme.soft }
                            Txt { text: (d.cpu ? String(d.cpu.freq || "—") : "—") + " ГГц"; font.family: Theme.mono }
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            visible: !!(d.gpu && d.gpu.holders && d.gpu.holders.length > 0)
                            Txt { Layout.fillWidth: true; text: "Держат GPU"; color: Theme.soft }
                            Txt { text: (d.gpu && d.gpu.holders) ? d.gpu.holders.join(", ") : ""; color: Theme.warn; font.pixelSize: 12; elide: Text.ElideRight }
                        }
                        Item { Layout.fillHeight: true }
                        Rectangle { Layout.fillWidth: true; height: 1; color: Theme.border }
                        Btn {
                            text: "Открыть «Производительность»"
                            onClicked: win.page = "performance"
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
                                icon: String(model.id || "")
                                label: model.label
                                on: model.on
                                can: model.can
                                tip: backend.describeToggle(model.id)
                                onToggled: backend.toggle(model.id)
                            }
                        }
                    }
                }

                // quick display strip (brightness slider + refresh rate)
                Card {
                    id: overviewDisplayCard
                    Layout.fillWidth: true
                    pad: 16
                    readonly property bool hasBright: !!(d.display && d.display.brightness !== null && d.display.brightness !== undefined)
                    readonly property bool hasRates: !!(d.display && d.display.rates && d.display.rates.length > 0)
                    visible: hasBright || hasRates

                    GridLayout {
                        Layout.fillWidth: true
                        columns: (overviewDisplayCard.hasBright && overviewDisplayCard.hasRates && content.width >= 660) ? 2 : 1
                        columnSpacing: 20
                        rowSpacing: 12

                        ColumnLayout {
                            visible: overviewDisplayCard.hasBright
                            Layout.fillWidth: true
                            Layout.minimumWidth: 0
                            spacing: 6
                            RowLayout {
                                Layout.fillWidth: true
                                Icon { name: "sun"; size: 15; color: Theme.accent }
                                Txt { Layout.fillWidth: true; text: "Яркость экрана"; font.pixelSize: 13; color: Theme.soft }
                                Txt {
                                    text: overviewDisplayCard.hasBright ? (overviewBrightSlider.displayValue + " %") : "—"
                                    font.family: Theme.mono
                                    font.pixelSize: 13
                                }
                            }
                            SmoothSlider {
                                id: overviewBrightSlider
                                from: 5
                                to: 100
                                handleSize: 16
                                targetValue: overviewDisplayCard.hasBright ? Number(d.display.brightness) : 50
                                onCommitted: function (val) { backend.setBrightness(val) }
                            }
                        }

                        ColumnLayout {
                            visible: overviewDisplayCard.hasRates
                            Layout.fillWidth: true
                            Layout.minimumWidth: 0
                            spacing: 6
                            RowLayout {
                                Layout.fillWidth: true
                                Icon { name: "monitor"; size: 15; color: Theme.accent }
                                Txt { Layout.fillWidth: true; text: "Частота экрана"; font.pixelSize: 13; color: Theme.soft }
                                Txt {
                                    text: (d.display && d.display.refresh) ? String(d.display.refresh) + " Гц" : "—"
                                    font.family: Theme.mono
                                    font.pixelSize: 13
                                }
                            }
                            SegmentBar {
                                id: overviewRatesBar
                                options: (d.display && d.display.rates ? d.display.rates : []).map(function (r) {
                                    return { id: String(r), label: String(r) + " Гц", tip: "" }
                                })
                                current: (d.display && d.display.refresh) ? String(d.display.refresh) : ""
                                onPicked: function (val) { backend.setRefresh(Number(val)) }
                            }
                        }
                    }
                }

                // what the program switched and why
                Card {
                    Layout.fillWidth: true
                    RowLayout {
                        Layout.fillWidth: true
                        Txt { Layout.fillWidth: true; text: "Что переключалось"; font.pixelSize: 16; font.weight: Font.DemiBold }
                        Btn {
                            visible: journalModel.count > 3
                            implicitHeight: 30
                            text: win.journalExpanded ? "Свернуть" : "Все (" + journalModel.count + ")"
                            onClicked: win.journalExpanded = !win.journalExpanded
                        }
                    }
                    Txt {
                        visible: journalModel.count === 0
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                        color: Theme.muted
                        font.pixelSize: 13
                        text: "Пока ничего. Здесь появятся смены профилей и режимов с причиной, например «Авто: Работа (работа от батареи)»."
                    }
                    Repeater {
                        model: journalModel
                        delegate: RowLayout {
                            visible: win.journalExpanded || index < 3
                            Layout.fillWidth: true
                            spacing: 12
                            Txt { text: model.time; color: Theme.muted; font.family: Theme.mono; font.pixelSize: 13 }
                            Txt { Layout.fillWidth: true; text: model.text; wrapMode: Text.WordWrap; font.pixelSize: 13 }
                        }
                    }
                }

                // problems: details are on the Diagnostics page
                Card {
                    Layout.fillWidth: true
                    GridLayout {
                        Layout.fillWidth: true
                        columns: content.width >= 600 ? 3 : 1
                        columnSpacing: 12
                        rowSpacing: 10
                        Chip { kind: win.problems > 0 ? "setup" : "ok"; text: win.problems > 0 ? "Не работает: " + win.problems : "Всё работает" }
                        Txt {
                            Layout.fillWidth: true
                            Layout.minimumWidth: 0
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
