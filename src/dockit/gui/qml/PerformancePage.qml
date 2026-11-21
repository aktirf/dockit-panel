import QtQuick
import QtQuick.Layouts
import QtQuick.Controls

Flickable {
    id: page
    property var d: ({})
    readonly property var modeIcons: ({
        "low-power": "fan",
        "balanced": "gauge",
        "dynamic": "pulse",
        "performance": "zap"
    })

    SyncModel { id: modesModel }
    SyncModel { id: topModel }

    function modeDesc(id, fallback) {
        if (id === "low-power") return Theme.tr("mode_low_power_desc")
        if (id === "balanced") return Theme.tr("mode_balanced_desc")
        if (id === "dynamic") return Theme.tr("mode_dynamic_desc")
        if (id === "performance") return Theme.tr("mode_performance_desc")
        return String(fallback || "")
    }
    function eppLabel(key) {
        var map = {
            "performance": "epp_performance",
            "balance_performance": "epp_balance_performance",
            "default": "epp_default",
            "balance_power": "epp_balance_power",
            "power": "epp_power"
        }
        return map[key] ? Theme.tr(map[key]) : String(key)
    }
    function modeOptions() {
        var arr = page.d.modes ? page.d.modes : []
        return arr.map(function (m) {
            return { id: String(m.id), label: String(m.name), tip: page.modeDesc(m.id, m.hint) }
        })
    }
    function eppOptions() {
        var arr = page.d.tuning && page.d.tuning.eppChoices ? page.d.tuning.eppChoices : []
        return arr.map(function (c) {
            return { id: String(c), label: page.eppLabel(c), tip: Theme.tr("epp_tip") }
        })
    }
    function gpuLimitOptions() {
        if (!page.d.tuning || !page.d.tuning.gpuLimit) return []
        var lo = page.d.tuning.gpuLimit.min
        var hi = page.d.tuning.gpuLimit.max
        var mid = Math.round((lo + hi) / 2)
        return [lo, mid, hi].map(function (w) {
            return { id: String(w), label: String(w) + " " + Theme.tr("unit_w"), tip: Theme.tr("gpu_limit_tip") }
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
            Txt { Layout.fillWidth: true; wrapMode: Text.WordWrap; text: Theme.tr("perf_title"); font.pixelSize: page.width < 560 ? 22 : 28; font.weight: Font.DemiBold }
            Txt { Layout.fillWidth: true; wrapMode: Text.WordWrap; text: Theme.tr("perf_sub"); color: Theme.muted }
        }

        // Compact 3-in-a-row mode cards (switches to SegmentBar on narrow windows)
        Card {
            Layout.fillWidth: true
            Txt { text: Theme.tr("power_mode"); font.pixelSize: 16; font.weight: Font.DemiBold }

            SegmentBar {
                visible: col.width < 580
                options: page.modeOptions()
                current: String(page.d.currentMode || "")
                onPicked: function (val) { backend.setMode(val) }
            }

            GridLayout {
                visible: col.width >= 580
                Layout.fillWidth: true
                columns: modesModel.count > 3 ? (col.width >= 760 ? 4 : 2) : 3
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
                                text: page.modeDesc(model.id, model.hint)
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
                Item {
                    Layout.fillWidth: true
                    implicitHeight: cpuHdrRow.implicitHeight
                    RowLayout {
                        id: cpuHdrRow
                        anchors.fill: parent
                        Icon { name: "cpu"; size: 16; color: Theme.accent }
                        Txt { Layout.fillWidth: true; text: Theme.tr("cpu"); font.pixelSize: 15; font.weight: Font.DemiBold }
                    }
                    Tip { text: Theme.tr("tip_cpu_card") }
                }
                Txt { Layout.fillWidth: true; text: page.d.cpu ? page.d.cpu.name : ""; color: Theme.muted; font.pixelSize: 12; elide: Text.ElideRight }
                RowLayout {
                    Txt { text: page.d.cpu ? page.d.cpu.freq : "—"; font.pixelSize: 26; font.family: Theme.mono }
                    Txt { text: Theme.tr("unit_ghz"); color: Theme.muted; Layout.alignment: Qt.AlignBottom; bottomPadding: 6 }
                }
                Bar { Layout.fillWidth: true; value: (page.d.cpu && page.d.cpu.load) ? Number(page.d.cpu.load) : 0 }
                Row2 { label: Theme.tr("load"); value: page.d.cpu && page.d.cpu.load !== null && page.d.cpu.load !== undefined ? page.d.cpu.load + " %" : "—" }
                Row2 {
                    label: Theme.tr("temp")
                    value: page.d.cpu && page.d.cpu.temp && page.d.cpu.temp !== "—" ? page.d.cpu.temp + " °C" : "—"
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
                    Txt { Layout.fillWidth: true; text: Theme.tr("gpu"); font.pixelSize: 15; font.weight: Font.DemiBold }
                    Chip {
                        visible: !!(page.d.gpu && page.d.gpu.sleepText && page.d.gpu.sleepText !== "—")
                        kind: !!(page.d.gpu && page.d.gpu.asleep) ? "ok" : ((page.d.gpu && page.d.gpu.sleepText === Theme.tr("gpu_sleep_never")) ? "setup" : "info")
                        text: page.d.gpu ? String(page.d.gpu.sleepText || "") : ""
                        tip: page.d.gpu ? String(page.d.gpu.sleepTip || "") : ""
                    }
                }
                Txt { Layout.fillWidth: true; text: page.d.gpu ? page.d.gpu.name : ""; color: Theme.muted; font.pixelSize: 12; elide: Text.ElideRight }
                RowLayout {
                    Txt {
                        text: !!(page.d.gpu && page.d.gpu.asleep) ? Theme.tr("gpu_sleeping") : (page.d.gpu ? page.d.gpu.clock : "—")
                        color: !!(page.d.gpu && page.d.gpu.asleep) ? Theme.okText : Theme.text
                        font.pixelSize: 26
                        font.family: Theme.mono
                    }
                    Txt {
                        visible: !!(page.d.gpu && !page.d.gpu.asleep)
                        text: Theme.tr("unit_mhz")
                        color: Theme.muted
                        Layout.alignment: Qt.AlignBottom
                        bottomPadding: 6
                    }
                }
                Bar { Layout.fillWidth: true; value: page.d.gpu && page.d.gpu.util !== null && page.d.gpu.util !== undefined ? page.d.gpu.util : 0 }
                Row2 { label: Theme.tr("load"); value: page.d.gpu && page.d.gpu.util !== null && page.d.gpu.util !== undefined ? page.d.gpu.util + " %" : "—" }
                Row2 {
                    label: Theme.tr("temp")
                    value: page.d.gpu && page.d.gpu.temp && page.d.gpu.temp !== "—" ? page.d.gpu.temp + " °C" : "—"
                    valueColor: Theme.tempColor(page.d.gpu ? page.d.gpu.temp : null)
                }
                Row2 { label: Theme.tr("power_draw"); value: page.d.gpu && page.d.gpu.power && page.d.gpu.power !== "—" ? page.d.gpu.power + " " + Theme.tr("unit_w") : "—" }
                Txt {
                    id: gpuHoldersText
                    Layout.fillWidth: true
                    visible: !!(page.d.gpu && page.d.gpu.holders && page.d.gpu.holders.length > 0)
                    text: visible ? Theme.tr("holders_prefix") + page.d.gpu.holders.join(", ") : ""
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

        // Fine tuning
        Card {
            Layout.fillWidth: true
            Txt { text: Theme.tr("fine_tuning"); font.pixelSize: 16; font.weight: Font.DemiBold }

            ToggleCard {
                Layout.fillWidth: true
                icon: "zap"
                label: Theme.tr("turbo_boost")
                tip: Theme.tr("tip_turbo_boost")
                on: !!(page.d.tuning && page.d.tuning.boost === true)
                can: !!(page.d.tuning && page.d.tuning.boost !== null && page.d.tuning.boost !== undefined)
                onToggled: backend.setBoost(!on)
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 6
                Txt { text: Theme.tr("epp_title"); color: Theme.soft; font.pixelSize: 13 }
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
                    text: Theme.tr("epp_unavailable")
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 6
                Txt { text: Theme.tr("gpu_limit_title"); color: Theme.soft; font.pixelSize: 13 }
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
                    text: Theme.tr("gpu_limit_unavailable")
                }
            }
        }

        // Top CPU consumers
        Card {
            Layout.fillWidth: true
            Txt { text: Theme.tr("top_cpu_title"); font.pixelSize: 16; font.weight: Font.DemiBold }
            Txt {
                visible: topModel.count === 0
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                color: Theme.muted
                font.pixelSize: 13
                text: Theme.tr("top_cpu_empty")
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
            Txt { Layout.fillWidth: true; wrapMode: Text.WordWrap; text: Theme.tr("top_cpu_note"); color: Theme.muted; font.pixelSize: 12 }
        }
    }
}
