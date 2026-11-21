import QtQuick
import QtQuick.Layouts
import QtQuick.Controls

Flickable {
    id: page
    property var d: ({})
    property string selId: ""
    property string tab: "settings"   // "settings" | "rules"
    property bool showRunning: false
    property bool procsExpanded: false
    property bool dirty: false

    readonly property var curEdit: cur ? cur.edit : ({ power: "keep", camera: "keep", output: "", input: "", brightness: 0, refresh: 0 })
    readonly property var curRule: cur ? cur.rule : ({ processes: [], when: "", idle: 0, temp: 0, hours: "" })
    readonly property var list: d.profiles ? d.profiles : []
    readonly property var cur: {
        for (var i = 0; i < list.length; i++)
            if (list[i].id === selId) return list[i]
        return list.length > 0 ? list[0] : null
    }
    readonly property string curId: cur ? String(cur.id) : ""
    readonly property int sidePad: page.width < 560 ? 16 : 32

    SyncModel { id: profilesModel }
    SyncModel { id: ruleProcsModel }
    SyncModel { id: appsModel }

    function modeLabel(id) {
        var modes = page.d.modes ? page.d.modes : []
        for (var i = 0; i < modes.length; i++)
            if (modes[i].id === id) return String(modes[i].name)
        return String(id || "")
    }
    function modeOptions() {
        var modes = page.d.modes ? page.d.modes : []
        return modes.map(function (m) { return { id: String(m.id), label: String(m.name), tip: String(m.hint || "") } })
    }
    function rateOptions() {
        var rates = page.d.display && page.d.display.rates ? page.d.display.rates : []
        return rates.map(function (r) { return { id: String(r), label: String(r) + " " + Theme.tr("unit_hz"), tip: Theme.tr("refresh_tip") } })
    }
    function audioItems(listArr, currentVal) {
        var arr = listArr ? listArr : []
        var res = arr.map(function (t) { return { id: String(t), label: String(t) } })
        if (currentVal && !anyMatch(arr, currentVal))
            res.unshift({ id: String(currentVal), label: String(currentVal) + Theme.tr("unplugged_tag") })
        return res
    }
    function matchedAudioId(listArr, query) {
        if (!query) return ""
        var arr = listArr ? listArr : []
        for (var i = 0; i < arr.length; i++)
            if (matches(arr[i], query)) return String(arr[i])
        return String(query)
    }
    function fallbackItems() {
        var res = [{ id: "keep", label: Theme.tr("fallback_keep") }]
        for (var i = 0; i < page.list.length; i++)
            res.push({ id: String(page.list[i].id), label: String(page.list[i].name) })
        return res
    }

    function syncAll() {
        var profs = page.list.map(function (p) {
            return { id: String(p.id), name: String(p.name), sub: String(p.sub || ""), summary: String(p.summary || "") }
        })
        profilesModel.sync(profs)
        var procs = page.curRule && page.curRule.processes ? page.curRule.processes : []
        ruleProcsModel.sync(procs.map(function (p) { return { name: String(p) } }))
        var apps = (page.d.apps ? page.d.apps : []).filter(function (a) { return procs.indexOf(a) < 0 })
        appsModel.sync(apps.map(function (a) { return { name: String(a) } }))
    }

    onCurIdChanged: {
        procsExpanded = false
        showRunning = false
        dirty = false
        syncAll()
        if (hoursField && !hoursField.activeFocus)
            hoursField.text = page.curRule ? String(page.curRule.hours || "") : ""
    }
    Connections {
        target: backend
        function onProfileCreated(pid) { page.selId = pid; page.tab = "settings" }
        function onStateChanged() {
            page.syncAll()
            if (hoursField && !hoursField.activeFocus)
                hoursField.text = page.curRule ? String(page.curRule.hours || "") : ""
        }
    }
    Component.onCompleted: {
        syncAll()
        if (hoursField)
            hoursField.text = page.curRule ? String(page.curRule.hours || "") : ""
    }

    function matches(name, query) {
        return query !== "" && String(name).toLowerCase().indexOf(String(query).toLowerCase()) >= 0
    }
    function anyMatch(names, query) {
        for (var i = 0; i < names.length; i++)
            if (matches(names[i], query)) return true
        return false
    }
    function save(field, value) {
        if (!cur) return
        var e = cur.edit
        var v = { power: e.power, camera: e.camera, output: e.output, input: e.input,
                  brightness: e.brightness, refresh: e.refresh }
        v[field] = value
        if (page.d.scenario === cur.id)
            page.dirty = true
        backend.saveProfile(cur.id, v.power, v.camera, v.output, v.input, v.brightness, v.refresh)
    }
    function saveRule(procs, when, idle, temp, hours) {
        if (!cur) return
        backend.saveRule(cur.id, procs.join(","), when, idle,
                         temp === undefined ? cur.rule.temp : temp,
                         hours === undefined ? cur.rule.hours : hours)
    }
    function addProgram(name) {
        if (!cur) return
        var n = String(name).trim()
        if (n === "" || cur.rule.processes.indexOf(n) >= 0) return
        saveRule(cur.rule.processes.concat([n]), cur.rule.when, cur.rule.idle)
    }
    function removeProgram(name) {
        if (!cur) return
        saveRule(cur.rule.processes.filter(function (x) { return x !== name }), cur.rule.when, cur.rule.idle)
    }

    clip: true
    contentWidth: width
    contentHeight: content.implicitHeight + 68
    boundsBehavior: Flickable.StopAtBounds
    ScrollBar.vertical: ScrollBar {}

    ColumnLayout {
        id: content
        width: Math.min(Math.max(200, page.width - page.sidePad * 2), 1020)
        x: Math.max(page.sidePad, (page.width - width) / 2)
        y: 28
        spacing: 20

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 4
            Txt { Layout.fillWidth: true; wrapMode: Text.WordWrap; text: Theme.tr("prof_title"); font.pixelSize: page.width < 560 ? 22 : 28; font.weight: Font.DemiBold }
            Txt { Layout.fillWidth: true; wrapMode: Text.WordWrap; text: Theme.tr("prof_sub"); color: Theme.muted }
        }

        GridLayout {
            Layout.fillWidth: true
            columns: page.width >= 820 ? 2 : 1
            columnSpacing: 16
            rowSpacing: 16

            // ----- profile list -----
            Card {
                id: listCard
                Layout.preferredWidth: page.width >= 820 ? 284 : -1
                Layout.fillWidth: page.width < 820
                Layout.minimumWidth: 0
                Layout.alignment: Qt.AlignTop
                Txt { text: Theme.tr("your_profiles"); font.pixelSize: 16; font.weight: Font.DemiBold }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    TextField {
                        id: newName
                        Layout.fillWidth: true
                        Layout.minimumWidth: 0
                        implicitHeight: 38
                        placeholderText: Theme.tr("new_profile_ph")
                        placeholderTextColor: Theme.muted
                        color: Theme.text
                        font.family: Theme.sans
                        font.pixelSize: 13
                        leftPadding: 12
                        maximumLength: 30
                        ToolTip.text: Theme.tr("new_profile_tip")
                        ToolTip.visible: hovered
                        ToolTip.delay: 450
                        background: Rectangle {
                            radius: 10
                            color: Theme.cardInner
                            border.width: 1
                            border.color: newName.activeFocus ? Theme.accent : Theme.border2
                        }
                        onAccepted: { backend.createProfile(text); text = "" }
                    }
                    Btn {
                        text: "+"
                        primary: true
                        implicitHeight: 38
                        implicitWidth: 42
                        tip: Theme.tr("create_profile_tip")
                        onClicked: { backend.createProfile(newName.text); newName.text = "" }
                    }
                }

                Repeater {
                    model: profilesModel
                    delegate: Rectangle {
                        id: profCard
                        readonly property bool sel: page.cur !== null && model.id === page.cur.id
                        Layout.fillWidth: true
                        implicitHeight: 68
                        radius: 12
                        color: sel ? "#1B2938" : Theme.cardInner
                        border.width: 1
                        border.color: sel ? Theme.accent : Theme.border2
                        Behavior on color { ColorAnimation { duration: 150 } }
                        Behavior on border.color { ColorAnimation { duration: 150 } }

                        Rectangle {
                            visible: profCard.sel
                            width: 3
                            height: parent.height - 20
                            radius: 2
                            anchors.left: parent.left
                            anchors.leftMargin: 4
                            anchors.verticalCenter: parent.verticalCenter
                            color: Theme.accent
                        }

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 14
                            anchors.rightMargin: 12
                            spacing: 8
                            ColumnLayout {
                                Layout.fillWidth: true
                                Layout.minimumWidth: 0
                                spacing: 2
                                Txt {
                                    Layout.fillWidth: true
                                    elide: Text.ElideRight
                                    text: model.name
                                    font.pixelSize: 15
                                    font.weight: Font.DemiBold
                                    color: profCard.sel ? "#FFFFFF" : Theme.text
                                }
                                Txt {
                                    Layout.fillWidth: true
                                    elide: Text.ElideRight
                                    text: model.summary !== "" ? model.summary : model.sub
                                    font.pixelSize: 12
                                    color: profCard.sel ? Theme.accent : Theme.muted
                                }
                            }
                            Chip {
                                visible: page.d.scenario === model.id
                                kind: "ok"
                                text: Theme.tr("active")
                            }
                        }
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: page.selId = model.id
                        }
                    }
                }
            }

            // ----- selected profile editor -----
            ColumnLayout {
                Layout.fillWidth: true
                Layout.minimumWidth: 0
                Layout.alignment: Qt.AlignTop
                spacing: 16
                visible: page.cur !== null

                Card {
                    id: editorHeaderCard
                    Layout.fillWidth: true

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 12
                        ColumnLayout {
                            Layout.fillWidth: true
                            Layout.minimumWidth: 0
                            spacing: 2
                            Txt {
                                Layout.fillWidth: true
                                wrapMode: Text.WordWrap
                                text: page.cur ? String(page.cur.name) : ""
                                font.pixelSize: 20
                                font.weight: Font.DemiBold
                            }
                            Txt {
                                Layout.fillWidth: true
                                wrapMode: Text.WordWrap
                                text: page.cur ? String(page.cur.summary || page.cur.sub || "") : ""
                                color: Theme.muted
                                font.pixelSize: 13
                            }
                        }
                    }

                    Flow {
                        Layout.fillWidth: true
                        spacing: 8
                        Chip {
                            visible: !!(page.cur !== null && page.d.scenario === page.cur.id)
                            kind: page.dirty ? "setup" : "ok"
                            icon: page.dirty ? "wrench" : "check"
                            text: page.dirty ? Theme.tr("dirty_chip") : Theme.tr("applied_chip")
                        }
                        Btn {
                            visible: page.cur !== null
                            primary: !!(page.cur !== null && (page.d.scenario !== page.cur.id || page.dirty))
                            implicitHeight: 36
                            text: (page.cur !== null && page.d.scenario === page.cur.id)
                                  ? (page.dirty ? Theme.tr("apply_changes") : Theme.tr("apply_again"))
                                  : Theme.tr("apply_now")
                            onClicked: {
                                page.dirty = false
                                backend.setScenario(page.cur.id)
                            }
                        }
                        Btn {
                            visible: !!(page.cur !== null && page.cur.custom === true)
                            implicitHeight: 36
                            text: Theme.tr("delete")
                            tip: Theme.tr("delete_tip")
                            onClicked: backend.deleteProfile(page.cur.id)
                        }
                    }

                    SegmentBar {
                        id: tabBar
                        current: page.tab
                        options: [
                            { id: "settings", label: Theme.tr("tab_settings") + (page.cur && page.cur.settingsCount ? " (" + page.cur.settingsCount + ")" : ""), tip: Theme.tr("tab_settings_tip") },
                            { id: "rules", label: Theme.tr("tab_rules") + (page.cur && page.cur.rulesCount ? " (" + page.cur.rulesCount + ")" : ""), tip: Theme.tr("tab_rules_tip") }
                        ]
                        onPicked: function (val) { page.tab = val }
                    }
                }

                // ========== TAB 1: SETTINGS ==========
                Card {
                    id: settingsTabCard
                    Layout.fillWidth: true
                    visible: page.tab === "settings"

                    SettingRow {
                        id: powerRow
                        icon: "gauge"
                        title: Theme.tr("power_mode")
                        checked: page.curEdit.power !== "keep"
                        valueText: page.modeLabel(page.curEdit.power)
                        tip: Theme.tr("prof_power_tip")
                        onToggled: function (on) { page.save("power", on ? "balanced" : "keep") }
                        SegmentBar {
                            options: page.modeOptions()
                            current: String(page.curEdit.power || "")
                            onPicked: function (val) { page.save("power", val) }
                        }
                    }

                    SettingRow {
                        id: cameraRow
                        icon: "camera"
                        title: Theme.tr("toggle_camera")
                        checked: page.curEdit.camera !== "keep"
                        valueText: page.curEdit.camera === "on" ? Theme.tr("turn_on") : Theme.tr("turn_off")
                        tip: Theme.tr("prof_cam_tip")
                        onToggled: function (on) { page.save("camera", on ? "off" : "keep") }
                        SegmentBar {
                            options: [
                                { id: "on", label: Theme.tr("turn_on"), tip: "" },
                                { id: "off", label: Theme.tr("turn_off"), tip: "" }
                            ]
                            current: String(page.curEdit.camera || "")
                            onPicked: function (val) { page.save("camera", val) }
                        }
                    }

                    SettingRow {
                        id: brightnessRow
                        icon: "sun"
                        title: Theme.tr("screen_brightness")
                        checked: Number(page.curEdit.brightness || 0) > 0
                        valueText: profBrightSlider.displayValue + " %"
                        tip: Theme.tr("prof_bright_tip")
                        onToggled: function (on) {
                            var defVal = (page.d.display && page.d.display.brightness) ? Number(page.d.display.brightness) : 60
                            page.save("brightness", on ? Math.max(5, Math.min(100, defVal)) : 0)
                        }
                        SmoothSlider {
                            id: profBrightSlider
                            from: 5
                            to: 100
                            targetValue: Number(page.curEdit.brightness || 60)
                            onCommitted: function (val) {
                                if (page.cur)
                                    page.save("brightness", val)
                            }
                        }
                        SegmentBar {
                            options: [
                                { id: "25", label: "25 %", tip: "" },
                                { id: "50", label: "50 %", tip: "" },
                                { id: "75", label: "75 %", tip: "" },
                                { id: "100", label: "100 %", tip: "" }
                            ]
                            current: String(page.curEdit.brightness || "")
                            onPicked: function (val) { page.save("brightness", Number(val)) }
                        }
                    }

                    SettingRow {
                        id: refreshRow
                        icon: "monitor"
                        title: Theme.tr("screen_refresh")
                        checked: Number(page.curEdit.refresh || 0) > 0
                        valueText: Number(page.curEdit.refresh || 0) + " " + Theme.tr("unit_hz")
                        tip: Theme.tr("refresh_tip")
                        onToggled: function (on) {
                            var rates = page.d.display && page.d.display.rates ? page.d.display.rates : []
                            page.save("refresh", on ? (rates.length > 0 ? Number(rates[0]) : 60) : 0)
                        }
                        SegmentBar {
                            visible: !!(page.d.display && page.d.display.rates && page.d.display.rates.length > 0)
                            options: page.rateOptions()
                            current: String(page.curEdit.refresh || "")
                            onPicked: function (val) { page.save("refresh", Number(val)) }
                        }
                        Txt {
                            visible: !!(!page.d.display || !page.d.display.rates || page.d.display.rates.length === 0)
                            Layout.fillWidth: true
                            wrapMode: Text.WordWrap
                            text: Theme.tr("prof_rates_missing")
                            color: Theme.muted
                            font.pixelSize: 12
                        }
                    }

                    SettingRow {
                        id: outputRow
                        icon: "speaker"
                        title: Theme.tr("sound_output")
                        checked: String(page.curEdit.output || "") !== ""
                        valueText: String(page.curEdit.output || "")
                        tip: Theme.tr("prof_out_tip")
                        onToggled: function (on) {
                            if (!on) { page.save("output", ""); return }
                            var outs = page.d.audio && page.d.audio.outputs ? page.d.audio.outputs : []
                            var defOut = page.d.audio && page.d.audio.outputDefault ? String(page.d.audio.outputDefault) : (outs.length > 0 ? String(outs[0]) : "")
                            if (defOut !== "")
                                page.save("output", defOut)
                            else
                                backend.say(Theme.tr("sound_output_none"))
                        }
                        SelectBox {
                            id: outputSelect
                            items: page.audioItems(page.d.audio ? page.d.audio.outputs : [], page.curEdit.output)
                            currentId: page.matchedAudioId(page.d.audio ? page.d.audio.outputs : [], page.curEdit.output)
                            placeholder: Theme.tr("prof_out_ph")
                            onPicked: function (val) { page.save("output", val) }
                        }
                        Txt {
                            visible: !!(page.curEdit.output !== "" && !page.anyMatch(page.d.audio ? page.d.audio.outputs : [], page.curEdit.output))
                            Layout.fillWidth: true
                            wrapMode: Text.WordWrap
                            text: Theme.tr("prof_out_unplugged")
                            color: Theme.warn
                            font.pixelSize: 12
                        }
                    }

                    SettingRow {
                        id: inputRow
                        icon: "mic"
                        title: Theme.tr("microphone")
                        checked: String(page.curEdit.input || "") !== ""
                        valueText: String(page.curEdit.input || "")
                        tip: Theme.tr("prof_in_tip")
                        onToggled: function (on) {
                            if (!on) { page.save("input", ""); return }
                            var ins = page.d.audio && page.d.audio.inputs ? page.d.audio.inputs : []
                            var defIn = page.d.audio && page.d.audio.inputDefault ? String(page.d.audio.inputDefault) : (ins.length > 0 ? String(ins[0]) : "")
                            if (defIn !== "")
                                page.save("input", defIn)
                            else
                                backend.say(Theme.tr("mic_none"))
                        }
                        SelectBox {
                            id: inputSelect
                            items: page.audioItems(page.d.audio ? page.d.audio.inputs : [], page.curEdit.input)
                            currentId: page.matchedAudioId(page.d.audio ? page.d.audio.inputs : [], page.curEdit.input)
                            placeholder: Theme.tr("prof_in_ph")
                            onPicked: function (val) { page.save("input", val) }
                        }
                        Txt {
                            visible: !!(page.curEdit.input !== "" && !page.anyMatch(page.d.audio ? page.d.audio.inputs : [], page.curEdit.input))
                            Layout.fillWidth: true
                            wrapMode: Text.WordWrap
                            text: Theme.tr("prof_in_unplugged")
                            color: Theme.warn
                            font.pixelSize: 12
                        }
                    }
                }

                // ========== TAB 2: AUTO RULES ==========
                Card {
                    id: rulesTabCard
                    Layout.fillWidth: true
                    visible: page.tab === "rules"

                    Txt {
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                        text: Theme.tr("rules_intro")
                        color: Theme.muted
                        font.pixelSize: 12
                    }

                    SettingRow {
                        id: ruleAppsRow
                        icon: "app"
                        title: Theme.tr("rule_app_title")
                        offText: Theme.tr("doesnt_matter")
                        checked: page.curRule.processes.length > 0 || page.procsExpanded
                        valueText: page.curRule.processes.length > 0 ? page.curRule.processes.join(", ") : Theme.tr("rule_app_empty")
                        tip: Theme.tr("rule_app_tip")
                        onToggled: function (on) {
                            if (on) {
                                page.procsExpanded = true
                            } else {
                                page.procsExpanded = false
                                page.showRunning = false
                                if (page.curRule.processes.length > 0)
                                    page.saveRule([], page.curRule.when, page.curRule.idle)
                            }
                        }
                        Flow {
                            Layout.fillWidth: true
                            spacing: 6
                            visible: ruleProcsModel.count > 0
                            Repeater {
                                model: ruleProcsModel
                                delegate: Pill {
                                    implicitHeight: 32
                                    text: model.name + "  ✕"
                                    tip: (backend ? backend.describeProgram(model.name) : "") + "\n" + Theme.tr("click_remove")
                                    sel: true
                                    onClicked: page.removeProgram(model.name)
                                }
                            }
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8
                            TextField {
                                id: nameField
                                Layout.fillWidth: true
                                Layout.minimumWidth: 0
                                implicitHeight: 38
                                ToolTip.text: Theme.tr("rule_app_input_tip")
                                ToolTip.visible: hovered
                                ToolTip.delay: 450
                                placeholderText: Theme.tr("rule_app_ph")
                                placeholderTextColor: Theme.muted
                                color: Theme.text
                                font.family: Theme.sans
                                font.pixelSize: 13
                                leftPadding: 12
                                selectByMouse: true
                                background: Rectangle {
                                    radius: 10
                                    color: Theme.panel
                                    border.width: 1
                                    border.color: nameField.activeFocus ? Theme.accent : Theme.border2
                                }
                                onAccepted: { page.addProgram(text); text = "" }
                            }
                            Btn {
                                text: Theme.tr("add")
                                implicitHeight: 38
                                onClicked: { page.addProgram(nameField.text); nameField.text = "" }
                            }
                        }
                        Pill {
                            implicitHeight: 30
                            text: page.showRunning ? Theme.tr("hide_running") : Theme.tr("pick_running")
                            tip: Theme.tr("pick_running_tip")
                            onClicked: page.showRunning = !page.showRunning
                        }
                        Flow {
                            Layout.fillWidth: true
                            spacing: 6
                            visible: page.showRunning
                            Repeater {
                                id: suggestions
                                model: appsModel
                                delegate: Pill {
                                    implicitHeight: 30
                                    text: model.name
                                    tip: (backend ? backend.describeProgram(model.name) : "") + "\n" + Theme.tr("click_add")
                                    onClicked: page.addProgram(model.name)
                                }
                            }
                        }
                    }

                    SettingRow {
                        id: rulePowerRow
                        icon: "battery"
                        title: Theme.tr("rule_power_title")
                        offText: Theme.tr("doesnt_matter")
                        checked: String(page.curRule.when || "") !== ""
                        valueText: page.curRule.when === "battery" ? Theme.tr("rule_battery") : Theme.tr("rule_ac")
                        tip: Theme.tr("rule_power_tip")
                        onToggled: function (on) {
                            page.saveRule(page.curRule.processes, on ? "battery" : "", page.curRule.idle)
                        }
                        SegmentBar {
                            options: [
                                { id: "battery", label: Theme.tr("rule_battery"), tip: Theme.tr("rule_battery_tip") },
                                { id: "ac", label: Theme.tr("rule_ac"), tip: Theme.tr("rule_ac_tip") }
                            ]
                            current: String(page.curRule.when || "")
                            onPicked: function (val) { page.saveRule(page.curRule.processes, val, page.curRule.idle) }
                        }
                    }

                    SettingRow {
                        id: ruleIdleRow
                        icon: "clock"
                        title: Theme.tr("rule_idle_title")
                        offText: Theme.tr("doesnt_matter")
                        checked: Number(page.curRule.idle || 0) > 0
                        valueText: Theme.tr("rule_idle_val").replace("{m}", String(Number(page.curRule.idle || 0)))
                        tip: Theme.tr("rule_idle_tip")
                        onToggled: function (on) {
                            page.saveRule(page.curRule.processes, page.curRule.when, on ? 10 : 0)
                        }
                        SegmentBar {
                            options: [
                                { id: "5", label: "5 " + Theme.tr("unit_min"), tip: "" },
                                { id: "10", label: "10 " + Theme.tr("unit_min"), tip: "" },
                                { id: "15", label: "15 " + Theme.tr("unit_min"), tip: "" },
                                { id: "30", label: "30 " + Theme.tr("unit_min"), tip: "" },
                                { id: "60", label: "60 " + Theme.tr("unit_min"), tip: "" }
                            ]
                            current: String(page.curRule.idle || "")
                            onPicked: function (val) { page.saveRule(page.curRule.processes, page.curRule.when, Number(val)) }
                        }
                        Txt {
                            visible: !page.d.idleAvailable
                            Layout.fillWidth: true
                            wrapMode: Text.WordWrap
                            text: Theme.tr("swayidle_missing")
                            color: Theme.warn
                            font.pixelSize: 12
                        }
                    }

                    SettingRow {
                        id: ruleTempRow
                        icon: "flame"
                        title: Theme.tr("rule_temp_title")
                        offText: Theme.tr("doesnt_matter")
                        checked: Number(page.curRule.temp || 0) > 0
                        valueText: Theme.tr("rule_temp_val").replace("{t}", String(Number(page.curRule.temp || 0)))
                        tip: Theme.tr("rule_temp_tip")
                        onToggled: function (on) {
                            page.saveRule(page.curRule.processes, page.curRule.when, page.curRule.idle, on ? 90 : 0)
                        }
                        SegmentBar {
                            options: [
                                { id: "80", label: "80 °C", tip: "" },
                                { id: "85", label: "85 °C", tip: "" },
                                { id: "90", label: "90 °C", tip: "" },
                                { id: "95", label: "95 °C", tip: "" }
                            ]
                            current: String(page.curRule.temp || "")
                            onPicked: function (val) { page.saveRule(page.curRule.processes, page.curRule.when, page.curRule.idle, Number(val)) }
                        }
                    }

                    SettingRow {
                        id: ruleHoursRow
                        icon: "sun"
                        title: Theme.tr("rule_hours_title")
                        offText: Theme.tr("doesnt_matter")
                        checked: String(page.curRule.hours || "") !== ""
                        valueText: String(page.curRule.hours || "").replace("-", " – ")
                        tip: Theme.tr("rule_hours_tip")
                        onToggled: function (on) {
                            page.saveRule(page.curRule.processes, page.curRule.when, page.curRule.idle, undefined, on ? "22:00-07:00" : "")
                        }
                        SegmentBar {
                            options: [
                                { id: "22:00-07:00", label: "22:00 – 07:00", tip: Theme.tr("night_word") },
                                { id: "09:00-18:00", label: "09:00 – 18:00", tip: Theme.tr("day_word") },
                                { id: "18:00-23:00", label: "18:00 – 23:00", tip: Theme.tr("evening_word") }
                            ]
                            current: String(page.curRule.hours || "")
                            onPicked: function (val) { page.saveRule(page.curRule.processes, page.curRule.when, page.curRule.idle, undefined, val) }
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8
                            TextField {
                                id: hoursField
                                readonly property bool validInput: text.trim() === "" || /^([01][0-9]|2[0-3]):[0-5][0-9]-([01][0-9]|2[0-3]):[0-5][0-9]$/.test(text.trim())
                                Layout.fillWidth: true
                                Layout.maximumWidth: 200
                                Layout.minimumWidth: 0
                                implicitHeight: 38
                                placeholderText: Theme.tr("hours_ph")
                                placeholderTextColor: Theme.muted
                                color: Theme.text
                                font.family: Theme.mono
                                font.pixelSize: 13
                                leftPadding: 12
                                ToolTip.text: Theme.tr("hours_tip")
                                ToolTip.visible: hovered
                                ToolTip.delay: 450
                                background: Rectangle {
                                    radius: 10
                                    color: Theme.panel
                                    border.width: 1
                                    border.color: !hoursField.validInput ? Theme.err : (hoursField.activeFocus ? Theme.accent : Theme.border2)
                                }
                                onActiveFocusChanged: {
                                    if (!activeFocus && !validInput)
                                        text = page.curRule ? String(page.curRule.hours || "") : ""
                                }
                                onAccepted: page.saveRule(page.curRule.processes, page.curRule.when, page.curRule.idle, undefined, text.trim())
                            }
                            Btn {
                                text: Theme.tr("apply")
                                implicitHeight: 38
                                onClicked: page.saveRule(page.curRule.processes, page.curRule.when, page.curRule.idle, undefined, hoursField.text.trim())
                            }
                        }
                    }
                }

                Card {
                    id: fallbackCard
                    Layout.fillWidth: true
                    visible: page.tab === "rules"
                    Txt { text: Theme.tr("fallback_title"); font.pixelSize: 15; font.weight: Font.DemiBold }
                    Txt {
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                        text: Theme.tr("fallback_desc")
                        color: Theme.muted
                        font.pixelSize: 12
                    }
                    SelectBox {
                        id: fallbackSelect
                        items: page.fallbackItems()
                        currentId: page.d.fallback ? String(page.d.fallback) : "keep"
                        onPicked: function (val) { backend.saveFallback(val) }
                    }
                    Txt {
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                        text: Theme.tr("config_path_label")
                        color: Theme.muted
                        font.family: Theme.mono
                        font.pixelSize: 11
                    }
                }
            }
        }
    }
}
