import QtQuick
import QtQuick.Layouts
import QtQuick.Controls

PageFrame {
    id: periphPage
    title: Theme.tr("periph_title")
    subtitle: Theme.tr("periph_sub")

    SyncModel { id: periphModel }
    SyncModel { id: btModel }
    SyncModel { id: periphBatModel }
    function syncAll() {
        periphModel.sync(d.peripherals)
        btModel.sync(d.bluetooth)
        periphBatModel.sync(d.periphBatteries)
    }
    Connections { target: backend; function onStateChanged() { syncAll() } }
    Component.onCompleted: syncAll()

    function audioItems(arr) {
        return (arr ? arr : []).map(function (t) { return { id: String(t), label: String(t) } })
    }
    function deviceIcon(kindText) {
        var k = String(kindText || "").toLowerCase()
        if (k.indexOf("мыш") >= 0 || k.indexOf("миш") >= 0 || k.indexOf("mouse") >= 0) return "mouse"
        if (k.indexOf("клав") >= 0 || k.indexOf("key") >= 0) return "keyboard"
        if (k.indexOf("кам") >= 0 || k.indexOf("cam") >= 0) return "camera"
        if (k.indexOf("гарн") >= 0 || k.indexOf("науш") >= 0 || k.indexOf("навуш") >= 0 || k.indexOf("head") >= 0) return "headphones"
        if (k.indexOf("bluetooth") >= 0) return "bluetooth"
        return "app"
    }

    readonly property bool audioMuted: !!(d.audio && d.audio.outputMuted === true)
    readonly property bool hasVolume: !!(d.audio && d.audio.outputVolume !== undefined && d.audio.outputVolume !== null && Number(d.audio.outputVolume) >= 0)

    readonly property var kbd: d.kbdBacklight || ({})
    readonly property bool kbdAvailable: !!(kbd && kbd.available === true)
    readonly property bool kbdCan: !!(kbd && kbd.can === true)
    readonly property bool kbdRgb: !!(kbd && kbd.rgb === true)
    readonly property bool kbdAuto: !!(kbd && kbd.autonomous === true)
    readonly property bool kbdOn: !!(kbd && kbd.on === true)
    readonly property int kbdBright: kbd && kbd.brightness !== undefined ? Number(kbd.brightness) : 100
    readonly property string kbdColor: kbd && kbd.color ? String(kbd.color) : "#5AB0FF"
    readonly property string kbdDevice: kbd && kbd.deviceName ? String(kbd.deviceName) : ""
    readonly property var kbdPalette: [
        "#FFFFFF", "#FFE0A3", "#FF0000", "#FF5500", "#FFD000", "#00FF00",
        "#00E58A", "#00E5FF", "#3B82F6", "#0033FF", "#9333EA", "#FF0099"
    ]

    function applyKbd(on, bright, color, autoMode) {
        if (!kbdCan) return
        backend.setKbdBacklight(!!on, Math.max(0, Math.min(100, Math.round(Number(bright)))), String(color || kbdColor), !!autoMode)
    }

    onKbdColorChanged: {
        if (kbdHexInput && !kbdHexInput.activeFocus)
            kbdHexInput.text = kbdColor
    }

    // 1. Sound card
    Card {
        id: soundCard
        Layout.fillWidth: true
        RowLayout {
            Layout.fillWidth: true
            Icon { name: periphPage.audioMuted ? "volumeMute" : "speaker"; size: 17; color: periphPage.audioMuted ? Theme.err : Theme.accent }
            Txt { Layout.fillWidth: true; text: Theme.tr("sound"); font.pixelSize: 16; font.weight: Font.DemiBold }
            Txt {
                visible: periphPage.hasVolume
                text: periphPage.audioMuted ? Theme.tr("muted") : (volSlider.displayValue + " %")
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
                Tip { text: periphPage.audioMuted ? Theme.tr("unmute_tip") : Theme.tr("mute_tip") }
            }
            SmoothSlider {
                id: volSlider
                from: 0
                to: 150
                targetValue: periphPage.hasVolume ? Number(d.audio.outputVolume) : 50
                fillColor: periphPage.audioMuted ? Theme.muted : (volSlider.displayValue > 100 ? Theme.warn : Theme.accent)
                handleColor: periphPage.audioMuted ? Theme.muted : Theme.accent
                onCommitted: function (val) { backend.setVolume(val) }
            }
        }

        GridLayout {
            Layout.fillWidth: true
            columns: periphPage.width >= 660 ? 2 : 1
            columnSpacing: 14
            rowSpacing: 12

            ColumnLayout {
                Layout.fillWidth: true
                Layout.minimumWidth: 0
                spacing: 6
                Txt { text: Theme.tr("sound_output"); color: Theme.soft; font.pixelSize: 13 }
                SelectBox {
                    id: periphOutSelect
                    items: periphPage.audioItems(d.audio ? d.audio.outputs : [])
                    currentId: d.audio && d.audio.outputDefault ? String(d.audio.outputDefault) : ""
                    placeholder: Theme.tr("sound_output_none")
                    onPicked: function (val) { backend.setAudio("output", val) }
                }
            }
            ColumnLayout {
                Layout.fillWidth: true
                Layout.minimumWidth: 0
                spacing: 6
                Txt { text: Theme.tr("microphone"); color: Theme.soft; font.pixelSize: 13 }
                SelectBox {
                    id: periphInSelect
                    items: periphPage.audioItems(d.audio ? d.audio.inputs : [])
                    currentId: d.audio && d.audio.inputDefault ? String(d.audio.inputDefault) : ""
                    placeholder: Theme.tr("mic_none")
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
                text: Theme.tr("audio_profiles_hint")
            }
            Btn { text: Theme.tr("nav_profiles"); implicitHeight: 34; onClicked: goto("profiles") }
        }
    }

    // 2. Keyboard backlight (HID LampArray RGB + kernel LED)
    Card {
        id: kbdBacklightCard
        Layout.fillWidth: true
        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            Icon {
                name: "keyboard"
                size: 17
                color: periphPage.kbdAvailable ? (periphPage.kbdRgb && periphPage.kbdOn && !periphPage.kbdAuto ? periphPage.kbdColor : Theme.accent) : Theme.muted
            }
            ColumnLayout {
                Layout.fillWidth: true
                Layout.minimumWidth: 0
                spacing: 1
                Txt { Layout.fillWidth: true; elide: Text.ElideRight; text: Theme.tr("kbd_backlight"); font.pixelSize: 16; font.weight: Font.DemiBold }
                Txt {
                    visible: periphPage.kbdAvailable && periphPage.kbdDevice !== ""
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                    color: Theme.muted
                    font.pixelSize: 12
                    text: periphPage.kbdDevice + (periphPage.kbdRgb ? " · HID LampArray" : " · LED")
                }
            }
            Chip {
                visible: !periphPage.kbdAvailable
                kind: "no"
                text: Theme.tr("status_no")
            }
            Chip {
                visible: periphPage.kbdAvailable
                kind: periphPage.kbdAuto ? "setup" : (periphPage.kbdOn ? "ok" : "no")
                text: periphPage.kbdAuto ? Theme.tr("kbd_auto_chip") : (periphPage.kbdRgb ? "RGB" : "LED")
                tip: periphPage.kbdRgb ? Theme.tr("kbd_lamparray_tip") : Theme.tr("kbd_led_tip")
            }
            Btn {
                id: kbdPowerBtn
                visible: periphPage.kbdAvailable && !periphPage.kbdAuto
                enabled: periphPage.kbdCan
                implicitHeight: 34
                primary: periphPage.kbdOn
                text: periphPage.kbdOn ? Theme.tr("kbd_on") : Theme.tr("kbd_off")
                onClicked: {
                    var nextOn = !periphPage.kbdOn
                    var nextBright = nextOn ? (periphPage.kbdBright > 0 ? periphPage.kbdBright : 100) : periphPage.kbdBright
                    periphPage.applyKbd(nextOn, nextBright, periphPage.kbdColor, false)
                }
            }
        }

        // Unavailable state
        Txt {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            color: Theme.muted
            font.pixelSize: 13
            visible: !periphPage.kbdAvailable
            text: Theme.tr("kbd_missing_text")
        }

        // Daemon not running hint
        Txt {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            color: Theme.warn
            font.pixelSize: 12
            visible: periphPage.kbdAvailable && !periphPage.kbdCan
            text: Theme.tr("kbd_need_service")
        }

        // Mode switcher: DOCKIT (color) vs Keyboard (Fn) — for LampArray RGB devices
        ColumnLayout {
            visible: periphPage.kbdAvailable && periphPage.kbdRgb
            Layout.fillWidth: true
            spacing: 6
            Txt {
                text: Theme.tr("kbd_mode")
                color: Theme.soft
                font.pixelSize: 13
            }
            SegmentBar {
                id: kbdModeBar
                enabled: periphPage.kbdCan
                opacity: periphPage.kbdCan ? 1.0 : 0.55
                options: [
                    { id: "dockit", label: Theme.tr("kbd_mode_dockit"), tip: Theme.tr("kbd_mode_tip") },
                    { id: "auto", label: Theme.tr("kbd_mode_auto"), tip: Theme.tr("kbd_mode_tip") }
                ]
                current: periphPage.kbdAuto ? "auto" : "dockit"
                onPicked: function (val) {
                    if (val === "auto")
                        periphPage.applyKbd(true, periphPage.kbdBright, periphPage.kbdColor, true)
                    else
                        periphPage.applyKbd(periphPage.kbdOn, periphPage.kbdBright > 0 ? periphPage.kbdBright : 100, periphPage.kbdColor, false)
                }
            }
        }

        // Autonomous mode explanation
        Txt {
            visible: periphPage.kbdAvailable && periphPage.kbdAuto
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            color: Theme.muted
            font.pixelSize: 12
            text: Theme.tr("kbd_auto_hint")
        }

        // Brightness slider (hidden in autonomous mode)
        ColumnLayout {
            visible: periphPage.kbdAvailable && !periphPage.kbdAuto
            Layout.fillWidth: true
            spacing: 6
            RowLayout {
                Layout.fillWidth: true
                Txt { Layout.fillWidth: true; text: Theme.tr("kbd_brightness"); color: Theme.soft; font.pixelSize: 13 }
                Txt {
                    text: kbdBrightSlider.displayValue + " %"
                    font.family: Theme.mono
                    font.pixelSize: 13
                    color: periphPage.kbdOn ? Theme.text : Theme.muted
                }
            }
            SmoothSlider {
                id: kbdBrightSlider
                enabled: periphPage.kbdCan
                from: 0
                to: 100
                targetValue: periphPage.kbdOn ? periphPage.kbdBright : 0
                fillColor: !periphPage.kbdOn ? Theme.muted : (periphPage.kbdRgb ? periphPage.kbdColor : Theme.accent)
                handleColor: !periphPage.kbdOn ? Theme.muted : (periphPage.kbdRgb ? periphPage.kbdColor : Theme.accent)
                onCommitted: function (val) {
                    periphPage.applyKbd(val > 0, val, periphPage.kbdColor, false)
                }
            }
        }

        // RGB color presets + custom HEX (LampArray only, when not autonomous)
        ColumnLayout {
            visible: periphPage.kbdAvailable && periphPage.kbdRgb && !periphPage.kbdAuto
            Layout.fillWidth: true
            spacing: 10
            RowLayout {
                Layout.fillWidth: true
                spacing: 10
                Txt { Layout.fillWidth: true; text: Theme.tr("kbd_color"); color: Theme.soft; font.pixelSize: 13 }
                Btn {
                    enabled: periphPage.kbdCan
                    implicitHeight: 30
                    text: Theme.tr("kbd_match_accent")
                    onClicked: {
                        var bright = periphPage.kbdBright > 0 ? periphPage.kbdBright : 100
                        periphPage.applyKbd(true, bright, String(backend.accentColor || "#5AB0FF"), false)
                    }
                }
            }
            Flow {
                Layout.fillWidth: true
                spacing: 10
                Repeater {
                    model: periphPage.kbdPalette
                    delegate: Rectangle {
                        id: swatchItem
                        required property string modelData
                        readonly property bool chosen: periphPage.kbdColor.toUpperCase() === modelData.toUpperCase()
                        implicitWidth: 32
                        implicitHeight: 32
                        radius: 16
                        color: modelData
                        border.width: chosen ? 3 : (swatchHover.hovered ? 2 : 1)
                        border.color: chosen ? "#FFFFFF" : (swatchHover.hovered ? Theme.soft : Theme.border3)
                        opacity: periphPage.kbdCan ? 1.0 : 0.45
                        HoverHandler { id: swatchHover }
                        MouseArea {
                            anchors.fill: parent
                            enabled: periphPage.kbdCan
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                var bright = periphPage.kbdBright > 0 ? periphPage.kbdBright : 100
                                periphPage.applyKbd(true, bright, swatchItem.modelData, false)
                            }
                        }
                        Tip { text: swatchItem.modelData }
                    }
                }
            }
            RowLayout {
                Layout.fillWidth: true
                spacing: 10
                Rectangle {
                    readonly property bool validHex: /^#[0-9a-fA-F]{6}$/.test(kbdHexInput.text.trim())
                    implicitWidth: 28
                    implicitHeight: 28
                    radius: 8
                    color: validHex ? kbdHexInput.text.trim() : periphPage.kbdColor
                    border.width: 1
                    border.color: Theme.border3
                }
                TextField {
                    id: kbdHexInput
                    enabled: periphPage.kbdCan
                    implicitWidth: 112
                    implicitHeight: 34
                    text: periphPage.kbdColor
                    placeholderText: "#5AB0FF"
                    font.family: Theme.mono
                    font.pixelSize: 13
                    color: Theme.text
                    placeholderTextColor: Theme.muted
                    maximumLength: 7
                    background: Rectangle {
                        radius: 9
                        color: Theme.cardInner
                        border.width: 1
                        border.color: kbdHexInput.activeFocus ? Theme.accent : Theme.border2
                    }
                    onAccepted: {
                        if (/^#[0-9a-fA-F]{6}$/.test(text.trim())) {
                            var bright = periphPage.kbdBright > 0 ? periphPage.kbdBright : 100
                            periphPage.applyKbd(true, bright, text.trim(), false)
                        }
                    }
                    Tip { text: Theme.tr("kbd_color_tip") }
                }
                Btn {
                    enabled: periphPage.kbdCan && /^#[0-9a-fA-F]{6}$/.test(kbdHexInput.text.trim())
                    implicitHeight: 34
                    text: Theme.tr("kbd_apply_color")
                    onClicked: {
                        var bright = periphPage.kbdBright > 0 ? periphPage.kbdBright : 100
                        periphPage.applyKbd(true, bright, kbdHexInput.text.trim(), false)
                    }
                }
                Item { Layout.fillWidth: true }
            }
        }
    }

    // 3. Peripheral batteries (UPower / sysfs HID++ / headsetcontrol / Bluetooth)
    Card {
        id: periphBatCard
        Layout.fillWidth: true
        RowLayout {
            Layout.fillWidth: true
            Icon { name: "battery"; size: 17; color: Theme.accent }
            Txt { Layout.fillWidth: true; text: Theme.tr("periph_bat_title"); font.pixelSize: 16; font.weight: Font.DemiBold }
            Chip {
                visible: periphBatModel.count > 0
                kind: "ok"
                text: Theme.tr("periph_bat_count").replace("{n}", String(periphBatModel.count))
                tip: Theme.tr("periph_bat_tip")
            }
            Chip {
                visible: periphBatModel.count === 0
                kind: "no"
                text: Theme.tr("no_data")
                tip: Theme.tr("periph_bat_tip")
            }
        }
        Txt {
            visible: periphBatModel.count === 0
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            color: Theme.muted
            font.pixelSize: 13
            text: Theme.tr("periph_bat_none")
        }
        GridLayout {
            visible: periphBatModel.count > 0
            Layout.fillWidth: true
            columns: periphPage.width >= 660 ? 2 : 1
            columnSpacing: 12
            rowSpacing: 10
            Repeater {
                model: periphBatModel
                delegate: Rectangle {
                    Layout.fillWidth: true
                    Layout.minimumWidth: 0
                    implicitHeight: pbatCol.implicitHeight + 22
                    radius: 12
                    color: Theme.cardInner
                    border.width: 1
                    border.color: Theme.border2
                    ColumnLayout {
                        id: pbatCol
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 8
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Rectangle {
                                implicitWidth: 32
                                implicitHeight: 32
                                radius: 9
                                color: Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.14)
                                Icon {
                                    anchors.centerIn: parent
                                    name: periphPage.deviceIcon(model.kind)
                                    size: 16
                                    color: Theme.accent
                                }
                            }
                            ColumnLayout {
                                Layout.fillWidth: true
                                Layout.minimumWidth: 0
                                spacing: 1
                                Txt {
                                    Layout.fillWidth: true
                                    Layout.minimumWidth: 0
                                    elide: Text.ElideRight
                                    text: String(model.name || "")
                                    font.weight: Font.Medium
                                }
                                Txt {
                                    Layout.fillWidth: true
                                    Layout.minimumWidth: 0
                                    elide: Text.ElideRight
                                    color: model.charging ? Theme.accent : Theme.muted
                                    font.pixelSize: 11
                                    text: {
                                        var parts = []
                                        if (model.source) parts.push(String(model.source))
                                        if (model.statusText) parts.push(String(model.statusText))
                                        return parts.join(" · ")
                                    }
                                }
                            }
                            Txt {
                                text: model.percent >= 0 ? (model.percent + " %") : (model.level ? String(model.level) : Theme.tr("bt_bat_unknown"))
                                font.family: Theme.mono
                                font.pixelSize: 14
                                font.weight: Font.DemiBold
                                color: model.charging ? Theme.accent : (model.percent >= 0 ? Theme.batteryColor(model.percent) : Theme.muted)
                            }
                        }
                        Bar {
                            visible: model.percent >= 0
                            Layout.fillWidth: true
                            value: model.percent >= 0 ? model.percent : 0
                            fill: model.charging ? Theme.accent : Theme.batteryColor(model.percent)
                        }
                    }
                }
            }
        }
    }

    // 4. Bluetooth devices with battery bars
    Card {
        Layout.fillWidth: true
        RowLayout {
            Layout.fillWidth: true
            Icon { name: "bluetooth"; size: 17; color: Theme.accent }
            Txt { Layout.fillWidth: true; text: Theme.tr("bt_devices"); font.pixelSize: 16; font.weight: Font.DemiBold }
            Chip {
                visible: btModel.count > 0
                kind: "ok"
                text: Theme.tr("bt_connected").replace("{n}", String(btModel.count))
            }
        }
        Txt {
            visible: btModel.count === 0
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            color: Theme.muted
            font.pixelSize: 13
            text: Theme.tr("bt_none")
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
                                text: model.battery >= 0 ? model.battery + " %" : Theme.tr("bt_bat_unknown")
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

    // 3. USB peripherals in 2-column grid
    Card {
        Layout.fillWidth: true
        RowLayout {
            Layout.fillWidth: true
            Icon { name: "mouse"; size: 17; color: Theme.accent }
            Txt { Layout.fillWidth: true; text: Theme.tr("usb_devices"); font.pixelSize: 16; font.weight: Font.DemiBold }
            Txt { text: periphModel.count > 0 ? String(periphModel.count) : ""; color: Theme.muted; font.family: Theme.mono; font.pixelSize: 13 }
        }
        Txt {
            visible: periphModel.count === 0
            text: Theme.tr("usb_none")
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
                                text: model.known ? Theme.tr("usb_known") : Theme.tr("usb_unknown")
                                tip: model.known ? Theme.tr("usb_known_tip") : Theme.tr("usb_unknown_tip")
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
}
