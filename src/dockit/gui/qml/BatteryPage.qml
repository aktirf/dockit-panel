import QtQuick
import QtQuick.Layouts
import QtQuick.Controls

PageFrame {
    id: batPage
    title: Theme.tr("bat_title")
    subtitle: Theme.tr("bat_sub")

    function rateOptions() {
        var rates = d.display && d.display.rates ? d.display.rates : []
        return rates.map(function (r) {
            return { id: String(r), label: String(r) + " " + Theme.tr("unit_hz"), tip: Theme.tr("refresh_tip") }
        })
    }

    // 2-column top grid: Battery + Display
    GridLayout {
        Layout.fillWidth: true
        columns: batPage.width >= 720 ? 2 : 1
        columnSpacing: 16
        rowSpacing: 16

        // Battery card
        Card {
            Layout.fillWidth: true
            Layout.fillHeight: true
            RowLayout {
                Layout.fillWidth: true
                Icon { name: "battery"; size: 17; color: Theme.batteryColor(d.battery ? d.battery.percent : 100) }
                Txt { Layout.fillWidth: true; text: Theme.tr("battery"); font.pixelSize: 16; font.weight: Font.DemiBold }
                Chip {
                    kind: d.battery && d.battery.percent !== null && d.battery.percent !== undefined ? "ok" : "no"
                    text: d.battery && d.battery.source ? String(d.battery.source) : Theme.tr("no_data")
                }
            }
            RowLayout {
                spacing: 8
                Txt {
                    text: (d.battery && d.battery.percent !== null && d.battery.percent !== undefined) ? String(d.battery.percent) : "—"
                    font.pixelSize: 42
                    font.family: Theme.mono
                    color: Theme.batteryColor(d.battery ? d.battery.percent : 100)
                }
                Txt { text: "%"; color: Theme.muted; Layout.alignment: Qt.AlignBottom; bottomPadding: 8 }
                Item { Layout.fillWidth: true }
                Txt {
                    visible: !!(d.battery && d.battery.left !== undefined && d.battery.left !== "")
                    text: d.battery ? String(d.battery.left) : ""
                    color: Theme.accent
                    font.pixelSize: 13
                    font.weight: Font.DemiBold
                    Layout.alignment: Qt.AlignBottom
                    bottomPadding: 8
                }
            }
            Bar { Layout.fillWidth: true; value: d.battery && d.battery.percent ? d.battery.percent : 0; fill: Theme.batteryColor(d.battery ? d.battery.percent : 100) }
            Txt { text: d.battery ? String(d.battery.text || "") : "—"; color: Theme.muted; font.pixelSize: 13 }

            // 3 compact stat tiles with cursor-anchored hover tips
            GridLayout {
                Layout.fillWidth: true
                columns: 3
                columnSpacing: 8
                rowSpacing: 8
                Rectangle {
                    Layout.fillWidth: true; Layout.minimumWidth: 0; implicitHeight: 54; radius: 10; color: Theme.cardInner
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 8; spacing: 2
                        Txt { text: Theme.tr("bat_capacity"); color: Theme.muted; font.pixelSize: 11 }
                        Txt { text: (d.battery && d.battery.health && d.battery.health !== "—") ? String(d.battery.health) + " %" : "—"; font.family: Theme.mono; font.pixelSize: 14; font.weight: Font.DemiBold }
                    }
                    Tip { text: Theme.tr("tip_bat_health") }
                }
                Rectangle {
                    Layout.fillWidth: true; Layout.minimumWidth: 0; implicitHeight: 54; radius: 10; color: Theme.cardInner
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 8; spacing: 2
                        Txt { text: Theme.tr("bat_cycles"); color: Theme.muted; font.pixelSize: 11 }
                        Txt { text: (d.battery && d.battery.cycles !== null && d.battery.cycles !== undefined) ? String(d.battery.cycles) : "—"; font.family: Theme.mono; font.pixelSize: 14; font.weight: Font.DemiBold }
                    }
                    Tip { text: Theme.tr("tip_bat_cycles") }
                }
                Rectangle {
                    Layout.fillWidth: true; Layout.minimumWidth: 0; implicitHeight: 54; radius: 10; color: Theme.cardInner
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 8; spacing: 2
                        Txt { text: Theme.tr("bat_power"); color: Theme.muted; font.pixelSize: 11 }
                        Txt { text: (d.battery && d.battery.power && d.battery.power !== "—") ? String(d.battery.power) + " " + Theme.tr("unit_w") : "—"; font.family: Theme.mono; font.pixelSize: 14; font.weight: Font.DemiBold }
                    }
                    Tip { text: Theme.tr("tip_bat_power") }
                }
            }
        }

        // Display card
        Card {
            Layout.fillWidth: true
            Layout.fillHeight: true
            RowLayout {
                Layout.fillWidth: true
                Icon { name: "monitor"; size: 17; color: Theme.accent }
                Txt { Layout.fillWidth: true; text: Theme.tr("screen_title"); font.pixelSize: 16; font.weight: Font.DemiBold }
            }

            Row2 {
                label: Theme.tr("brightness")
                value: (d.display && d.display.brightness !== null && d.display.brightness !== undefined)
                       ? (brightnessSlider.displayValue + " %") : "—"
            }
            SmoothSlider {
                id: brightnessSlider
                visible: !!(d.display && d.display.brightness !== null && d.display.brightness !== undefined)
                from: 5
                to: 100
                targetValue: (d.display && d.display.brightness !== null && d.display.brightness !== undefined) ? Number(d.display.brightness) : 50
                onCommitted: function (val) { backend.setBrightness(val) }
            }
            SegmentBar {
                visible: !!(d.display && d.display.brightness !== null && d.display.brightness !== undefined)
                options: [
                    { id: "25", label: "25 %", tip: "" },
                    { id: "50", label: "50 %", tip: "" },
                    { id: "75", label: "75 %", tip: "" },
                    { id: "100", label: "100 %", tip: "" }
                ]
                current: d.display && d.display.brightness !== null && d.display.brightness !== undefined ? String(d.display.brightness) : ""
                onPicked: function (val) { backend.setBrightness(Number(val)) }
            }
            Txt {
                visible: !!(!d.display || d.display.brightness === null || d.display.brightness === undefined)
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                color: Theme.muted
                font.pixelSize: 12
                text: Theme.tr("brightness_missing")
            }

            Rectangle { Layout.fillWidth: true; height: 1; color: Theme.border }

            Row2 { label: Theme.tr("refresh_rate"); value: d.display && d.display.refresh ? d.display.refresh + " " + Theme.tr("unit_hz") : "—" }
            SegmentBar {
                visible: !!(d.display && d.display.rates && d.display.rates.length > 0)
                options: batPage.rateOptions()
                current: d.display && d.display.refresh ? String(d.display.refresh) : ""
                onPicked: function (val) { backend.setRefresh(Number(val)) }
            }
            Txt {
                visible: !!(!d.display || !d.display.rates || d.display.rates.length === 0)
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                color: Theme.muted
                font.pixelSize: 12
                text: Theme.tr("refresh_missing")
            }
        }
    }

    // 24h charge graph
    Card {
        Layout.fillWidth: true
        RowLayout {
            Layout.fillWidth: true
            Txt { Layout.fillWidth: true; text: Theme.tr("bat_history_title"); font.pixelSize: 15; font.weight: Font.DemiBold }
            Txt { text: Theme.tr("bat_history_step"); color: Theme.muted; font.pixelSize: 12 }
        }
        Spark {
            Layout.fillWidth: true
            Layout.preferredHeight: 56
            implicitHeight: 56
            showBounds: true
            unit: "%"
            values: d.batteryHistory ? d.batteryHistory : []
            lineColor: Theme.ok
        }
    }

    // Compact charge limit strip
    Card {
        Layout.fillWidth: true
        pad: 16
        Item {
            Layout.fillWidth: true
            implicitHeight: limHdrRow.implicitHeight
            RowLayout {
                id: limHdrRow
                anchors.fill: parent
                spacing: 12
                Txt { Layout.fillWidth: true; text: Theme.tr("charge_limit_example"); font.pixelSize: 15; font.weight: Font.DemiBold }
                Chip { kind: d.limit ? d.limit.status : "no"; text: d.limit ? d.limit.statusText : "" }
            }
            Tip { text: Theme.tr("tip_charge_limit") }
        }
        Txt {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            visible: !!(d.limit && d.limit.status !== "ok")
            color: Theme.muted
            font.pixelSize: 12
            text: Theme.tr("charge_limit_unavail")
        }
        Txt {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            visible: !!(d.limit && d.limit.hint !== undefined && d.limit.hint !== "")
            color: Theme.warn
            font.pixelSize: 12
            text: Theme.tr("hint_prefix") + (d.limit ? d.limit.hint : "")
        }
    }
}
