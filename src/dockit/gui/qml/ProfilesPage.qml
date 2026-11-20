import QtQuick
import QtQuick.Layouts
import QtQuick.Controls

Flickable {
    id: page
    property var d: ({})
    property string selId: ""
    property bool showRunning: false
    readonly property var curEdit: cur ? cur.edit : ({ power: "keep", camera: "keep", output: "", input: "", brightness: 0, refresh: 0 })
    readonly property var curRule: cur ? cur.rule : ({ processes: [], when: "", idle: 0, temp: 0, hours: "" })
    readonly property var list: d.profiles ? d.profiles : []
    readonly property var cur: {
        for (var i = 0; i < list.length; i++)
            if (list[i].id === selId) return list[i]
        return list.length > 0 ? list[0] : null
    }
    readonly property string curId: cur ? String(cur.id) : ""

    // SyncModel keeps delegates alive across 3-second refreshes so tooltips and clicks do not break.
    SyncModel { id: profilesModel }
    SyncModel { id: modesModel }
    SyncModel { id: outputsModel }
    SyncModel { id: inputsModel }
    SyncModel { id: ratesModel }
    SyncModel { id: ruleProcsModel }
    SyncModel { id: appsModel }

    function syncAll() {
        var profs = page.list.map(function (p) { return { id: p.id, name: p.name, sub: p.sub } })
        profilesModel.sync(profs)
        modesModel.sync(page.d.modes ? page.d.modes : [])
        var outs = page.d.audio && page.d.audio.outputs ? page.d.audio.outputs : []
        outputsModel.sync(outs.map(function (t) { return { text: t } }))
        var ins = page.d.audio && page.d.audio.inputs ? page.d.audio.inputs : []
        inputsModel.sync(ins.map(function (t) { return { text: t } }))
        var rates = page.d.display && page.d.display.rates ? page.d.display.rates : []
        ratesModel.sync(rates.map(function (r) { return { hz: r } }))
        var procs = page.curRule && page.curRule.processes ? page.curRule.processes : []
        ruleProcsModel.sync(procs.map(function (p) { return { name: p } }))
        var apps = (page.d.apps ? page.d.apps : []).filter(function (a) { return procs.indexOf(a) < 0 })
        appsModel.sync(apps.map(function (a) { return { name: a } }))
    }

    onCurIdChanged: {
        syncAll()
        if (hoursField && !hoursField.activeFocus)
            hoursField.text = page.curRule ? String(page.curRule.hours || "") : ""
    }
    Connections {
        target: backend
        function onProfileCreated(pid) { page.selId = pid }
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
        return query !== "" && name.toLowerCase().indexOf(query.toLowerCase()) >= 0
    }
    function anyMatch(names, query) {
        for (var i = 0; i < names.length; i++)
            if (matches(names[i], query)) return true
        return false
    }
    function save(field, value) {
        var e = cur.edit
        var v = { power: e.power, camera: e.camera, output: e.output, input: e.input,
                  brightness: e.brightness, refresh: e.refresh }
        v[field] = value
        backend.saveProfile(cur.id, v.power, v.camera, v.output, v.input, v.brightness, v.refresh)
    }

    function saveRule(procs, when, idle, temp, hours) {
        backend.saveRule(cur.id, procs.join(","), when, idle,
                         temp === undefined ? cur.rule.temp : temp,
                         hours === undefined ? cur.rule.hours : hours)
    }
    function addProgram(name) {
        var n = name.trim()
        if (n === "" || cur.rule.processes.indexOf(n) >= 0) return
        saveRule(cur.rule.processes.concat([n]), cur.rule.when, cur.rule.idle)
    }
    function removeProgram(name) {
        saveRule(cur.rule.processes.filter(function (x) { return x !== name }), cur.rule.when, cur.rule.idle)
    }

    readonly property int sidePad: page.width < 560 ? 16 : 32
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
        spacing: 24

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 4
            Txt { Layout.fillWidth: true; wrapMode: Text.WordWrap; text: "Профили"; font.pixelSize: page.width < 560 ? 22 : 28; font.weight: Font.DemiBold }
            Txt { Layout.fillWidth: true; wrapMode: Text.WordWrap; text: "Набор настроек под задачу и правила, когда его включать"; color: Theme.muted }
        }

        GridLayout {
            Layout.fillWidth: true
            columns: page.width >= 820 ? 2 : 1
            columnSpacing: 16
            rowSpacing: 16

            // ----- profile list -----
            Card {
                Layout.preferredWidth: page.width >= 820 ? 290 : -1
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
                        implicitHeight: 40
                        placeholderText: "Новый профиль"
                        placeholderTextColor: Theme.muted
                        color: Theme.text
                        font.family: Theme.sans
                        font.pixelSize: 14
                        leftPadding: 12
                        maximumLength: 30
                        ToolTip.text: "Назовите профиль, например «Кино» или «Учёба», и нажмите «Создать»."
                        ToolTip.visible: hovered
                        ToolTip.delay: 450
                        background: Rectangle { radius: 10; color: Theme.cardInner; border.width: 1; border.color: newName.activeFocus ? Theme.accent : Theme.border2 }
                        onAccepted: { backend.createProfile(text); text = "" }
                    }
                    Btn { text: "Создать"; implicitHeight: 40; onClicked: { backend.createProfile(newName.text); newName.text = "" } }
                }
                Repeater {
                    model: profilesModel
                    delegate: Rectangle {
                        readonly property bool sel: page.cur !== null && model.id === page.cur.id
                        Layout.fillWidth: true
                        implicitHeight: 64
                        radius: 12
                        color: sel ? "#1B2D40" : Theme.cardInner
                        border.width: 1
                        border.color: sel ? Theme.accent : Theme.border2
                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 14
                            anchors.rightMargin: 14
                            spacing: 8
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                Txt {
                                    text: model.name
                                    font.pixelSize: 15
                                    font.weight: Font.DemiBold
                                    color: sel ? "#FFFFFF" : Theme.text
                                }
                                Txt {
                                    text: model.sub
                                    font.pixelSize: 12
                                    color: sel ? "#A9D3FF" : Theme.muted
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

            // ----- selected profile -----
            ColumnLayout {
                Layout.fillWidth: true
                Layout.minimumWidth: 0
                Layout.alignment: Qt.AlignTop
                spacing: 16

                Card {
                    Layout.fillWidth: true
                    visible: page.cur !== null
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 10
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2
                            Txt { Layout.fillWidth: true; wrapMode: Text.WordWrap; text: page.cur ? page.cur.name : ""; font.pixelSize: 20; font.weight: Font.DemiBold }
                            Txt { Layout.fillWidth: true; wrapMode: Text.WordWrap; text: page.cur ? page.cur.sub : ""; color: Theme.muted; font.pixelSize: 13 }
                        }
                        Flow {
                            Layout.fillWidth: true
                            spacing: 8
                            Chip {
                                visible: !!(page.cur !== null && page.d.scenario === page.cur.id)
                                kind: "ok"
                                icon: "check"
                                text: "Сейчас применён"
                            }
                            Btn {
                                visible: !!(page.cur !== null && page.d.scenario !== page.cur.id)
                                primary: true
                                implicitHeight: 38
                                text: "Применить сейчас"
                                onClicked: backend.setScenario(page.cur.id)
                            }
                            Btn {
                                visible: !!(page.cur !== null && page.cur.custom === true)
                                implicitHeight: 38
                                text: "Удалить"
                                tip: "Удалить этот профиль и его правила. Встроенные профили удалить нельзя."
                                onClicked: backend.deleteProfile(page.cur.id)
                            }
                        }
                    }
                    Txt { text: "Что применяется"; font.pixelSize: 14; font.weight: Font.DemiBold; color: Theme.muted }
                    Txt {
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                        text: "Выберите значение, оно сохраняется сразу. «Не менять» значит, что профиль эту настройку не трогает."
                        color: Theme.muted
                        font.pixelSize: 12
                    }

                    Txt { text: "Режим мощности"; color: Theme.soft }
                    Flow {
                        Layout.fillWidth: true
                        spacing: 8
                        Pill { text: "Не менять"; tip: "Профиль не трогает режим производительности — остаётся тот, что был."; sel: page.curEdit.power === "keep"; onClicked: page.save("power", "keep") }
                        Repeater {
                            model: modesModel
                            delegate: Pill {
                                text: model.name
                                sel: page.curEdit.power === model.id
                                onClicked: page.save("power", model.id)
                            }
                        }
                    }

                    Txt { text: "Камера"; color: Theme.soft }
                    Flow {
                        Layout.fillWidth: true
                        spacing: 8
                        Pill { text: "Не менять"; sel: page.curEdit.camera === "keep"; onClicked: page.save("camera", "keep") }
                        Pill { text: "Включить"; sel: page.curEdit.camera === "on"; onClicked: page.save("camera", "on") }
                        Pill { text: "Выключить"; sel: page.curEdit.camera === "off"; onClicked: page.save("camera", "off") }
                    }

                    Txt { text: "Звук (вывод)"; color: Theme.soft }
                    Flow {
                        Layout.fillWidth: true
                        spacing: 8
                        Pill { text: "Не менять"; sel: page.curEdit.output === ""; onClicked: page.save("output", "") }
                        Repeater {
                            model: outputsModel
                            delegate: Pill {
                                text: model.text
                                sel: page.matches(model.text, page.curEdit.output)
                                onClicked: page.save("output", model.text)
                            }
                        }
                    }
                    Txt {
                        visible: !!(page.curEdit.output !== "" && !page.anyMatch(page.d.audio ? page.d.audio.outputs : [], page.curEdit.output))
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                        text: "Выбрано: «" + page.curEdit.output + "». Сейчас такое устройство не подключено, при включении профиля звук останется как есть."
                        color: Theme.warn
                        font.pixelSize: 12
                    }

                    Txt { text: "Микрофон"; color: Theme.soft }
                    Flow {
                        Layout.fillWidth: true
                        spacing: 8
                        Pill { text: "Не менять"; sel: page.curEdit.input === ""; onClicked: page.save("input", "") }
                        Repeater {
                            model: inputsModel
                            delegate: Pill {
                                text: model.text
                                sel: page.matches(model.text, page.curEdit.input)
                                onClicked: page.save("input", model.text)
                            }
                        }
                    }
                    Txt {
                        visible: !!(page.curEdit.input !== "" && !page.anyMatch(page.d.audio ? page.d.audio.inputs : [], page.curEdit.input))
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                        text: "Выбрано: «" + page.curEdit.input + "». Сейчас такое устройство не подключено, при включении профиля микрофон останется как есть."
                        color: Theme.warn
                        font.pixelSize: 12
                    }
                }

                Card {
                    Layout.fillWidth: true
                    visible: page.cur !== null
                    Txt { text: "Экран"; font.pixelSize: 16; font.weight: Font.DemiBold }
                    Txt { text: "Яркость"; color: Theme.soft }
                    Flow {
                        Layout.fillWidth: true
                        spacing: 8
                        Pill { text: "Не менять"; sel: page.curEdit.brightness === 0; onClicked: page.save("brightness", 0) }
                        Repeater {
                            model: [20, 40, 60, 80, 100]
                            delegate: Pill {
                                text: modelData + " %"
                                sel: page.curEdit.brightness === modelData
                                onClicked: page.save("brightness", modelData)
                            }
                        }
                    }
                    Txt { text: "Частота экрана"; color: Theme.soft }
                    Flow {
                        Layout.fillWidth: true
                        spacing: 8
                        Pill { text: "Не менять"; sel: page.curEdit.refresh === 0; onClicked: page.save("refresh", 0) }
                        Repeater {
                            model: ratesModel
                            delegate: Pill {
                                text: model.hz + " Гц"
                                tip: "Меньшая частота экономит заряд, большая даёт более плавную картинку."
                                sel: page.curEdit.refresh === model.hz
                                onClicked: page.save("refresh", model.hz)
                            }
                        }
                    }
                    Txt {
                        visible: !!(!page.d.display || !page.d.display.rates || page.d.display.rates.length === 0)
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                        text: "Список частот не найден: смена частоты экрана работает в niri, Hyprland, Sway, KDE Plasma и X11."
                        color: Theme.muted
                        font.pixelSize: 12
                    }
                }

                Card {
                    Layout.fillWidth: true
                    visible: page.cur !== null
                    Txt { text: "Когда включать автоматически"; font.pixelSize: 16; font.weight: Font.DemiBold }
                    Txt {
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                        text: "Работает, когда на странице «Обзор» выбран сценарий «Авто». Если выбраны несколько условий, должны выполняться все сразу. Пусто — профиль сам не включается."
                        color: Theme.muted
                        font.pixelSize: 12
                    }

                    Txt { text: "Запущена программа"; color: Theme.soft }
                    Flow {
                        Layout.fillWidth: true
                        spacing: 8
                        visible: page.curRule.processes.length > 0
                        Repeater {
                            model: ruleProcsModel
                            delegate: Pill {
                                text: model.name + "  ✕"
                                tip: (backend ? backend.describeProgram(model.name) : "") + "\nНажмите, чтобы убрать из списка."
                                sel: true
                                onClicked: page.removeProgram(model.name)
                            }
                        }
                    }
                    Txt {
                        visible: page.curRule.processes.length === 0
                        text: "Программы не выбраны"
                        color: Theme.muted
                        font.pixelSize: 13
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        TextField {
                            id: nameField
                            Layout.fillWidth: true
                            Layout.minimumWidth: 0
                            implicitHeight: 40
                            ToolTip.text: "Имя процесса, как в системе (команда ps). Можно со звёздочкой: steam_app_* — любая игра из Steam."
                            ToolTip.visible: hovered
                            ToolTip.delay: 450
                            placeholderText: "Название программы, например cs2 или steam_app_*"
                            placeholderTextColor: Theme.muted
                            color: Theme.text
                            font.family: Theme.sans
                            font.pixelSize: 14
                            leftPadding: 12
                            selectByMouse: true
                            background: Rectangle {
                                radius: 10
                                color: Theme.cardInner
                                border.width: 1
                                border.color: nameField.activeFocus ? Theme.accent : Theme.border2
                            }
                            onAccepted: { page.addProgram(text); text = "" }
                        }
                        Btn {
                            text: "Добавить"
                            implicitHeight: 40
                            onClicked: { page.addProgram(nameField.text); nameField.text = "" }
                        }
                    }
                    Pill {
                        height: 30
                        text: page.showRunning ? "Скрыть запущенные программы" : "Выбрать из запущенных программ"
                        tip: "Покажет программы, которые открыты сейчас. Наведите на название, чтобы увидеть, что это."
                        onClicked: page.showRunning = !page.showRunning
                    }
                    Txt {
                        visible: !!(page.showRunning && suggestions.count > 0)
                        text: "Нажмите на программу, чтобы добавить её в правило:"
                        color: Theme.muted
                        font.pixelSize: 12
                    }
                    Flow {
                        Layout.fillWidth: true
                        spacing: 6
                        visible: page.showRunning
                        opacity: page.showRunning ? 1 : 0
                        Behavior on opacity { NumberAnimation { duration: 200 } }
                        Repeater {
                            id: suggestions
                            model: appsModel
                            delegate: Pill {
                                height: 30
                                text: model.name
                                tip: (backend ? backend.describeProgram(model.name) : "") + "\nНажмите, чтобы добавить в правило."
                                onClicked: page.addProgram(model.name)
                            }
                        }
                    }

                    Txt { text: "Питание ноутбука"; color: Theme.soft }
                    Flow {
                        Layout.fillWidth: true
                        spacing: 8
                        Pill { text: "Не важно"; sel: page.curRule.when === ""; onClicked: page.saveRule(page.curRule.processes, "", page.curRule.idle) }
                        Pill { text: "Работа от батареи"; tip: "Правило сработает, когда ноутбук отключён от зарядки."; sel: page.curRule.when === "battery"; onClicked: page.saveRule(page.curRule.processes, "battery", page.curRule.idle) }
                        Pill { text: "Подключена зарядка"; tip: "Правило сработает, когда ноутбук подключён к розетке."; sel: page.curRule.when === "ac"; onClicked: page.saveRule(page.curRule.processes, "ac", page.curRule.idle) }
                    }

                    Txt { text: "Нет действий с клавиатурой и мышью"; color: Theme.soft }
                    Flow {
                        Layout.fillWidth: true
                        spacing: 8
                        Pill { text: "Не важно"; sel: page.curRule.idle === 0; onClicked: page.saveRule(page.curRule.processes, page.curRule.when, 0) }
                        Repeater {
                            model: [5, 10, 15, 30, 60]
                            delegate: Pill {
                                text: modelData + " мин"
                                sel: page.curRule.idle === modelData
                                onClicked: page.saveRule(page.curRule.processes, page.curRule.when, modelData)
                            }
                        }
                    }
                    Txt {
                        visible: !page.d.idleAvailable
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                        text: "Чтобы это условие работало, нужна небольшая программа swayidle: sudo pacman -S swayidle"
                        color: Theme.warn
                        font.pixelSize: 12
                    }

                    Txt { text: "Процессор горячее"; color: Theme.soft }
                    Flow {
                        Layout.fillWidth: true
                        spacing: 8
                        Pill { text: "Не важно"; tip: "Температура не учитывается."; sel: page.curRule.temp === 0; onClicked: page.saveRule(page.curRule.processes, page.curRule.when, page.curRule.idle, 0) }
                        Repeater {
                            model: [80, 85, 90, 95]
                            delegate: Pill {
                                text: modelData + " °C"
                                tip: "Защита от перегрева: правило сработает, когда процессор достигнет этой температуры. Оно проверяется раньше остальных. Обычно ему назначают профиль «Ночь» (тихий режим)."
                                sel: page.curRule.temp === modelData
                                onClicked: page.saveRule(page.curRule.processes, page.curRule.when, page.curRule.idle, modelData)
                            }
                        }
                    }

                    Txt { text: "Время суток"; color: Theme.soft }
                    Flow {
                        Layout.fillWidth: true
                        spacing: 8
                        Pill { text: "Не важно"; sel: page.curRule.hours === ""; onClicked: page.saveRule(page.curRule.processes, page.curRule.when, page.curRule.idle, undefined, "") }
                        Repeater {
                            model: ["22:00-07:00", "09:00-18:00", "18:00-23:00"]
                            delegate: Pill {
                                text: modelData.replace("-", " – ")
                                tip: "Правило сработает только в это время суток."
                                sel: page.curRule.hours === modelData
                                onClicked: page.saveRule(page.curRule.processes, page.curRule.when, page.curRule.idle, undefined, modelData)
                            }
                        }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        TextField {
                            id: hoursField
                            Layout.fillWidth: true
                            Layout.maximumWidth: 200
                            Layout.minimumWidth: 0
                            implicitHeight: 40
                            placeholderText: "ЧЧ:ММ-ЧЧ:ММ"
                            placeholderTextColor: Theme.muted
                            color: Theme.text
                            font.family: Theme.sans
                            font.pixelSize: 14
                            leftPadding: 12
                            ToolTip.text: "Своё время, например 23:30-06:45. Можно через полночь."
                            ToolTip.visible: hovered
                            ToolTip.delay: 450
                            background: Rectangle { radius: 10; color: Theme.cardInner; border.width: 1; border.color: hoursField.activeFocus ? Theme.accent : Theme.border2 }
                            onAccepted: page.saveRule(page.curRule.processes, page.curRule.when, page.curRule.idle, undefined, text)
                        }
                        Btn { text: "Задать время"; implicitHeight: 40; onClicked: page.saveRule(page.curRule.processes, page.curRule.when, page.curRule.idle, undefined, hoursField.text) }
                    }
                }

                Card {
                    Layout.fillWidth: true
                    Txt { text: "Если ни одно правило не подошло"; font.pixelSize: 16; font.weight: Font.DemiBold }
                    Txt {
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                        text: "Например, вы отключили игру или снова подключили зарядку: в режиме «Авто» включится этот профиль."
                        color: Theme.muted
                        font.pixelSize: 12
                    }
                    Flow {
                        Layout.fillWidth: true
                        spacing: 8
                        Pill { text: "Ничего не менять"; tip: "Если ни одно правило не подошло, ничего не переключается."; sel: page.d.fallback === ""; onClicked: backend.saveFallback("keep") }
                        Repeater {
                            model: profilesModel
                            delegate: Pill {
                                text: model.name
                                sel: page.d.fallback === model.id
                                onClicked: backend.saveFallback(model.id)
                            }
                        }
                    }
                    Txt {
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                        text: "Файл с настройками: ~/.config/dockit/profiles.toml (можно править и руками)."
                        color: Theme.muted
                        font.pixelSize: 12
                    }
                }
            }
        }
    }
}
