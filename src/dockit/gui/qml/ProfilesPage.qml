import QtQuick
import QtQuick.Layouts
import QtQuick.Controls

Flickable {
    id: page
    property var d: ({})
    property string selId: ""
    readonly property var list: d.profiles ? d.profiles : []
    readonly property var cur: {
        for (var i = 0; i < list.length; i++)
            if (list[i].id === selId) return list[i]
        return list.length > 0 ? list[0] : null
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
        var v = { power: e.power, camera: e.camera, output: e.output, input: e.input }
        v[field] = value
        backend.saveProfile(cur.id, v.power, v.camera, v.output, v.input)
    }

    clip: true
    contentWidth: width
    contentHeight: content.implicitHeight + 68
    boundsBehavior: Flickable.StopAtBounds
    ScrollBar.vertical: ScrollBar {}

    ColumnLayout {
        id: content
        x: 32
        y: 28
        width: page.width - 64
        spacing: 24

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 4
            Txt { text: "Профили"; font.pixelSize: 28; font.weight: Font.DemiBold }
            Txt { text: "Набор настроек под задачу и правила, когда его включать"; color: Theme.muted }
        }

        GridLayout {
            Layout.fillWidth: true
            columns: page.width >= 860 ? 2 : 1
            columnSpacing: 16
            rowSpacing: 16

            // ----- profile list -----
            Card {
                Layout.preferredWidth: page.width >= 860 ? 300 : -1
                Layout.fillWidth: page.width < 860
                Layout.alignment: Qt.AlignTop
                Txt { text: "Ваши профили"; font.pixelSize: 16; font.weight: Font.DemiBold }
                Repeater {
                    model: page.list
                    delegate: Rectangle {
                        readonly property bool sel: page.cur !== null && modelData.id === page.cur.id
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
                                    text: modelData.name
                                    font.pixelSize: 15
                                    font.weight: Font.DemiBold
                                    color: sel ? "#FFFFFF" : Theme.text
                                }
                                Txt {
                                    text: modelData.sub
                                    font.pixelSize: 12
                                    color: sel ? "#A9D3FF" : Theme.muted
                                }
                            }
                            Chip {
                                visible: page.d.scenario === modelData.id
                                kind: "ok"
                                text: "Активен"
                            }
                        }
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: page.selId = modelData.id
                        }
                    }
                }
            }

            // ----- selected profile -----
            ColumnLayout {
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignTop
                spacing: 16

                Card {
                    Layout.fillWidth: true
                    visible: page.cur !== null
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 12
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2
                            Txt { text: page.cur ? page.cur.name : ""; font.pixelSize: 20; font.weight: Font.DemiBold }
                            Txt { text: page.cur ? page.cur.sub : ""; color: Theme.muted; font.pixelSize: 13 }
                        }
                        Chip {
                            visible: page.cur !== null && page.d.scenario === page.cur.id
                            kind: "ok"
                            icon: "check"
                            text: "Сейчас применён"
                        }
                        Btn {
                            visible: page.cur !== null && page.d.scenario !== page.cur.id
                            primary: true
                            text: "Применить сейчас"
                            onClicked: backend.setScenario(page.cur.id)
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
                        Pill { text: "Не менять"; sel: page.cur.edit.power === "keep"; onClicked: page.save("power", "keep") }
                        Repeater {
                            model: page.d.modes ? page.d.modes : []
                            delegate: Pill {
                                text: modelData.name
                                sel: page.cur.edit.power === modelData.id
                                onClicked: page.save("power", modelData.id)
                            }
                        }
                    }

                    Txt { text: "Камера"; color: Theme.soft }
                    Flow {
                        Layout.fillWidth: true
                        spacing: 8
                        Pill { text: "Не менять"; sel: page.cur.edit.camera === "keep"; onClicked: page.save("camera", "keep") }
                        Pill { text: "Включить"; sel: page.cur.edit.camera === "on"; onClicked: page.save("camera", "on") }
                        Pill { text: "Выключить"; sel: page.cur.edit.camera === "off"; onClicked: page.save("camera", "off") }
                    }

                    Txt { text: "Звук (вывод)"; color: Theme.soft }
                    Flow {
                        Layout.fillWidth: true
                        spacing: 8
                        Pill { text: "Не менять"; sel: page.cur.edit.output === ""; onClicked: page.save("output", "") }
                        Repeater {
                            model: page.d.audio ? page.d.audio.outputs : []
                            delegate: Pill {
                                text: modelData
                                sel: page.matches(modelData, page.cur.edit.output)
                                onClicked: page.save("output", modelData)
                            }
                        }
                    }
                    Txt {
                        visible: page.cur.edit.output !== "" && !page.anyMatch(page.d.audio ? page.d.audio.outputs : [], page.cur.edit.output)
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                        text: "Выбрано: «" + page.cur.edit.output + "». Сейчас такое устройство не подключено, при включении профиля звук останется как есть."
                        color: Theme.warn
                        font.pixelSize: 12
                    }

                    Txt { text: "Микрофон"; color: Theme.soft }
                    Flow {
                        Layout.fillWidth: true
                        spacing: 8
                        Pill { text: "Не менять"; sel: page.cur.edit.input === ""; onClicked: page.save("input", "") }
                        Repeater {
                            model: page.d.audio ? page.d.audio.inputs : []
                            delegate: Pill {
                                text: modelData
                                sel: page.matches(modelData, page.cur.edit.input)
                                onClicked: page.save("input", modelData)
                            }
                        }
                    }
                    Txt {
                        visible: page.cur.edit.input !== "" && !page.anyMatch(page.d.audio ? page.d.audio.inputs : [], page.cur.edit.input)
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                        text: "Выбрано: «" + page.cur.edit.input + "». Сейчас такое устройство не подключено, при включении профиля микрофон останется как есть."
                        color: Theme.warn
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
                        text: "Работает, когда на странице «Обзор» выбран сценарий «Авто». Проверяются правила сверху вниз, срабатывает первое подходящее."
                        color: Theme.muted
                        font.pixelSize: 13
                    }
                    Repeater {
                        model: page.cur ? page.cur.rules : []
                        delegate: Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: ruleText.implicitHeight + 24
                            radius: 12
                            color: Theme.cardInner
                            Txt {
                                id: ruleText
                                anchors.fill: parent
                                anchors.margins: 12
                                wrapMode: Text.WordWrap
                                text: modelData
                                verticalAlignment: Text.AlignVCenter
                            }
                        }
                    }
                    Txt {
                        visible: page.cur !== null && page.cur.rules.length === 0
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                        text: "Для этого профиля автоматических правил нет."
                        color: Theme.muted
                    }
                    Txt {
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                        text: "Свои профили и правила описываются в файле ~/.config/dockit/profiles.toml (пример есть в README)."
                        color: Theme.muted
                        font.pixelSize: 12
                    }
                }
            }
        }
    }
}
