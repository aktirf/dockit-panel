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
                    Repeater {
                        model: page.cur ? page.cur.rows : []
                        delegate: RowLayout {
                            Layout.fillWidth: true
                            Txt { Layout.fillWidth: true; text: modelData.label; color: Theme.soft }
                            Txt {
                                text: modelData.value
                                color: modelData.value === "Не меняется" ? Theme.muted : Theme.text
                            }
                        }
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
