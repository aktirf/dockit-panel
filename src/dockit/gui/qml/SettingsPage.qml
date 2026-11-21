import QtQuick
import QtQuick.Layouts

PageFrame {
    id: settingsPage
    title: Theme.tr("settings_title")
    subtitle: Theme.tr("settings_sub")

    // Language switcher (instant live switch)
    Card {
        id: languageCard
        Layout.fillWidth: true
        Txt { text: Theme.tr("language_card"); font.pixelSize: 16; font.weight: Font.DemiBold }
        Txt {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            color: Theme.muted
            font.pixelSize: 13
            text: Theme.tr("language_desc")
        }
        SegmentBar {
            current: d.settings && d.settings.lang ? String(d.settings.lang) : "auto"
            options: [
                { id: "auto", label: Theme.tr("lang_auto"), tip: "" },
                { id: "ru", label: "Русский", tip: "" },
                { id: "en", label: "English", tip: "" },
                { id: "uk", label: "Українська", tip: "" }
            ]
            onPicked: function (val) { backend.setLang(val) }
        }
    }

    // Refresh & Overheat
    Card {
        Layout.fillWidth: true
        Txt { text: Theme.tr("monitoring_card"); font.pixelSize: 16; font.weight: Font.DemiBold }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 6
            Txt { text: Theme.tr("refresh_interval"); color: Theme.soft; font.pixelSize: 13 }
            SegmentBar {
                current: String(backend.interval)
                options: [
                    { id: "1", label: "1 " + Theme.tr("unit_s"), tip: Theme.tr("interval_1_tip") },
                    { id: "3", label: "3 " + Theme.tr("unit_s"), tip: Theme.tr("interval_3_tip") },
                    { id: "5", label: "5 " + Theme.tr("unit_s"), tip: Theme.tr("interval_5_tip") },
                    { id: "10", label: "10 " + Theme.tr("unit_s"), tip: Theme.tr("interval_10_tip") }
                ]
                onPicked: function (val) { backend.setInterval(Number(val)) }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 6
            Txt { text: Theme.tr("overheat_warn"); color: Theme.soft; font.pixelSize: 13 }
            SegmentBar {
                current: d.settings && d.settings.warn_temp !== undefined ? String(d.settings.warn_temp) : "90"
                options: [
                    { id: "0", label: Theme.tr("off_word"), tip: Theme.tr("off_warn_tip") },
                    { id: "80", label: "80 °C", tip: "" },
                    { id: "85", label: "85 °C", tip: "" },
                    { id: "90", label: "90 °C", tip: "" },
                    { id: "95", label: "95 °C", tip: "" }
                ]
                onPicked: function (val) { backend.setWarnTemp(Number(val)) }
            }
        }
    }

    // Window & startup behavior
    Card {
        Layout.fillWidth: true
        Txt { text: Theme.tr("window_card"); font.pixelSize: 16; font.weight: Font.DemiBold }
        ToggleCard {
            Layout.fillWidth: true
            icon: "pulse"
            label: Theme.tr("notifications")
            tip: Theme.tr("notifications_tip")
            on: d.settings ? d.settings.notify === true : false
            can: d.settings ? d.settings.notifyAvailable === true : false
            onToggled: backend.setNotify(!on)
        }
        ToggleCard {
            Layout.fillWidth: true
            icon: "zap"
            label: Theme.tr("autostart")
            tip: Theme.tr("autostart_tip")
            on: d.settings ? d.settings.autostart === true : false
            onToggled: backend.setAutostart(!on)
        }
        ToggleCard {
            Layout.fillWidth: true
            icon: "layers"
            label: Theme.tr("tray_setting")
            tip: Theme.tr("tray_tip")
            on: d.settings ? d.settings.tray === true : false
            can: d.settings ? d.settings.trayAvailable === true : false
            onToggled: backend.setTray(!on)
        }
        ToggleCard {
            Layout.fillWidth: true
            icon: "sliders"
            label: Theme.tr("compact_nav")
            tip: Theme.tr("compact_nav_tip")
            on: d.settings ? d.settings.compact_nav === true : false
            onToggled: backend.setCompactNav(!on)
        }
    }

    // Accent color picker
    Card {
        id: accentCard
        Layout.fillWidth: true
        Txt { text: Theme.tr("accent_card"); font.pixelSize: 16; font.weight: Font.DemiBold }
        Txt {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            color: Theme.muted
            font.pixelSize: 13
            text: Theme.tr("accent_desc")
        }
        Flow {
            Layout.fillWidth: true
            spacing: 8
            Repeater {
                model: [
                    { id: "blue", key: "accent_blue", hex: "#5AB0FF" },
                    { id: "mint", key: "accent_mint", hex: "#4CC38A" },
                    { id: "purple", key: "accent_purple", hex: "#A78BFA" },
                    { id: "amber", key: "accent_amber", hex: "#F5B942" },
                    { id: "coral", key: "accent_coral", hex: "#FF7A7A" }
                ]
                delegate: Rectangle {
                    readonly property bool sel: !!(d.settings && (d.settings.accent || "blue") === modelData.id)
                    height: 36
                    width: accentRow.implicitWidth + 24
                    radius: 18
                    color: sel ? Theme.navActive : (accHover.hovered ? Theme.cardInner : Theme.btn)
                    border.width: 1
                    border.color: sel ? modelData.hex : (accHover.hovered ? modelData.hex : Theme.border3)
                    scale: accMouse.pressed ? 0.95 : 1.0
                    Behavior on color { ColorAnimation { duration: 150; easing.type: Easing.OutCubic } }
                    Behavior on border.color { ColorAnimation { duration: 150; easing.type: Easing.OutCubic } }
                    Behavior on scale { NumberAnimation { duration: 100; easing.type: Easing.OutCubic } }
                    HoverHandler { id: accHover }
                    RowLayout {
                        id: accentRow
                        anchors.centerIn: parent
                        spacing: 8
                        Rectangle { width: 10; height: 10; radius: 5; color: modelData.hex }
                        Txt { text: Theme.tr(modelData.key); font.pixelSize: 13; color: sel ? "#FFFFFF" : Theme.soft }
                    }
                    MouseArea {
                        id: accMouse
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: backend.setAccent(modelData.id)
                    }
                }
            }
        }
    }

    // About card
    Card {
        Layout.fillWidth: true
        GridLayout {
            Layout.fillWidth: true
            columns: settingsPage.width >= 600 ? 2 : 1
            columnSpacing: 14
            rowSpacing: 10
            RowLayout {
                Layout.fillWidth: true
                Layout.minimumWidth: 0
                spacing: 14
                Rectangle {
                    implicitWidth: 44
                    implicitHeight: 44
                    radius: 12
                    color: "#1B2A3A"
                    Icon { anchors.centerIn: parent; name: "gauge"; size: 22; color: Theme.accent }
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.minimumWidth: 0
                    spacing: 2
                    Txt { Layout.fillWidth: true; elide: Text.ElideRight; text: "DOCKIT " + backend.version + " (" + Theme.tr("beta_tag") + ")"; font.pixelSize: 16; font.weight: Font.DemiBold }
                    Txt { Layout.fillWidth: true; elide: Text.ElideRight; text: "GPL-3.0-or-later · github.com/aktirf/dockit-panel"; color: Theme.muted; font.pixelSize: 12 }
                }
            }
            RowLayout {
                Layout.alignment: settingsPage.width >= 600 ? Qt.AlignRight | Qt.AlignVCenter : Qt.AlignLeft
                spacing: 8
                Btn {
                    text: Theme.tr("welcome_recheck_btn")
                    implicitHeight: 34
                    tip: Theme.tr("welcome_recheck_tip")
                    onClicked: backend.openWelcome()
                }
                Btn {
                    text: Theme.tr("copy_report")
                    implicitHeight: 34
                    onClicked: backend.copyReport()
                }
            }
        }
        Txt {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            color: Theme.muted
            font.pixelSize: 12
            text: Theme.tr("about_desc")
        }
    }
}
