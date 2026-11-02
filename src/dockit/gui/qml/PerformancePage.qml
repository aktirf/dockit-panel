import QtQuick
import QtQuick.Layouts
import QtQuick.Controls

Flickable {
    id: page
    property var d: ({})
    readonly property var details: ({
        "low-power": "Процессор и видеокарта работают спокойнее: меньше шума и нагрева, батарея держит дольше. Подходит для работы с документами, сайтами, видео.",
        "balanced": "Золотая середина: хватает мощности для большинства задач, вентиляторы шумят умеренно. Хороший выбор по умолчанию.",
        "performance": "Максимум мощности для игр и тяжёлых программ. Ноутбук греется сильнее и шумит громче, лучше работать от зарядки."
    })

    SyncModel { id: modesModel }
    SyncModel { id: topModel }
    readonly property var eppNames: ({
        "performance": "Максимум", "balance_performance": "Быстрее", "default": "По умолчанию",
        "balance_power": "Экономнее", "power": "Экономия"
    })
    Connections { target: backend; function onStateChanged() { modesModel.sync(page.d.modes); topModel.sync(page.d.top) } }
    Component.onCompleted: { modesModel.sync(d.modes); topModel.sync(d.top) }

    contentWidth: width
    contentHeight: col.implicitHeight + 68
    clip: true
    boundsBehavior: Flickable.StopAtBounds
    ScrollBar.vertical: ScrollBar {}

    ColumnLayout {
        id: col
        x: 32
        y: 28
        width: page.width - 64
        spacing: 20

        ColumnLayout {
            spacing: 4
            Txt { text: "Производительность"; font.pixelSize: 28; font.weight: Font.DemiBold }
            Txt { text: "Режим работы ноутбука и нагрузка прямо сейчас"; color: Theme.muted }
        }

        Card {
            Layout.fillWidth: true
            Txt { text: "Режим мощности"; font.pixelSize: 16; font.weight: Font.DemiBold }
            Repeater {
                model: modesModel
                delegate: Rectangle {
                    readonly property bool sel: model.id === page.d.currentMode
                    Layout.fillWidth: true
                    implicitHeight: modeCol.implicitHeight + 28
                    radius: 12
                    color: sel ? "#1B2D40" : Theme.cardInner
                    border.width: 1
                    border.color: sel ? Theme.accent : Theme.border2
                    Behavior on color { ColorAnimation { duration: 200 } }
                    Behavior on border.color { ColorAnimation { duration: 200 } }
                    ColumnLayout {
                        id: modeCol
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 4
                        RowLayout {
                            Layout.fillWidth: true
                            Txt { Layout.fillWidth: true; text: model.name; font.pixelSize: 15; font.weight: Font.DemiBold; color: sel ? "#FFFFFF" : Theme.text }
                            Chip { visible: sel; kind: "ok"; text: "Выбран" }
                        }
                        Txt {
                            Layout.fillWidth: true
                            wrapMode: Text.WordWrap
                            text: page.details[model.id] ? page.details[model.id] : model.hint
                            font.pixelSize: 13
                            color: sel ? "#A9D3FF" : Theme.muted
                        }
                    }
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: backend.setMode(model.id)
                    }
                }
            }
        }

        GridLayout {
            Layout.fillWidth: true
            columns: width >= 520 ? 2 : 1
            columnSpacing: 16
            rowSpacing: 16

            Card {
                pad: 14
                Layout.fillWidth: true
                Layout.fillHeight: true
                Txt { text: "Процессор"; font.pixelSize: 15; font.weight: Font.DemiBold }
                Txt { Layout.fillWidth: true; text: page.d.cpu ? page.d.cpu.name : ""; color: Theme.muted; font.pixelSize: 12; elide: Text.ElideRight }
                RowLayout {
                    Txt { text: page.d.cpu ? page.d.cpu.freq : "—"; font.pixelSize: 24; font.family: Theme.mono }
                    Txt { text: "ГГц"; color: Theme.muted; Layout.alignment: Qt.AlignBottom; bottomPadding: 6 }
                }
                Bar { Layout.fillWidth: true; value: page.d.cpu && page.d.cpu.load !== null ? page.d.cpu.load : 0 }
                RowLayout {
                    Txt { Layout.fillWidth: true; text: "Загрузка"; color: Theme.muted }
                    Txt { text: page.d.cpu && page.d.cpu.load !== null ? page.d.cpu.load + " %" : "—"; font.family: Theme.mono }
                }
                RowLayout {
                    Txt { Layout.fillWidth: true; text: "Температура"; color: Theme.muted }
                    Txt { text: page.d.cpu ? page.d.cpu.temp + " °C" : "—"; font.family: Theme.mono }
                }
                Spark { Layout.fillWidth: true; Layout.preferredHeight: 28; implicitHeight: 28; values: page.d.cpuHistory ? page.d.cpuHistory : [] }
            }

            Card {
                pad: 14
                Layout.fillWidth: true
                Layout.fillHeight: true
                Txt { text: "Видеокарта"; font.pixelSize: 15; font.weight: Font.DemiBold }
                Txt { Layout.fillWidth: true; text: page.d.gpu ? page.d.gpu.name : ""; color: Theme.muted; font.pixelSize: 12; elide: Text.ElideRight }
                RowLayout {
                    Txt { text: page.d.gpu ? page.d.gpu.clock : "—"; font.pixelSize: 24; font.family: Theme.mono }
                    Txt { text: "МГц"; color: Theme.muted; Layout.alignment: Qt.AlignBottom; bottomPadding: 6 }
                }
                Bar { Layout.fillWidth: true; value: page.d.gpu && page.d.gpu.util !== null && page.d.gpu.util !== undefined ? page.d.gpu.util : 0 }
                RowLayout {
                    Txt { Layout.fillWidth: true; text: "Загрузка"; color: Theme.muted }
                    Txt { text: page.d.gpu && page.d.gpu.util !== null && page.d.gpu.util !== undefined ? page.d.gpu.util + " %" : "—"; font.family: Theme.mono }
                }
                RowLayout {
                    Txt { Layout.fillWidth: true; text: "Температура"; color: Theme.muted }
                    Txt { text: page.d.gpu ? page.d.gpu.temp + " °C" : "—"; font.family: Theme.mono }
                }
                RowLayout {
                    Txt { Layout.fillWidth: true; text: "Потребление"; color: Theme.muted }
                    Txt { text: page.d.gpu ? page.d.gpu.power + " Вт" : "—"; font.family: Theme.mono }
                }
                Spark { Layout.fillWidth: true; Layout.preferredHeight: 28; implicitHeight: 28; values: page.d.gpuHistory ? page.d.gpuHistory : [] }
            }
        }

        Card {
            Layout.fillWidth: true
            Txt { text: "Тонкая настройка"; font.pixelSize: 16; font.weight: Font.DemiBold }
            ToggleCard {
                Layout.fillWidth: true
                label: "Turbo Boost процессора"
                tip: "Когда включён, процессор разгоняется выше базовой частоты под нагрузкой. Выключите, чтобы стало тише, холоднее и дольше от батареи."
                on: page.d.tuning && page.d.tuning.boost === true
                can: page.d.tuning && page.d.tuning.boost !== null && page.d.tuning.boost !== undefined
                onToggled: backend.setBoost(!on)
            }
            Txt { text: "Энергопотребление процессора"; color: Theme.soft }
            Flow {
                Layout.fillWidth: true
                spacing: 8
                Repeater {
                    model: page.d.tuning && page.d.tuning.eppChoices ? page.d.tuning.eppChoices : []
                    delegate: Pill {
                        text: page.eppNames[modelData] ? page.eppNames[modelData] : modelData
                        tip: "Подсказка процессору, что важнее: скорость или экономия энергии."
                        sel: page.d.tuning && page.d.tuning.epp === modelData
                        onClicked: backend.setEpp(modelData)
                    }
                }
            }
            Txt {
                visible: !page.d.tuning || !page.d.tuning.eppChoices || page.d.tuning.eppChoices.length === 0
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                color: Theme.muted
                font.pixelSize: 12
                text: "Эта настройка процессора недоступна на этом ноутбуке."
            }
            Txt { text: "Лимит мощности видеокарты"; color: Theme.soft }
            Flow {
                Layout.fillWidth: true
                spacing: 8
                visible: page.d.tuning && page.d.tuning.gpuLimit
                Repeater {
                    model: page.d.tuning && page.d.tuning.gpuLimit
                           ? [page.d.tuning.gpuLimit.min,
                              Math.round((page.d.tuning.gpuLimit.min + page.d.tuning.gpuLimit.max) / 2),
                              page.d.tuning.gpuLimit.max] : []
                    delegate: Pill {
                        text: modelData + " Вт"
                        sel: page.d.tuning.gpuLimit.current === modelData
                        tip: "Меньше мощность: тише и холоднее, но игры идут медленнее."
                        onClicked: backend.setGpuLimit(modelData)
                    }
                }
            }
            Txt {
                visible: !page.d.tuning || !page.d.tuning.gpuLimit
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                color: Theme.muted
                font.pixelSize: 12
                text: "Видеокарта этого ноутбука не позволяет менять лимит мощности (он зафиксирован производителем)."
            }
        }

        Card {
            Layout.fillWidth: true
            Txt { text: "Что нагружает процессор"; font.pixelSize: 16; font.weight: Font.DemiBold }
            Txt {
                visible: topModel.count === 0
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                color: Theme.muted
                font.pixelSize: 13
                text: "Сейчас ничто не нагружает процессор заметно."
            }
            Repeater {
                model: topModel
                delegate: Row2 { label: model.name; value: model.cpu + " %" }
            }
            Txt { text: "100 % равно одному ядру процессора."; color: Theme.muted; font.pixelSize: 12 }
        }
    }
}
