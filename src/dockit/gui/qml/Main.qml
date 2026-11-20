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
    function syncLang() {
        if (backend && backend.t)
            Theme.t = backend.t
    }
    Connections {
        target: backend
        function onStateChanged() { win.syncAll() }
        function onSettingsChanged() { win.syncAccent() }
        function onLangChanged() { win.syncLang() }
    }
    Component.onCompleted: { syncAll(); syncAccent(); syncLang() }
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
                        Tip { text: win.compactNav ? ("DOCKIT — " + (d.model || Theme.tr("app_laptop"))) : "" }
                    }
                    ColumnLayout {
                        visible: !win.compactNav
                        Layout.fillWidth: true
                        Layout.minimumWidth: 0
                        spacing: 0
                        Txt { Layout.fillWidth: true; elide: Text.ElideRight; text: "DOCKIT"; font.pixelSize: 15; font.weight: Font.DemiBold }
                        Txt { Layout.fillWidth: true; elide: Text.ElideRight; text: d.model || Theme.tr("app_laptop"); font.pixelSize: 12; color: Theme.muted }
                    }
                }

                NavItem { compact: win.compactNav; icon: "grid"; text: Theme.tr("nav_overview"); active: win.page === "overview"; onClicked: win.page = "overview" }
                NavItem { compact: win.compactNav; icon: "gauge"; text: Theme.tr("nav_performance"); active: win.page === "performance"; onClicked: win.page = "performance" }
                NavItem { compact: win.compactNav; icon: "battery"; text: Theme.tr("nav_battery"); active: win.page === "battery"; onClicked: win.page = "battery" }
                NavItem { compact: win.compactNav; icon: "fan"; text: Theme.tr("nav_cooling"); active: win.page === "cooling"; onClicked: win.page = "cooling" }
                NavItem { compact: win.compactNav; icon: "mouse"; text: Theme.tr("nav_peripherals"); active: win.page === "peripherals"; onClicked: win.page = "peripherals" }
                NavItem { compact: win.compactNav; icon: "layers"; text: Theme.tr("nav_profiles"); active: win.page === "profiles"; onClicked: win.page = "profiles" }

                Item { Layout.fillHeight: true }

                NavItem { compact: win.compactNav; icon: "pulse"; text: Theme.tr("nav_diagnostics"); badge: win.problems; active: win.page === "diagnostics"; onClicked: win.page = "diagnostics" }
                NavItem { compact: win.compactNav; icon: "sliders"; text: Theme.tr("nav_settings"); active: win.page === "settings"; onClicked: win.page = "settings" }
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
                text: Theme.tr("app_checking")
                color: Theme.muted
                font.pixelSize: 16
            }

            ColumnLayout {
                id: content
                visible: d.ready
                width: Math.min(Math.max(200, flick.width - flick.sidePad * 2), 1020)
                x: Math.max(flick.sidePad, (flick.width - width) / 2)
                y: 28
                spacing: 20

                // 1. Hero header banner (subtle accent gradient, model title, live status chips)
                Rectangle {
                    id: overviewHero
                    Layout.fillWidth: true
                    implicitHeight: heroCol.implicitHeight + 36
                    radius: 18
                    border.width: 1
                    border.color: Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.28)
                    gradient: Gradient {
                        orientation: Gradient.Horizontal
                        GradientStop { position: 0.0; color: Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.14) }
                        GradientStop { position: 0.55; color: Theme.card }
                        GradientStop { position: 1.0; color: Theme.card }
                    }

                    ColumnLayout {
                        id: heroCol
                        anchors.fill: parent
                        anchors.margins: 18
                        spacing: 14

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 14
                            Rectangle {
                                implicitWidth: 44
                                implicitHeight: 44
                                radius: 13
                                color: Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.18)
                                border.width: 1
                                border.color: Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.35)
                                Icon { anchors.centerIn: parent; name: "gauge"; size: 22; color: Theme.accent }
                            }
                            ColumnLayout {
                                Layout.fillWidth: true
                                Layout.minimumWidth: 0
                                spacing: 2
                                Txt {
                                    Layout.fillWidth: true
                                    elide: Text.ElideRight
                                    text: d.model ? String(d.model) : Theme.tr("overview_title")
                                    font.pixelSize: flick.width < 560 ? 19 : 24
                                    font.weight: Font.DemiBold
                                }
                                Txt {
                                    Layout.fillWidth: true
                                    wrapMode: Text.WordWrap
                                    text: Theme.tr("overview_sub")
                                    color: Theme.muted
                                    font.pixelSize: 13
                                }
                            }
                        }

                        Flow {
                            Layout.fillWidth: true
                            spacing: 8
                            Chip {
                                big: true
                                kind: d.service ? "ok" : "no"
                                icon: d.service ? "check" : "x"
                                text: d.service ? Theme.tr("service_running") : Theme.tr("service_stopped")
                            }
                            Chip {
                                big: true
                                kind: win.problems > 0 ? "setup" : "ok"
                                icon: "pulse"
                                text: Theme.tr("working_count").replace("{ok}", String(d.okCount)).replace("{total}", String(d.total))
                            }
                            Chip {
                                big: true
                                visible: !!(d.currentMode && d.currentMode !== "")
                                kind: d.currentMode === "performance" ? "setup" : (d.currentMode === "low-power" ? "ok" : "info")
                                icon: "zap"
                                text: Theme.tr("mode_now").replace("{mode}", win.modeName(d.currentMode))
                            }
                        }
                    }
                }

                // 2. Scenarios strip
                Card {
                    id: overviewScenariosCard
                    Layout.fillWidth: true
                    pad: 18
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10
                        Icon { name: "layers"; size: 17; color: Theme.accent }
                        Txt { Layout.fillWidth: true; Layout.minimumWidth: 0; elide: Text.ElideRight; text: Theme.tr("scenario"); font.pixelSize: 16; font.weight: Font.DemiBold }
                        Btn {
                            implicitHeight: 30
                            text: Theme.tr("open_profiles")
                            onClicked: win.page = "profiles"
                        }
                    }
                    Flow {
                        Layout.fillWidth: true
                        spacing: 8
                        Repeater {
                            model: scenariosModel
                            delegate: Rectangle {
                                id: scenPill
                                readonly property bool sel: model.id === d.scenario
                                readonly property bool isAuto: model.id === "auto"
                                height: 38
                                width: parent && parent.width > 0 ? Math.min(pillRow.implicitWidth + 28, Math.max(76, parent.width)) : pillRow.implicitWidth + 28
                                radius: 19
                                color: sel ? Theme.accent : (scenHover.hovered ? Theme.cardInner : Theme.btn)
                                border.width: 1
                                border.color: sel ? Theme.accent : (scenHover.hovered ? Theme.accent : Theme.border3)
                                Behavior on color { ColorAnimation { duration: 150 } }
                                HoverHandler { id: scenHover }
                                Row {
                                    id: pillRow
                                    anchors.centerIn: parent
                                    spacing: 6
                                    Icon {
                                        visible: scenPill.isAuto
                                        anchors.verticalCenter: parent.verticalCenter
                                        name: "zap"
                                        size: 14
                                        color: scenPill.sel ? "#0B1218" : Theme.accent
                                    }
                                    Txt {
                                        anchors.verticalCenter: parent.verticalCenter
                                        text: String(model.name || "")
                                        color: scenPill.sel ? "#0B1218" : Theme.soft
                                        font.pixelSize: 13
                                        font.weight: scenPill.sel ? Font.DemiBold : Font.Medium
                                    }
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

                // 3. Battery and live CPU/GPU telemetry
                GridLayout {
                    Layout.fillWidth: true
                    columns: width >= 660 ? 2 : 1
                    columnSpacing: 16
                    rowSpacing: 16

                    // Battery card
                    Card {
                        id: overviewBatCard
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8
                            Icon { name: "battery"; size: 17; color: Theme.batteryColor(d.battery.percent) }
                            Txt { Layout.fillWidth: true; text: Theme.tr("battery"); font.pixelSize: 16; font.weight: Font.DemiBold }
                            Chip {
                                kind: d.battery.status || "no"
                                icon: Theme.statusIcon(d.battery.status || "no")
                                text: d.battery.source || d.battery.statusText || Theme.tr("no_data")
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 12
                            Row {
                                spacing: 6
                                Txt {
                                    text: d.battery.percent !== undefined && d.battery.percent !== null ? String(d.battery.percent) : "—"
                                    color: Theme.batteryColor(d.battery.percent)
                                    font.family: Theme.mono
                                    font.pixelSize: 38
                                    font.weight: Font.DemiBold
                                }
                                Txt { text: "%"; color: Theme.muted; font.pixelSize: 16; anchors.baseline: parent.children[0].baseline }
                            }
                            Item { Layout.fillWidth: true }
                            ColumnLayout {
                                spacing: 2
                                Txt {
                                    Layout.alignment: Qt.AlignRight
                                    text: String(d.battery.text || "")
                                    font.pixelSize: 13
                                    color: Theme.soft
                                }
                                Txt {
                                    Layout.alignment: Qt.AlignRight
                                    visible: !!(d.battery.left && d.battery.left !== "") || !!(d.battery.power && d.battery.power !== "—")
                                    text: (d.battery.left && d.battery.left !== "")
                                          ? String(d.battery.left)
                                          : (String(d.battery.power || "—") + " " + Theme.tr("unit_w"))
                                    font.pixelSize: 12
                                    font.family: Theme.mono
                                    color: Theme.muted
                                }
                            }
                        }

                        Bar {
                            Layout.fillWidth: true
                            value: d.battery.percent || 0
                            fill: Theme.batteryColor(d.battery.percent)
                        }

                        // Compact 2-tile health + cycles strip
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Rectangle {
                                Layout.fillWidth: true
                                implicitHeight: ovHealthTile.implicitHeight + 18
                                radius: 11
                                color: Theme.cardInner
                                border.width: 1
                                border.color: Theme.border2
                                ColumnLayout {
                                    id: ovHealthTile
                                    anchors.fill: parent
                                    anchors.margins: 9
                                    spacing: 2
                                    Txt { text: Theme.tr("battery_health"); color: Theme.muted; font.pixelSize: 11; elide: Text.ElideRight; Layout.fillWidth: true }
                                    Txt { text: (d.battery.health || "—") + " %"; font.family: Theme.mono; font.pixelSize: 15; font.weight: Font.DemiBold }
                                }
                                Tip { text: Theme.tr("tip_bat_health") }
                            }
                            Rectangle {
                                Layout.fillWidth: true
                                implicitHeight: ovCyclesTile.implicitHeight + 18
                                radius: 11
                                color: Theme.cardInner
                                border.width: 1
                                border.color: Theme.border2
                                ColumnLayout {
                                    id: ovCyclesTile
                                    anchors.fill: parent
                                    anchors.margins: 9
                                    spacing: 2
                                    Txt { text: Theme.tr("battery_cycles"); color: Theme.muted; font.pixelSize: 11; elide: Text.ElideRight; Layout.fillWidth: true }
                                    Txt {
                                        text: d.battery.cycles !== undefined && d.battery.cycles !== null ? String(d.battery.cycles) : "—"
                                        font.family: Theme.mono
                                        font.pixelSize: 15
                                        font.weight: Font.DemiBold
                                    }
                                }
                                Tip { text: Theme.tr("tip_bat_cycles") }
                            }
                        }

                        Item { Layout.fillHeight: true }
                        Rectangle { Layout.fillWidth: true; height: 1; color: Theme.border }
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Item {
                                Layout.fillWidth: true
                                Layout.minimumWidth: 0
                                implicitHeight: ovLimitInner.implicitHeight
                                RowLayout {
                                    id: ovLimitInner
                                    anchors.fill: parent
                                    spacing: 6
                                    Txt { text: Theme.tr("charge_limit"); color: Theme.muted; font.pixelSize: 12; elide: Text.ElideRight; Layout.fillWidth: true }
                                    Chip {
                                        kind: d.limit.status || "no"
                                        icon: Theme.statusIcon(d.limit.status || "no")
                                        text: d.limit.statusText || Theme.tr("no_data")
                                    }
                                }
                                Tip { text: Theme.tr("tip_charge_limit") }
                            }
                            Btn {
                                implicitHeight: 32
                                text: Theme.tr("open_battery")
                                onClicked: win.page = "battery"
                            }
                        }
                    }

                    // CPU & GPU live card
                    Card {
                        id: overviewHardwareCard
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8
                            Icon { name: "cpu"; size: 17; color: Theme.accent }
                            Txt { Layout.fillWidth: true; text: Theme.tr("hw_card_title"); font.pixelSize: 16; font.weight: Font.DemiBold }
                            Chip {
                                id: overviewGpuChip
                                visible: !!(d.gpu && d.gpu.sleepText && d.gpu.sleepText !== "—")
                                kind: !!(d.gpu && d.gpu.asleep) ? "ok" : ((d.gpu && d.gpu.sleepText === Theme.tr("gpu_sleep_never")) ? "setup" : "info")
                                text: d.gpu ? "GPU: " + String(d.gpu.sleepText || "—") : ""
                                tip: d.gpu ? String(d.gpu.sleepTip || "") : ""
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10

                            // CPU telemetry tile
                            Rectangle {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                implicitHeight: ovCpuCol.implicitHeight + 22
                                radius: 12
                                color: Theme.cardInner
                                border.width: 1
                                border.color: Theme.border2
                                ColumnLayout {
                                    id: ovCpuCol
                                    anchors.fill: parent
                                    anchors.margins: 11
                                    spacing: 4
                                    RowLayout {
                                        Layout.fillWidth: true
                                        Txt { Layout.fillWidth: true; text: "CPU"; color: Theme.muted; font.pixelSize: 12; font.weight: Font.DemiBold }
                                        Txt {
                                            text: (d.cpu ? String(d.cpu.freq || "—") : "—") + " " + Theme.tr("unit_ghz")
                                            color: Theme.muted
                                            font.family: Theme.mono
                                            font.pixelSize: 11
                                        }
                                    }
                                    Row {
                                        spacing: 4
                                        Txt {
                                            text: d.cpu ? String(d.cpu.temp || "—") : "—"
                                            color: Theme.tempColor(d.cpu ? d.cpu.temp : "")
                                            font.family: Theme.mono
                                            font.pixelSize: 30
                                            font.weight: Font.DemiBold
                                        }
                                        Txt { text: "°C"; color: Theme.muted; anchors.baseline: parent.children[0].baseline }
                                    }
                                    Txt {
                                        text: (d.cpu && d.cpu.load !== null && d.cpu.load !== undefined) ? Theme.tr("load_pct").replace("{pct}", String(d.cpu.load)) : "—"
                                        color: Theme.soft
                                        font.pixelSize: 12
                                        font.family: Theme.mono
                                    }
                                    Spark {
                                        Layout.fillWidth: true
                                        implicitHeight: 28
                                        values: d.cpuHistory || []
                                        lineColor: Theme.tempColor(d.cpu ? d.cpu.temp : "")
                                    }
                                }
                                Tip { text: Theme.tr("tip_cpu_card") }
                            }

                            // GPU telemetry tile
                            Rectangle {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                implicitHeight: ovGpuCol.implicitHeight + 22
                                radius: 12
                                color: Theme.cardInner
                                border.width: 1
                                border.color: !!(d.gpu && d.gpu.asleep) ? Qt.rgba(0.298, 0.765, 0.541, 0.35) : Theme.border2
                                ColumnLayout {
                                    id: ovGpuCol
                                    anchors.fill: parent
                                    anchors.margins: 11
                                    spacing: 4
                                    RowLayout {
                                        Layout.fillWidth: true
                                        Txt { Layout.fillWidth: true; text: "GPU"; color: Theme.muted; font.pixelSize: 12; font.weight: Font.DemiBold }
                                        Txt {
                                            text: !!(d.gpu && d.gpu.asleep)
                                                  ? ("0 " + Theme.tr("unit_w"))
                                                  : ((d.gpu && d.gpu.power && d.gpu.power !== "—") ? (String(d.gpu.power) + " " + Theme.tr("unit_w")) : "—")
                                            color: !!(d.gpu && d.gpu.asleep) ? Theme.okText : Theme.muted
                                            font.family: Theme.mono
                                            font.pixelSize: 11
                                        }
                                    }
                                    Row {
                                        spacing: 4
                                        Txt {
                                            text: !!(d.gpu && d.gpu.asleep) ? Theme.tr("gpu_sleeping") : (d.gpu ? String(d.gpu.temp || "—") : "—")
                                            color: !!(d.gpu && d.gpu.asleep) ? Theme.okText : Theme.tempColor(d.gpu ? d.gpu.temp : "")
                                            font.family: Theme.mono
                                            font.pixelSize: !!(d.gpu && d.gpu.asleep) ? 24 : 30
                                            font.weight: Font.DemiBold
                                        }
                                        Txt {
                                            visible: !!(d.gpu && !d.gpu.asleep)
                                            text: "°C"; color: Theme.muted; anchors.baseline: parent.children[0].baseline
                                        }
                                    }
                                    Txt {
                                        Layout.fillWidth: true
                                        elide: Text.ElideRight
                                        text: !!(d.gpu && d.gpu.asleep)
                                              ? Theme.tr("gpu_sleeping_sub")
                                              : ((d.gpu && d.gpu.util !== null && d.gpu.util !== undefined)
                                                 ? Theme.tr("load_pct").replace("{pct}", String(d.gpu.util))
                                                 : "—")
                                        color: !!(d.gpu && d.gpu.asleep) ? Theme.okText : Theme.soft
                                        font.pixelSize: 12
                                        font.family: Theme.mono
                                    }
                                    Spark {
                                        Layout.fillWidth: true
                                        implicitHeight: 28
                                        opacity: !!(d.gpu && d.gpu.asleep) ? 0.35 : 1.0
                                        values: d.gpuHistory || []
                                        lineColor: !!(d.gpu && d.gpu.asleep) ? Theme.ok : Theme.tempColor(d.gpu ? d.gpu.temp : "")
                                    }
                                }
                                Tip { text: (d.gpu && d.gpu.sleepTip) ? String(d.gpu.sleepTip) : Theme.tr("tip_gpu_card") }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            visible: !!(d.gpu && d.gpu.holders && d.gpu.holders.length > 0)
                            Txt { Layout.fillWidth: true; text: Theme.tr("gpu_holders_label"); color: Theme.soft; font.pixelSize: 12 }
                            Txt { text: (d.gpu && d.gpu.holders) ? d.gpu.holders.join(", ") : ""; color: Theme.warn; font.pixelSize: 12; elide: Text.ElideRight }
                        }

                        Item { Layout.fillHeight: true }
                        Rectangle { Layout.fillWidth: true; height: 1; color: Theme.border }
                        Btn {
                            Layout.fillWidth: true
                            implicitHeight: 34
                            text: Theme.tr("open_performance")
                            onClicked: win.page = "performance"
                        }
                    }
                }

                // 4. Quick toggles
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 10
                    Txt { text: Theme.tr("quick_toggles"); font.pixelSize: 16; font.weight: Font.DemiBold }
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

                // 5. Quick controls strip (brightness + refresh rate + keyboard RGB shortcut)
                Card {
                    id: overviewDisplayCard
                    Layout.fillWidth: true
                    pad: 16
                    readonly property bool hasBright: !!(d.display && d.display.brightness !== null && d.display.brightness !== undefined)
                    readonly property bool hasRates: !!(d.display && d.display.rates && d.display.rates.length > 0)
                    readonly property bool hasKbd: !!(d.kbdBacklight && d.kbdBacklight.available === true)
                    visible: hasBright || hasRates || hasKbd

                    GridLayout {
                        visible: overviewDisplayCard.hasBright || overviewDisplayCard.hasRates
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
                                Txt { Layout.fillWidth: true; text: Theme.tr("screen_brightness"); font.pixelSize: 13; color: Theme.soft }
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
                                Txt { Layout.fillWidth: true; text: Theme.tr("screen_refresh"); font.pixelSize: 13; color: Theme.soft }
                                Txt {
                                    text: (d.display && d.display.refresh) ? String(d.display.refresh) + " " + Theme.tr("unit_hz") : "—"
                                    font.family: Theme.mono
                                    font.pixelSize: 13
                                }
                            }
                            SegmentBar {
                                id: overviewRatesBar
                                options: (d.display && d.display.rates ? d.display.rates : []).map(function (r) {
                                    return { id: String(r), label: String(r) + " " + Theme.tr("unit_hz"), tip: Theme.tr("refresh_tip") }
                                })
                                current: (d.display && d.display.refresh) ? String(d.display.refresh) : ""
                                onPicked: function (val) { backend.setRefresh(Number(val)) }
                            }
                        }
                    }

                    Rectangle {
                        visible: overviewDisplayCard.hasKbd && (overviewDisplayCard.hasBright || overviewDisplayCard.hasRates)
                        Layout.fillWidth: true
                        height: 1
                        color: Theme.border
                    }

                    // Compact keyboard backlight shortcut strip
                    RowLayout {
                        id: overviewKbdRow
                        visible: overviewDisplayCard.hasKbd
                        Layout.fillWidth: true
                        spacing: 10
                        readonly property var kb: d.kbdBacklight || ({})
                        readonly property bool kbOn: !!(kb && kb.on === true)
                        readonly property bool kbAuto: !!(kb && kb.autonomous === true)
                        readonly property bool kbRgb: !!(kb && kb.rgb === true)
                        readonly property bool kbCan: !!(kb && kb.can === true)
                        readonly property int kbBright: kb && kb.brightness !== undefined ? Number(kb.brightness) : 100
                        readonly property string kbColor: kb && kb.color ? String(kb.color) : "#5AB0FF"

                        Rectangle {
                            implicitWidth: 26
                            implicitHeight: 26
                            radius: 8
                            color: overviewKbdRow.kbAuto ? Theme.btn : (overviewKbdRow.kbOn ? (overviewKbdRow.kbRgb ? overviewKbdRow.kbColor : Theme.accent) : Theme.cardInner)
                            border.width: 1
                            border.color: overviewKbdRow.kbOn && !overviewKbdRow.kbAuto ? "#FFFFFF" : Theme.border3
                            Icon {
                                anchors.centerIn: parent
                                name: "keyboard"
                                size: 14
                                color: overviewKbdRow.kbOn && !overviewKbdRow.kbAuto ? "#0B1218" : Theme.muted
                            }
                        }
                        ColumnLayout {
                            Layout.fillWidth: true
                            Layout.minimumWidth: 0
                            spacing: 1
                            Txt { Layout.fillWidth: true; elide: Text.ElideRight; text: Theme.tr("kbd_backlight"); font.pixelSize: 13; font.weight: Font.Medium }
                            Txt {
                                Layout.fillWidth: true
                                elide: Text.ElideRight
                                font.pixelSize: 11
                                font.family: Theme.mono
                                color: Theme.muted
                                text: overviewKbdRow.kbAuto
                                      ? Theme.tr("kbd_auto_chip")
                                      : (!overviewKbdRow.kbOn
                                         ? Theme.tr("kbd_off")
                                         : (overviewKbdRow.kbRgb ? (overviewKbdRow.kbColor + " · " + overviewKbdRow.kbBright + " %") : (overviewKbdRow.kbBright + " %")))
                            }
                        }
                        Btn {
                            visible: !overviewKbdRow.kbAuto
                            enabled: overviewKbdRow.kbCan
                            implicitHeight: 32
                            primary: overviewKbdRow.kbOn
                            text: overviewKbdRow.kbOn ? Theme.tr("kbd_on") : Theme.tr("kbd_off")
                            onClicked: {
                                var nextOn = !overviewKbdRow.kbOn
                                var nextBright = nextOn ? (overviewKbdRow.kbBright > 0 ? overviewKbdRow.kbBright : 100) : overviewKbdRow.kbBright
                                backend.setKbdBacklight(nextOn, nextBright, overviewKbdRow.kbColor, false)
                            }
                        }
                        Btn {
                            implicitHeight: 32
                            text: Theme.tr("open_kbd_color")
                            onClicked: win.page = "peripherals"
                        }
                    }
                }

                // 6. Compact 2-column footer: Journal + System Health
                GridLayout {
                    Layout.fillWidth: true
                    columns: width >= 680 ? 2 : 1
                    columnSpacing: 16
                    rowSpacing: 16

                    Card {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        pad: 18
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8
                            Icon { name: "clock"; size: 16; color: Theme.accent }
                            Txt { Layout.fillWidth: true; text: Theme.tr("journal_title"); font.pixelSize: 15; font.weight: Font.DemiBold }
                            Btn {
                                visible: journalModel.count > 3
                                implicitHeight: 28
                                text: win.journalExpanded ? Theme.tr("journal_collapse") : Theme.tr("journal_all").replace("{n}", String(journalModel.count))
                                onClicked: win.journalExpanded = !win.journalExpanded
                            }
                        }
                        Txt {
                            visible: journalModel.count === 0
                            Layout.fillWidth: true
                            wrapMode: Text.WordWrap
                            color: Theme.muted
                            font.pixelSize: 12
                            text: Theme.tr("journal_empty")
                        }
                        Repeater {
                            model: journalModel
                            delegate: RowLayout {
                                visible: win.journalExpanded || index < 3
                                Layout.fillWidth: true
                                spacing: 10
                                Txt { text: model.time; color: Theme.muted; font.family: Theme.mono; font.pixelSize: 12 }
                                Txt { Layout.fillWidth: true; text: model.text; wrapMode: Text.WordWrap; font.pixelSize: 12 }
                            }
                        }
                        Item { Layout.fillHeight: true }
                    }

                    Card {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        pad: 18
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8
                            Icon { name: "pulse"; size: 16; color: win.problems > 0 ? Theme.warn : Theme.okText }
                            Txt { Layout.fillWidth: true; text: Theme.tr("nav_diagnostics"); font.pixelSize: 15; font.weight: Font.DemiBold }
                            Chip {
                                kind: win.problems > 0 ? "setup" : "ok"
                                text: win.problems > 0 ? Theme.tr("problems_count_chip").replace("{n}", String(win.problems)) : Theme.tr("problems_none_chip")
                            }
                        }
                        Txt {
                            Layout.fillWidth: true
                            Layout.minimumWidth: 0
                            wrapMode: Text.WordWrap
                            color: Theme.muted
                            font.pixelSize: 12
                            text: win.problems > 0 ? Theme.tr("problems_some_text") : Theme.tr("problems_none_text")
                        }
                        Item { Layout.fillHeight: true }
                        Btn {
                            Layout.fillWidth: true
                            implicitHeight: 34
                            text: Theme.tr("open_diagnostics")
                            onClicked: win.page = "diagnostics"
                        }
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
