import QtQuick
import QtQuick.Layouts
import QtQuick.Controls

Flickable {
    id: page
    property var d: ({})
    readonly property var details: ({
        "low-power": "Тихо и экономно: меньше шума и нагрева, дольше от батареи.",
        "balanced": "Золотая середина для повседневной работы и умеренного шума.",
        "performance": "Максимум мощности для игр и тяжёлых задач."
    })
    readonly property var modeIcons: ({
        "low-power": "fan",
        "balanced": "gauge",
        "performance": "zap"
    })

    SyncModel { id: modesModel }
    SyncModel { id: topModel }
    readonly property var eppNames: ({
        "performance": "Максимум", "balance_performance": "Быстрее", "default": "По умолчанию",
        "balance_power": "Экономнее", "power": "Экономия"
    })
    function modeOptions() {
        var arr = page.d.modes ? page.d.modes : []
        return arr.map(function (m) {
            return { id: String(m.id), label: String(m.name), tip: page.details[m.id] ? page.details[m.id] : String(m.hint || "") }
        })
    }
    function eppOptions() {
        var arr = page.d.tuning && page.d.tuning.eppChoices ? page.d.tuning.eppChoices : []
        return arr.map(function (c) {
            return { id: String(c), label: page.eppNames[c] ? page.eppNames[c] : String(c), tip: "Баланс скорости и энергопотребления CPU." }
        })
    }
    function gpuLimitOptions() {
        if (!page.d.tuning || !page.d.tuning.gpuLimit) return []
        var lo = page.d.tuning.gpuLimit.min
        var hi = page.d.tuning.gpuLimit.max
        var mid = Math.round((lo + hi) / 2)
        return [lo, mid, hi].map(function (w) {
            return { id: String(w), label: String(w) + " Вт", tip: "Меньше ватт — тише и холоднее." }
        })
    }

    Connections { target: backend; function onStateChanged() { modesModel.sync(page.d.modes); topModel.sync(page.d.top) } }
    Component.onCompleted: { modesModel.sync(d.modes); topModel.sync(d.top) }

    readonly property int sidePad: page.width < 560 ? 16 : 32
    contentWidth: width
    contentHeight: col.implicitHeight + 68
    clip: true
    boundsBehavior: Flickable.StopAtBounds
    ScrollBar.vertical: ScrollBar {}

    ColumnLayout {
        id: col
        width: Math.min(Math.max(200, page.width - page.sidePad * 2), 1020)
        x: Math.max(page.sidePad, (page.width - width) / 2)
        y: 28
        spacing: 20

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 4
            Txt { Layout.fillWidth: true; wrapMode: Text.WordWrap; text: "Производительность"; font.pixelSize: page.width < 560 ? 22 : 28; font.weight: Font.DemiBold }
            Txt { Layout.fillWidth: true; wrapMode: Text.WordWrap; text: "Режим работы ноутбука, тонкая настройка и нагрузка прямо сейчас"; color: Theme.muted }
        }

        // Compact 3-in-a-row mode cards (switches to SegmentBar on narrow windows)
        Card {
            Layout.fillWidth: true
            Txt { text: "Режим мощности"; font.pixelSize: 16; font.weight: Font.DemiBold }

            SegmentBar {
                visible: col.width < 580
                options: page.modeOptions()
                current: String(page.d.currentMode || "")
                onPicked: function (val) { backend.setMode(val) }
            }

            GridLayout {
                visible: col.width >= 580
                Layout.fillWidth: true
                columns: 3
                columnSpacing: 12
                rowSpacing: 12

                Repeater {
                    model: modesModel
                    delegate: Rectangle {
                        id: modeTile
                        readonly property bool sel: model.id === page.d.currentMode
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.minimumWidth: 0
                        implicitHeight: tileCol.implicitHeight + 28
                        radius: 14
                        color: sel ? "#192634" : Theme.cardInner
                        border.width: 1
                        border.color: sel ? Theme.accent : Theme.border2
                        Behavior on color { ColorAnimation { duration: 180 } }
                        Behavior on border.color { ColorAnimation { duration: 180 } }

                        ColumnLayout {
                            id: tileCol
                            anchors.fill: parent
                            anchors.margins: 14
                            spacing: 8
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 10
                                Rectangle {
                                    implicitWidth: 32
                                    implicitHeight: 32
                                    radius: 9
                                    color: modeTile.sel ? Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.18) : Theme.card
                                    Icon {
                                        anchors.centerIn: parent
                                        name: page.modeIcons[model.id] ? page.modeIcons[model.id] : "gauge"
                                        size: 16
                                        color: modeTile.sel ? Theme.accent : Theme.muted
                                    }
                                }
                                Txt {
                                    Layout.fillWidth: true
                                    Layout.minimumWidth: 0
                                    elide: Text.ElideRight
                                    text: model.name
                                    font.pixelSize: 14
                                    font.weight: Font.DemiBold
                                    color: modeTile.sel ? "#FFFFFF" : Theme.text
                                }
                            }
                            Txt {
                                Layout.fillWidth: true
                                wrapMode: Text.WordWrap
                                text: page.details[model.id] ? page.details[model.id] : model.hint
                                font.pixelSize: 12
                                color: modeTile.sel ? Theme.soft : Theme.muted
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
        }

        // Live CPU & GPU cards
        GridLayout {
            Layout.fillWidth: true
            columns: width >= 560 ? 2 : 1
            columnSpacing: 16
            rowSpacing: 16

            Card {
                pad: 16
                Layout.fillWidth: true
                Layout.fillHeight: true
                RowLayout {
                    Layout.fillWidth: true
                    Icon { name: "cpu"; size: 16; color: Theme.accent }
                    Txt { Layout.fillWidth: true; text: "Процессор"; font.pixelSize: 15; font.weight: Font.DemiBold }
                }
                Txt { Layout.fillWidth: true; text: page.d.cpu ? page.d.cpu.name : ""; color: Theme.muted; font.pixelSize: 12; elide: Text.ElideRight }
                RowLayout {
                    Txt { text: page.d.cpu ? page.d.cpu.freq : "—"; font.pixelSize: 26; font.family: Theme.mono }
                    Txt { text: "ГГц"; color: Theme.muted; Layout.alignment: Qt.AlignBottom; bottomPadding: 6 }
                }
                Bar { Layout.fillWidth: true; value: (page.d.cpu && page.d.cpu.load) ? Number(page.d.cpu.load) : 0 }
                Row2 { label: "Загрузка"; value: page.d.cpu && page.d.cpu.load !== null ? page.d.cpu.load + " %" : "—" }
                Row2 {
                    label: "Температура"
                    value: page.d.cpu ? page.d.cpu.temp + " °C" : "—"
                    valueColor: Theme.tempColor(page.d.cpu ? page.d.cpu.temp : null)
                }
                Spark {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 34
                    implicitHeight: 34
                    values: page.d.cpuHistory ? page.d.cpuHistory : []
                    lineColor: Theme.tempColor(page.d.cpu ? page.d.cpu.temp : null)
                }
            }

            Card {
                pad: 16
                Layout.fillWidth: true
                Layout.fillHeight: true
                RowLayout {
                    Layout.fillWidth: true
                    Icon { name: "monitor"; size: 16; color: Theme.accent }
                    Txt { Layout.fillWidth: true; text: "Видеокарта"; font.pixelSize: 15; font.weight: Font.DemiBold }
                    Chip {
                        visible: !!(page.d.gpu && page.d.gpu.sleepText && page.d.gpu.sleepText !== "—")
                        kind: !!(page.d.gpu && page.d.gpu.asleep) ? "ok" : ((page.d.gpu && page.d.gpu.sleepText === "не засыпает") ? "setup" : "info")
                        text: page.d.gpu ? String(page.d.gpu.sleepText || "") : ""
                        tip: page.d.gpu ? String(page.d.gpu.sleepTip || "") : ""
                    }
                }
                Txt { Layout.fillWidth: true; text: page.d.gpu ? page.d.gpu.name : ""; color: Theme.muted; font.pixelSize: 12; elide: Text.ElideRight }
                RowLayout {
                    Txt {
                        text: !!(page.d.gpu && page.d.gpu.asleep) ? "Спит" : (page.d.gpu ? page.d.gpu.clock : "—")
                        color: !!(page.d.gpu && page.d.gpu.asleep) ? Theme.okText : Theme.text
                        font.pixelSize: 26
                        font.family: Theme.mono
                    }
                    Txt {
                        visible: !!(page.d.gpu && !page.d.gpu.asleep)
                        text: "МГц"
                        color: Theme.muted
                        Layout.alignment: Qt.AlignBottom
                        bottomPadding: 6
                    }
                }
                Bar { Layout.fillWidth: true; value: page.d.gpu && page.d.gpu.util !== null && page.d.gpu.util !== undefined ? page.d.gpu.util : 0 }
                Row2 { label: "Загрузка"; value: page.d.gpu && page.d.gpu.util !== null && page.d.gpu.util !== undefined ? page.d.gpu.util + " %" : "—" }
                Row2 {
                    label: "Температура"
                    value: page.d.gpu ? page.d.gpu.temp + " °C" : "—"
                    valueColor: Theme.tempColor(page.d.gpu ? page.d.gpu.temp : null)
                }
                Row2 { label: "Потребление"; value: page.d.gpu ? page.d.gpu.power + " Вт" : "—" }
                Txt {
                    id: gpuHoldersText
                    Layout.fillWidth: true
                    visible: !!(page.d.gpu && page.d.gpu.holders && page.d.gpu.holders.length > 0)
                    text: visible ? "Держат: " + page.d.gpu.holders.join(", ") : ""
                    color: Theme.warn
                    font.pixelSize: 12
                    elide: Text.ElideRight
                }
                Spark {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 34
                    implicitHeight: 34
                    values: page.d.gpuHistory ? page.d.gpuHistory : []
                    lineColor: Theme.tempColor(page.d.gpu ? page.d.gpu.temp : null)
                }
            }
        }

        // Fine tuning (unified with Profiles style)
        Card {
            Layout.fillWidth: true
            Txt { text: "Тонкая настройка"; font.pixelSize: 16; font.weight: Font.DemiBold }

            ToggleCard {
                Layout.fillWidth: true
                icon: "zap"
                label: "Turbo Boost процессора"
                tip: "Когда включён, процессор разгоняется выше базовой частоты. Выключите, чтобы стало тише, холоднее и дольше от батареи."
                on: !!(page.d.tuning && page.d.tuning.boost === true)
                can: !!(page.d.tuning && page.d.tuning.boost !== null && page.d.tuning.boost !== undefined)
                onToggled: backend.setBoost(!on)
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 6
                Txt { text: "Энергопотребление процессора (EPP)"; color: Theme.soft; font.pixelSize: 13 }
                SegmentBar {
                    visible: !!(page.d.tuning && page.d.tuning.eppChoices && page.d.tuning.eppChoices.length > 0)
                    options: page.eppOptions()
                    current: page.d.tuning && page.d.tuning.epp ? String(page.d.tuning.epp) : ""
                    onPicked: function (val) { backend.setEpp(val) }
                }
                Txt {
                    visible: !!(!page.d.tuning || !page.d.tuning.eppChoices || page.d.tuning.eppChoices.length === 0)
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                    color: Theme.muted
                    font.pixelSize: 12
                    text: "Эта настройка процессора недоступна на этом ноутбуке."
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 6
                Txt { text: "Лимит мощности видеокарты"; color: Theme.soft; font.pixelSize: 13 }
                SegmentBar {
                    visible: !!(page.d.tuning && page.d.tuning.gpuLimit)
                    options: page.gpuLimitOptions()
                    current: page.d.tuning && page.d.tuning.gpuLimit ? String(page.d.tuning.gpuLimit.current) : ""
                    onPicked: function (val) { backend.setGpuLimit(Number(val)) }
                }
                Txt {
                    visible: !!(!page.d.tuning || !page.d.tuning.gpuLimit)
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                    color: Theme.muted
                    font.pixelSize: 12
                    text: "Видеокарта этого ноутбука не позволяет менять лимит мощности (зафиксирован производителем)."
                }
            }
        }

        // Top CPU consumers with visual load bars
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
                delegate: ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4
                    Row2 { label: model.name; value: model.cpu + " %" }
                    Bar { Layout.fillWidth: true; implicitHeight: 4; value: Math.min(100, Number(model.cpu || 0)) }
                }
            }
            Txt { text: "100 % равно одному ядру процессора."; color: Theme.muted; font.pixelSize: 12 }
        }
    }
}
