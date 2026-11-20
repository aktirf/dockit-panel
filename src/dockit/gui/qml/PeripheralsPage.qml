import QtQuick
import QtQuick.Layouts
import QtQuick.Controls

PageFrame {
    id: periphPage
    title: "Периферия и звук"
    subtitle: "Громкость, аудиоустройства, Bluetooth и USB-периферия"

    SyncModel { id: periphModel }
    SyncModel { id: btModel }
    function syncAll() {
        periphModel.sync(d.peripherals)
        btModel.sync(d.bluetooth)
    }
    Connections { target: backend; function onStateChanged() { syncAll() } }
    Component.onCompleted: syncAll()

    function audioItems(arr) {
        return (arr ? arr : []).map(function (t) { return { id: String(t), label: String(t) } })
    }
    function deviceIcon(kindText) {
        var k = String(kindText || "").toLowerCase()
        if (k.indexOf("мыш") >= 0) return "mouse"
        if (k.indexOf("клав") >= 0) return "keyboard"
        if (k.indexOf("кам") >= 0) return "camera"
        if (k.indexOf("гарн") >= 0 || k.indexOf("науш") >= 0) return "headphones"
        if (k.indexOf("bluetooth") >= 0) return "bluetooth"
        return "app"
    }

    readonly property bool audioMuted: !!(d.audio && d.audio.outputMuted === true)
    readonly property bool hasVolume: !!(d.audio && d.audio.outputVolume !== undefined && d.audio.outputVolume !== null && Number(d.audio.outputVolume) >= 0)

    // 1. Sound card (Volume slider + Mute + SelectBox dropdowns)
    Card {
        id: soundCard
        Layout.fillWidth: true
        RowLayout {
            Layout.fillWidth: true
            Icon { name: periphPage.audioMuted ? "volumeMute" : "speaker"; size: 17; color: periphPage.audioMuted ? Theme.err : Theme.accent }
            Txt { Layout.fillWidth: true; text: "Звук"; font.pixelSize: 16; font.weight: Font.DemiBold }
            Txt {
                visible: periphPage.hasVolume
                text: periphPage.audioMuted
                      ? "Без звука"
                      : (volSlider.pressed ? Math.round(volSlider.value) + " %" : String(d.audio.outputVolume) + " %")
                font.family: Theme.mono
                font.pixelSize: 13
                color: periphPage.audioMuted ? Theme.err : Theme.text
            }
        }

        // Volume slider + Mute button
        RowLayout {
            visible: periphPage.hasVolume
            Layout.fillWidth: true
            spacing: 12
            Rectangle {
                implicitWidth: 38
                implicitHeight: 38
                radius: 10
                color: periphPage.audioMuted ? Qt.rgba(1.0, 0.478, 0.478, 0.16) : Theme.btn
                border.width: 1
                border.color: periphPage.audioMuted ? Theme.err : Theme.border3
                Icon {
                    anchors.centerIn: parent
                    name: periphPage.audioMuted ? "volumeMute" : "speaker"
                    size: 18
                    color: periphPage.audioMuted ? Theme.err : Theme.soft
                }
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: backend.toggleMuteOutput()
                }
                Tip { text: periphPage.audioMuted ? "Включить звук" : "Выключить звук (Mute)" }
            }
            Slider {
                id: volSlider
                Layout.fillWidth: true
                from: 0
                to: 150
                stepSize: 1
                value: periphPage.hasVolume ? Number(d.audio.outputVolume) : 50
                onPressedChanged: {
                    if (!pressed)
                        backend.setVolume(Math.round(value))
                }
                background: Rectangle {
                    x: volSlider.leftPadding
                    y: volSlider.topPadding + volSlider.availableHeight / 2 - height / 2
                    width: volSlider.availableWidth
                    height: 6
                    radius: 3
                    color: Theme.border2
                    Rectangle {
                        width: volSlider.visualPosition * parent.width
                        height: parent.height
                        radius: 3
                        color: periphPage.audioMuted ? Theme.muted : (volSlider.value > 100 ? Theme.warn : Theme.accent)
                    }
                }
                handle: Rectangle {
                    x: volSlider.leftPadding + volSlider.visualPosition * (volSlider.availableWidth - width)
                    y: volSlider.topPadding + volSlider.availableHeight / 2 - height / 2
                    width: 18
                    height: 18
                    radius: 9
                    color: volSlider.pressed ? "#FFFFFF" : (periphPage.audioMuted ? Theme.muted : Theme.accent)
                    border.width: 2
                    border.color: Theme.card
                }
            }
        }

        // Output & Microphone dropdowns side-by-side on wide windows
        GridLayout {
            Layout.fillWidth: true
            columns: periphPage.width >= 660 ? 2 : 1
            columnSpacing: 14
            rowSpacing: 12

            ColumnLayout {
                Layout.fillWidth: true
                Layout.minimumWidth: 0
                spacing: 6
                Txt { text: "Куда играет звук"; color: Theme.soft; font.pixelSize: 13 }
                SelectBox {
                    id: periphOutSelect
                    items: periphPage.audioItems(d.audio ? d.audio.outputs : [])
                    currentId: d.audio && d.audio.outputDefault ? String(d.audio.outputDefault) : ""
                    placeholder: "Устройства вывода не найдены"
                    onPicked: function (val) { backend.setAudio("output", val) }
                }
            }
            ColumnLayout {
                Layout.fillWidth: true
                Layout.minimumWidth: 0
                spacing: 6
                Txt { text: "Микрофон"; color: Theme.soft; font.pixelSize: 13 }
                SelectBox {
                    id: periphInSelect
                    items: periphPage.audioItems(d.audio ? d.audio.inputs : [])
                    currentId: d.audio && d.audio.inputDefault ? String(d.audio.inputDefault) : ""
                    placeholder: "Микрофоны не найдены"
                    onPicked: function (val) { backend.setAudio("input", val) }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 12
            Txt {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                color: Theme.muted
                font.pixelSize: 12
                text: "Для автопереключения звука под игры или звонки задайте устройства в «Профилях»."
            }
            Btn { text: "Профили"; implicitHeight: 34; onClicked: goto("profiles") }
        }
    }

    // 2. Bluetooth devices with battery bars
    Card {
        Layout.fillWidth: true
        RowLayout {
            Layout.fillWidth: true
            Icon { name: "bluetooth"; size: 17; color: Theme.accent }
            Txt { Layout.fillWidth: true; text: "Bluetooth-устройства"; font.pixelSize: 16; font.weight: Font.DemiBold }
            Chip {
                visible: btModel.count > 0
                kind: "ok"
                text: "Подключено: " + btModel.count
            }
        }
        Txt {
            visible: btModel.count === 0
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            color: Theme.muted
            font.pixelSize: 13
            text: "Подключённых Bluetooth-устройств нет."
        }
        GridLayout {
            visible: btModel.count > 0
            Layout.fillWidth: true
            columns: periphPage.width >= 660 ? 2 : 1
            columnSpacing: 12
            rowSpacing: 10
            Repeater {
                model: btModel
                delegate: Rectangle {
                    Layout.fillWidth: true
                    Layout.minimumWidth: 0
                    implicitHeight: btCol.implicitHeight + 22
                    radius: 12
                    color: Theme.cardInner
                    border.width: 1
                    border.color: Theme.border2
                    ColumnLayout {
                        id: btCol
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 6
                        RowLayout {
                            Layout.fillWidth: true
                            Txt { Layout.fillWidth: true; Layout.minimumWidth: 0; elide: Text.ElideRight; text: model.name; font.weight: Font.Medium }
                            Txt {
                                text: model.battery >= 0 ? model.battery + " %" : "заряд ?"
                                font.family: Theme.mono
                                font.pixelSize: 13
                                color: model.battery >= 0 ? Theme.batteryColor(model.battery) : Theme.muted
                            }
                        }
                        Bar {
                            visible: model.battery >= 0
                            Layout.fillWidth: true
                            value: model.battery >= 0 ? model.battery : 0
                            fill: Theme.batteryColor(model.battery)
                        }
                    }
                }
            }
        }
    }

    // 3. USB peripherals in a responsive 2-column grid with icons
    Card {
        Layout.fillWidth: true
        RowLayout {
            Layout.fillWidth: true
            Icon { name: "mouse"; size: 17; color: Theme.accent }
            Txt { Layout.fillWidth: true; text: "USB-устройства"; font.pixelSize: 16; font.weight: Font.DemiBold }
            Txt { text: periphModel.count > 0 ? String(periphModel.count) : ""; color: Theme.muted; font.family: Theme.mono; font.pixelSize: 13 }
        }
        Txt {
            visible: periphModel.count === 0
            text: "USB-устройства не найдены."
            color: Theme.muted
            font.pixelSize: 13
        }
        GridLayout {
            visible: periphModel.count > 0
            Layout.fillWidth: true
            columns: periphPage.width >= 680 ? 2 : 1
            columnSpacing: 12
            rowSpacing: 12
            Repeater {
                model: periphModel
                delegate: Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumWidth: 0
                    implicitHeight: usbCol.implicitHeight + 24
                    radius: 12
                    color: Theme.cardInner
                    border.width: 1
                    border.color: Theme.border2
                    ColumnLayout {
                        id: usbCol
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: 12
                        spacing: 8
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Rectangle {
                                implicitWidth: 34
                                implicitHeight: 34
                                radius: 9
                                color: model.known ? Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.14) : Theme.card
                                Icon {
                                    anchors.centerIn: parent
                                    name: periphPage.deviceIcon(model.kind)
                                    size: 17
                                    color: model.known ? Theme.accent : Theme.muted
                                }
                            }
                            ColumnLayout {
                                Layout.fillWidth: true
                                Layout.minimumWidth: 0
                                spacing: 1
                                Txt { Layout.fillWidth: true; elide: Text.ElideRight; text: model.name; font.pixelSize: 14; font.weight: Font.DemiBold }
                                Txt { Layout.fillWidth: true; elide: Text.ElideRight; text: model.kind + " · USB " + model.usbId; color: Theme.muted; font.pixelSize: 11; font.family: Theme.mono }
                            }
                            Chip {
                                kind: model.known ? "ok" : "no"
                                text: model.known ? "В базе" : "Неизвестно"
                                tip: model.known ? "Устройство есть в базе DOCKIT." : "Устройства нет в базе (папка devices/)."
                            }
                        }
                        Txt {
                            Layout.fillWidth: true
                            visible: model.notes !== ""
                            wrapMode: Text.WordWrap
                            text: model.notes
                            color: Theme.muted
                            font.pixelSize: 12
                        }
                    }
                }
            }
        }
    }

    // 4. Compact keyboard backlight strip
    Card {
        id: kbdBacklightCard
        Layout.fillWidth: true
        pad: 16
        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            Icon { name: "keyboard"; size: 16; color: Theme.muted }
            Txt { Layout.fillWidth: true; text: "Подсветка клавиатуры"; font.pixelSize: 15; font.weight: Font.DemiBold }
            Chip {
                kind: !!(d.backlight && d.backlight.length > 0) ? "ok" : "no"
                text: !!(d.backlight && d.backlight.length > 0) ? "Видна системе" : "Недоступно"
            }
        }
        Txt {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            color: Theme.muted
            font.pixelSize: 12
            visible: !!(d.backlight && d.backlight.length > 0)
            text: "Система видит подсветку (" + (d.backlight ? d.backlight.join(", ") : "") + "). Управление из DOCKIT появится позже."
        }
        Txt {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            color: Theme.muted
            font.pixelSize: 12
            visible: !!(!d.backlight || d.backlight.length === 0)
            text: "Подсветка клавиатуры не видна через стандартный интерфейс ядра — используйте клавиши Fn ноутбука."
        }
    }
}
