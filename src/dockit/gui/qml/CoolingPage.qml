import QtQuick
import QtQuick.Layouts

PageFrame {
    id: root
    title: Theme.tr("cool_title")
    subtitle: Theme.tr("cool_sub")

    SyncModel { id: tempsModel }
    SyncModel { id: fansModel }
    function syncAll() {
        tempsModel.sync(d.temps)
        fansModel.sync(d.fans)
    }
    Connections { target: backend; function onStateChanged() { syncAll() } }
    Component.onCompleted: syncAll()

    readonly property var cool: d.cooling ? d.cooling : ({})

    // Overheat alert banner
    Card {
        Layout.fillWidth: true
        visible: cool.hot === true
        GridLayout {
            Layout.fillWidth: true
            columns: root.width >= 620 ? 3 : 1
            columnSpacing: 12
            rowSpacing: 10
            Chip { kind: "setup"; text: Theme.tr("cool_hot_chip") }
            Txt {
                Layout.fillWidth: true
                Layout.minimumWidth: 0
                wrapMode: Text.WordWrap
                color: Theme.warn
                text: Theme.tr("cool_hot_msg").replace("{t}", String(cool.warn || 90))
            }
            Btn { text: Theme.tr("change_mode"); onClicked: goto("performance") }
        }
    }

    // Main 3 thermal cards with dynamic temperature colors & bounds on Spark
    GridLayout {
        Layout.fillWidth: true
        columns: width >= 720 ? 3 : (width >= 480 ? 2 : 1)
        columnSpacing: 16
        rowSpacing: 16

        Repeater {
            model: [
                { key: "cpu", icon: "cpu", titleKey: "cpu", noteKey: "throttling_cpu_tip" },
                { key: "gpu", icon: "monitor", titleKey: "gpu", noteKey: "throttling_gpu_tip" },
                { key: "ssd", icon: "layers", titleKey: "chip_nvme", noteKey: "" }
            ]
            delegate: Card {
                pad: 16
                Layout.fillWidth: true
                Layout.fillHeight: true
                readonly property var part: root.cool[modelData.key] ? root.cool[modelData.key] : ({})
                readonly property color tColor: part.throttled === true ? Theme.err : Theme.tempColor(part.now)

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    Icon { name: modelData.icon; size: 15; color: tColor }
                    Txt { Layout.fillWidth: true; text: Theme.tr(modelData.titleKey); font.pixelSize: 15; font.weight: Font.DemiBold }
                    Chip {
                        visible: part.throttled === true
                        kind: "setup"
                        text: Theme.tr("throttling")
                        tip: modelData.noteKey !== "" ? Theme.tr(modelData.noteKey) : ""
                    }
                }
                RowLayout {
                    Txt { text: part.now ? part.now : "—"; font.pixelSize: 30; font.family: Theme.mono; color: tColor }
                    Txt { text: "°C"; color: Theme.muted; Layout.alignment: Qt.AlignBottom; bottomPadding: 6 }
                }
                Row2 { label: Theme.tr("max_session"); value: (part.max ? part.max : "—") + " °C" }
                Spark {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 46
                    implicitHeight: 46
                    showBounds: true
                    unit: "°"
                    values: part.values ? part.values : []
                    lineColor: tColor
                }
                Txt {
                    visible: part.has === false
                    text: Theme.tr("sensor_missing")
                    color: Theme.muted
                    font.pixelSize: 12
                }
            }
        }
    }

    // All hwmon sensors in a crisp 2-column mini-tile grid
    Card {
        Layout.fillWidth: true
        Txt { text: Theme.tr("all_sensors"); font.pixelSize: 16; font.weight: Font.DemiBold }
        Txt {
            visible: tempsModel.count === 0
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            color: Theme.muted
            text: Theme.tr("sensors_missing")
        }
        GridLayout {
            visible: tempsModel.count > 0
            Layout.fillWidth: true
            columns: root.width >= 580 ? 2 : 1
            columnSpacing: 10
            rowSpacing: 10
            Repeater {
                model: tempsModel
                delegate: Rectangle {
                    Layout.fillWidth: true
                    Layout.minimumWidth: 0
                    implicitHeight: 42
                    radius: 10
                    color: Theme.cardInner
                    border.width: 1
                    border.color: model.hot ? Theme.err : Theme.border2
                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 12
                        anchors.rightMargin: 12
                        spacing: 10
                        Rectangle {
                            width: 8; height: 8; radius: 4
                            color: model.hot ? Theme.err : Theme.tempColor(model.value)
                        }
                        Txt { Layout.fillWidth: true; Layout.minimumWidth: 0; elide: Text.ElideRight; text: model.name; color: Theme.soft; font.pixelSize: 13 }
                        Txt { text: model.value + " °C"; color: model.hot ? Theme.err : Theme.text; font.family: Theme.mono; font.pixelSize: 13; font.weight: Font.DemiBold }
                    }
                }
            }
        }
    }

    // Compact fan strip
    Card {
        Layout.fillWidth: true
        pad: 16
        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            Icon { name: "fan"; size: 16; color: Theme.muted }
            Txt { Layout.fillWidth: true; text: Theme.tr("fans"); font.pixelSize: 15; font.weight: Font.DemiBold }
            Chip { kind: fansModel.count > 0 ? "ok" : "no"; text: fansModel.count > 0 ? Theme.tr("fans_visible") : Theme.tr("no_data") }
        }
        Repeater {
            model: fansModel
            delegate: Row2 { label: model.name; value: model.rpm + " " + Theme.tr("unit_rpm") }
        }
        Txt {
            visible: fansModel.count === 0
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            color: Theme.muted
            font.pixelSize: 12
            text: Theme.tr("fans_missing")
        }
    }
}
