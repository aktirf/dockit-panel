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

    // SyncModel keeps lists alive across 3-second refreshes so tooltips and clicks do not break.
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
        return rates.map(function (r) { return { id: String(r), label: String(r) + " Гц", tip: "" } })
    }
    function audioItems(listArr, currentVal) {
        var arr = listArr ? listArr : []
        var res = arr.map(function (t) { return { id: String(t), label: String(t) } })
        if (currentVal && !anyMatch(arr, currentVal))
            res.unshift({ id: String(currentVal), label: String(currentVal) + " (отключено)" })
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
        var res = [{ id: "keep", label: "Ничего не менять" }]
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
            Txt { Layout.fillWidth: true; wrapMode: Text.WordWrap; text: "Профили"; font.pixelSize: page.width < 560 ? 22 : 28; font.weight: Font.DemiBold }
            Txt { Layout.fillWidth: true; wrapMode: Text.WordWrap; text: "Включите нужные переключатели — выключенные параметры профиль не трогает"; color: Theme.muted }
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
                Txt { text: "Ваши профили"; font.pixelSize: 16; font.weight: Font.DemiBold }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    TextField {
                        id: newName
                        Layout.fillWidth: true
                        Layout.minimumWidth: 0
                        implicitHeight: 38
                        placeholderText: "Новый профиль…"
                        placeholderTextColor: Theme.muted
                        color: Theme.text
                        font.family: Theme.sans
                        font.pixelSize: 13
                        leftPadding: 12
                        maximumLength: 30
                        ToolTip.text: "Назовите профиль, например «Кино» или «Учёба», и нажмите «+»."
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
                        tip: "Создать новый профиль"
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

                        // Accent left strip for the selected profile
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
                                text: "Активен"
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

                // Header + 2-tab switcher
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
                            text: page.dirty ? "Есть неприменённые правки" : "Сейчас применён"
                        }
                        Btn {
                            visible: page.cur !== null
                            primary: !!(page.cur !== null && (page.d.scenario !== page.cur.id || page.dirty))
                            implicitHeight: 36
                            text: (page.cur !== null && page.d.scenario === page.cur.id)
                                  ? (page.dirty ? "Применить изменения" : "Применить заново")
                                  : "Применить сейчас"
                            onClicked: {
                                page.dirty = false
                                backend.setScenario(page.cur.id)
                            }
                        }
                        Btn {
                            visible: !!(page.cur !== null && page.cur.custom === true)
                            implicitHeight: 36
                            text: "Удалить"
                            tip: "Удалить этот профиль и его правила. Встроенные профили удалить нельзя."
                            onClicked: backend.deleteProfile(page.cur.id)
                        }
                    }

                    SegmentBar {
                        id: tabBar
                        current: page.tab
                        options: [
                            { id: "settings", label: "Настройки" + (page.cur && page.cur.settingsCount ? " (" + page.cur.settingsCount + ")" : ""), tip: "Что этот профиль меняет при включении" },
                            { id: "rules", label: "Автоправила" + (page.cur && page.cur.rulesCount ? " (" + page.cur.rulesCount + ")" : ""), tip: "Когда профиль включается сам в режиме «Авто»" }
                        ]
                        onPicked: function (val) { page.tab = val }
                    }
                }

                // ========== TAB 1: SETTINGS ==========
                Card {
                    id: settingsTabCard
                    Layout.fillWidth: true
                    visible: page.tab === "settings"

                    // 1. Power profile
                    SettingRow {
                        id: powerRow
                        icon: "gauge"
                        title: "Режим мощности"
                        checked: page.curEdit.power !== "keep"
                        valueText: page.modeLabel(page.curEdit.power)
                        tip: "Переключает режим производительности ноутбука при активации профиля."
                        onToggled: function (on) { page.save("power", on ? "balanced" : "keep") }
                        SegmentBar {
                            options: page.modeOptions()
                            current: String(page.curEdit.power || "")
                            onPicked: function (val) { page.save("power", val) }
                        }
                    }

                    // 2. Camera
                    SettingRow {
                        id: cameraRow
                        icon: "camera"
                        title: "Веб-камера"
                        checked: page.curEdit.camera !== "keep"
                        valueText: page.curEdit.camera === "on" ? "Включить" : "Выключить"
                        tip: "Включает или аппаратно отключает встроенную камеру."
                        onToggled: function (on) { page.save("camera", on ? "off" : "keep") }
                        SegmentBar {
                            options: [
                                { id: "on", label: "Включить", tip: "" },
                                { id: "off", label: "Выключить", tip: "" }
                            ]
                            current: String(page.curEdit.camera || "")
                            onPicked: function (val) { page.save("camera", val) }
                        }
                    }

                    // 3. Brightness
                    SettingRow {
                        id: brightnessRow
                        icon: "sun"
                        title: "Яркость экрана"
                        checked: Number(page.curEdit.brightness || 0) > 0
                        valueText: profBrightSlider.displayValue + " %"
                        tip: "Автоматически выставляет выбранную яркость экрана."
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

                    // 4. Refresh rate
                    SettingRow {
                        id: refreshRow
                        icon: "monitor"
                        title: "Частота экрана"
                        checked: Number(page.curEdit.refresh || 0) > 0
                        valueText: Number(page.curEdit.refresh || 0) + " Гц"
                        tip: "Меньшая частота экономит батарею, большая даёт более плавную картинку."
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
                            text: "Список частот не найден в текущем окружении."
                            color: Theme.muted
                            font.pixelSize: 12
                        }
                    }

                    // 5. Audio output
                    SettingRow {
                        id: outputRow
                        icon: "speaker"
                        title: "Звук (вывод)"
                        checked: String(page.curEdit.output || "") !== ""
                        valueText: String(page.curEdit.output || "")
                        tip: "Переключает устройство воспроизведения (динамики, наушники и т. д.)."
                        onToggled: function (on) {
                            if (!on) { page.save("output", ""); return }
                            var outs = page.d.audio && page.d.audio.outputs ? page.d.audio.outputs : []
                            var defOut = page.d.audio && page.d.audio.outputDefault ? String(page.d.audio.outputDefault) : (outs.length > 0 ? String(outs[0]) : "")
                            if (defOut !== "")
                                page.save("output", defOut)
                            else
                                backend.say("Устройства вывода звука не найдены")
                        }
                        SelectBox {
                            id: outputSelect
                            items: page.audioItems(page.d.audio ? page.d.audio.outputs : [], page.curEdit.output)
                            currentId: page.matchedAudioId(page.d.audio ? page.d.audio.outputs : [], page.curEdit.output)
                            placeholder: "Выберите устройство вывода…"
                            onPicked: function (val) { page.save("output", val) }
                        }
                        Txt {
                            visible: !!(page.curEdit.output !== "" && !page.anyMatch(page.d.audio ? page.d.audio.outputs : [], page.curEdit.output))
                            Layout.fillWidth: true
                            wrapMode: Text.WordWrap
                            text: "Сейчас это устройство не подключено — при включении профиля звук останется как есть."
                            color: Theme.warn
                            font.pixelSize: 12
                        }
                    }

                    // 6. Microphone
                    SettingRow {
                        id: inputRow
                        icon: "mic"
                        title: "Микрофон"
                        checked: String(page.curEdit.input || "") !== ""
                        valueText: String(page.curEdit.input || "")
                        tip: "Переключает микрофон по умолчанию при включении профиля."
                        onToggled: function (on) {
                            if (!on) { page.save("input", ""); return }
                            var ins = page.d.audio && page.d.audio.inputs ? page.d.audio.inputs : []
                            var defIn = page.d.audio && page.d.audio.inputDefault ? String(page.d.audio.inputDefault) : (ins.length > 0 ? String(ins[0]) : "")
                            if (defIn !== "")
                                page.save("input", defIn)
                            else
                                backend.say("Микрофоны не найдены")
                        }
                        SelectBox {
                            id: inputSelect
                            items: page.audioItems(page.d.audio ? page.d.audio.inputs : [], page.curEdit.input)
                            currentId: page.matchedAudioId(page.d.audio ? page.d.audio.inputs : [], page.curEdit.input)
                            placeholder: "Выберите микрофон…"
                            onPicked: function (val) { page.save("input", val) }
                        }
                        Txt {
                            visible: !!(page.curEdit.input !== "" && !page.anyMatch(page.d.audio ? page.d.audio.inputs : [], page.curEdit.input))
                            Layout.fillWidth: true
                            wrapMode: Text.WordWrap
                            text: "Сейчас этот микрофон не подключён — при включении профиля останется текущий."
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
                        text: "Срабатывает, когда на «Обзоре» выбран сценарий «Авто». Если включено несколько условий — должны совпасть все сразу."
                        color: Theme.muted
                        font.pixelSize: 12
                    }

                    // Rule 1: Running program
                    SettingRow {
                        id: ruleAppsRow
                        icon: "app"
                        title: "Запущена программа"
                        offText: "Не важно"
                        checked: page.curRule.processes.length > 0 || page.procsExpanded
                        valueText: page.curRule.processes.length > 0 ? page.curRule.processes.join(", ") : "Добавьте программу ниже"
                        tip: "Профиль включится автоматически, пока запущена любая из указанных программ."
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
                                    tip: (backend ? backend.describeProgram(model.name) : "") + "\nНажмите, чтобы убрать."
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
                                ToolTip.text: "Имя процесса (можно со звёздочкой: steam_app_* — любая игра из Steam)."
                                ToolTip.visible: hovered
                                ToolTip.delay: 450
                                placeholderText: "Например: cs2 или steam_app_*"
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
                                text: "Добавить"
                                implicitHeight: 38
                                onClicked: { page.addProgram(nameField.text); nameField.text = "" }
                            }
                        }
                        Pill {
                            implicitHeight: 30
                            text: page.showRunning ? "Скрыть запущенные" : "Выбрать из запущенных сейчас"
                            tip: "Покажет открытые сейчас программы — нажмите на любую, чтобы добавить."
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
                                    tip: (backend ? backend.describeProgram(model.name) : "") + "\nНажмите, чтобы добавить."
                                    onClicked: page.addProgram(model.name)
                                }
                            }
                        }
                    }

                    // Rule 2: Power source
                    SettingRow {
                        id: rulePowerRow
                        icon: "battery"
                        title: "Питание ноутбука"
                        offText: "Не важно"
                        checked: String(page.curRule.when || "") !== ""
                        valueText: page.curRule.when === "battery" ? "Работа от батареи" : "Подключена зарядка"
                        tip: "Переключает профиль при отключении или подключении зарядки."
                        onToggled: function (on) {
                            page.saveRule(page.curRule.processes, on ? "battery" : "", page.curRule.idle)
                        }
                        SegmentBar {
                            options: [
                                { id: "battery", label: "От батареи", tip: "Когда ноутбук отключён от розетки." },
                                { id: "ac", label: "От зарядки", tip: "Когда ноутбук подключён к розетке." }
                            ]
                            current: String(page.curRule.when || "")
                            onPicked: function (val) { page.saveRule(page.curRule.processes, val, page.curRule.idle) }
                        }
                    }

                    // Rule 3: Idle (AFK)
                    SettingRow {
                        id: ruleIdleRow
                        icon: "clock"
                        title: "Нет действий (AFK)"
                        offText: "Не важно"
                        checked: Number(page.curRule.idle || 0) > 0
                        valueText: "Через " + Number(page.curRule.idle || 0) + " мин"
                        tip: "Включает профиль, если не трогать клавиатуру и мышь указанное время."
                        onToggled: function (on) {
                            page.saveRule(page.curRule.processes, page.curRule.when, on ? 10 : 0)
                        }
                        SegmentBar {
                            options: [
                                { id: "5", label: "5 мин", tip: "" },
                                { id: "10", label: "10 мин", tip: "" },
                                { id: "15", label: "15 мин", tip: "" },
                                { id: "30", label: "30 мин", tip: "" },
                                { id: "60", label: "60 мин", tip: "" }
                            ]
                            current: String(page.curRule.idle || "")
                            onPicked: function (val) { page.saveRule(page.curRule.processes, page.curRule.when, Number(val)) }
                        }
                        Txt {
                            visible: !page.d.idleAvailable
                            Layout.fillWidth: true
                            wrapMode: Text.WordWrap
                            text: "Нужна программа swayidle: sudo pacman -S swayidle"
                            color: Theme.warn
                            font.pixelSize: 12
                        }
                    }

                    // Rule 4: CPU Temperature
                    SettingRow {
                        id: ruleTempRow
                        icon: "flame"
                        title: "Защита от перегрева (CPU)"
                        offText: "Не важно"
                        checked: Number(page.curRule.temp || 0) > 0
                        valueText: "Выше " + Number(page.curRule.temp || 0) + " °C"
                        tip: "Срабатывает раньше остальных правил при достижении указанной температуры процессора."
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

                    // Rule 5: Time of day
                    SettingRow {
                        id: ruleHoursRow
                        icon: "sun"
                        title: "Время суток"
                        offText: "Не важно"
                        checked: String(page.curRule.hours || "") !== ""
                        valueText: String(page.curRule.hours || "").replace("-", " – ")
                        tip: "Ограничивает срабатывание правила часами суток (можно через полночь)."
                        onToggled: function (on) {
                            page.saveRule(page.curRule.processes, page.curRule.when, page.curRule.idle, undefined, on ? "22:00-07:00" : "")
                        }
                        SegmentBar {
                            options: [
                                { id: "22:00-07:00", label: "22:00 – 07:00", tip: "Ночь" },
                                { id: "09:00-18:00", label: "09:00 – 18:00", tip: "День" },
                                { id: "18:00-23:00", label: "18:00 – 23:00", tip: "Вечер" }
                            ]
                            current: String(page.curRule.hours || "")
                            onPicked: function (val) { page.saveRule(page.curRule.processes, page.curRule.when, page.curRule.idle, undefined, val) }
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8
                            TextField {
                                id: hoursField
                                Layout.fillWidth: true
                                Layout.maximumWidth: 200
                                Layout.minimumWidth: 0
                                implicitHeight: 38
                                placeholderText: "ЧЧ:ММ-ЧЧ:ММ"
                                placeholderTextColor: Theme.muted
                                color: Theme.text
                                font.family: Theme.mono
                                font.pixelSize: 13
                                leftPadding: 12
                                ToolTip.text: "Свой интервал, например 23:30-06:45."
                                ToolTip.visible: hovered
                                ToolTip.delay: 450
                                background: Rectangle {
                                    radius: 10
                                    color: Theme.panel
                                    border.width: 1
                                    border.color: hoursField.activeFocus ? Theme.accent : Theme.border2
                                }
                                onAccepted: page.saveRule(page.curRule.processes, page.curRule.when, page.curRule.idle, undefined, text)
                            }
                            Btn {
                                text: "Применить"
                                implicitHeight: 38
                                onClicked: page.saveRule(page.curRule.processes, page.curRule.when, page.curRule.idle, undefined, hoursField.text)
                            }
                        }
                    }
                }

                // Fallback card (shown on the rules tab)
                Card {
                    id: fallbackCard
                    Layout.fillWidth: true
                    visible: page.tab === "rules"
                    Txt { text: "Если ни одно правило не подошло"; font.pixelSize: 15; font.weight: Font.DemiBold }
                    Txt {
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                        text: "Например, вы закрыли игру или подключили зарядку — в режиме «Авто» включится этот профиль."
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
                        text: "Конфиг: ~/.config/dockit/profiles.toml"
                        color: Theme.muted
                        font.family: Theme.mono
                        font.pixelSize: 11
                    }
                }
            }
        }
    }
}
