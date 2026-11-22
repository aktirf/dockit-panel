import QtQuick
import QtQuick.Layouts
import QtQuick.Controls

Rectangle {
    id: welcomeRoot
    property var d: ({})
    property int step: 0   // 0 = Welcome & Theme, 1 = Hardware Check, 2 = Quick Setup
    signal done(string nextPage)

    readonly property var w: (d && d.welcome) ? d.welcome : ({})
    readonly property var workingList: (w && w.working) ? w.working : []
    readonly property var setupList: (w && w.needsSetup) ? w.needsSetup : []
    readonly property var unavailList: (w && w.unavailable) ? w.unavailable : []
    readonly property int sidePad: width < 560 ? 16 : 36

    color: Theme.bg

    function goStep(n) {
        var clamped = Math.max(0, Math.min(2, n))
        if (step !== clamped) {
            step = clamped
            welcomeFlick.contentY = 0
            stepAnim.restart()
        }
    }

    onVisibleChanged: {
        if (visible) {
            step = (backend && backend.welcomeStep !== undefined) ? Number(backend.welcomeStep) : 0
            welcomeFlick.contentY = 0
            stepAnim.restart()
        }
    }

    ParallelAnimation {
        id: stepAnim
        NumberAnimation { target: stepContainer; property: "opacity"; from: 0.0; to: 1.0; duration: 220; easing.type: Easing.OutCubic }
        NumberAnimation { target: stepSlide; property: "y"; from: 10; to: 0; duration: 240; easing.type: Easing.OutCubic }
    }

    Flickable {
        id: welcomeFlick
        anchors.fill: parent
        clip: true
        contentWidth: width
        contentHeight: welcomeCol.implicitHeight + 76
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: ScrollBar {}

        ColumnLayout {
            id: welcomeCol
            width: Math.min(Math.max(260, welcomeRoot.width - welcomeRoot.sidePad * 2), 920)
            x: Math.max(welcomeRoot.sidePad, (welcomeRoot.width - width) / 2)
            y: 28
            spacing: 20

            // Top wizard stepper + Skip button
            RowLayout {
                Layout.fillWidth: true
                spacing: 10

                Flow {
                    Layout.fillWidth: true
                    Layout.minimumWidth: 0
                    spacing: 8
                    Repeater {
                        model: [
                            { idx: 0, key: "wizard_step_1" },
                            { idx: 1, key: "wizard_step_2" },
                            { idx: 2, key: "wizard_step_3" }
                        ]
                        delegate: Rectangle {
                            id: stepPill
                            readonly property bool active: welcomeRoot.step === modelData.idx
                            readonly property bool passed: welcomeRoot.step > modelData.idx
                            height: 34
                            width: stepPillRow.implicitWidth + 24
                            radius: 17
                            color: active
                                   ? Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.18)
                                   : (stepHover.hovered ? Theme.cardInner : Theme.card)
                            border.width: 1
                            border.color: active ? Theme.accent : (passed ? Qt.rgba(0.298, 0.765, 0.541, 0.45) : Theme.border2)
                            Behavior on color { ColorAnimation { duration: 160 } }
                            Behavior on border.color { ColorAnimation { duration: 160 } }
                            HoverHandler { id: stepHover }
                            Row {
                                id: stepPillRow
                                anchors.centerIn: parent
                                spacing: 7
                                Rectangle {
                                    width: 18; height: 18; radius: 9
                                    anchors.verticalCenter: parent.verticalCenter
                                    color: stepPill.active ? Theme.accent : (stepPill.passed ? Theme.ok : Theme.btn)
                                    Txt {
                                        anchors.centerIn: parent
                                        text: stepPill.passed ? "✓" : String(modelData.idx + 1)
                                        font.pixelSize: 11
                                        font.weight: Font.DemiBold
                                        color: (stepPill.active || stepPill.passed) ? "#0B1218" : Theme.soft
                                    }
                                }
                                Txt {
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: Theme.tr(modelData.key)
                                    font.pixelSize: 13
                                    font.weight: stepPill.active ? Font.DemiBold : Font.Medium
                                    color: stepPill.active ? "#FFFFFF" : Theme.soft
                                }
                            }
                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: welcomeRoot.goStep(modelData.idx)
                            }
                        }
                    }
                }

                Btn {
                    implicitHeight: 34
                    text: Theme.tr("wizard_skip")
                    onClicked: welcomeRoot.done("overview")
                }
            }

            // Animated step container
            ColumnLayout {
                id: stepContainer
                Layout.fillWidth: true
                spacing: 18
                transform: Translate { id: stepSlide; y: 0 }

                // ==================== STEP 0: WELCOME & APPEARANCE ====================
                ColumnLayout {
                    visible: welcomeRoot.step === 0
                    Layout.fillWidth: true
                    spacing: 18

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: helloBox.implicitHeight + 48
                        radius: 20
                        border.width: 1
                        border.color: Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.34)
                        gradient: Gradient {
                            orientation: Gradient.Horizontal
                            GradientStop { position: 0.0; color: Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.20) }
                            GradientStop { position: 0.65; color: Theme.card }
                            GradientStop { position: 1.0; color: Theme.card }
                        }

                        ColumnLayout {
                            id: helloBox
                            anchors.fill: parent
                            anchors.margins: 24
                            spacing: 12

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 16
                                Rectangle {
                                    implicitWidth: 54
                                    implicitHeight: 54
                                    radius: 16
                                    color: Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.20)
                                    border.width: 1
                                    border.color: Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.42)
                                    Icon { anchors.centerIn: parent; name: "gauge"; size: 28; color: Theme.accent }
                                }
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    Layout.minimumWidth: 0
                                    spacing: 4
                                    Txt {
                                        Layout.fillWidth: true
                                        wrapMode: Text.WordWrap
                                        text: Theme.tr("wizard_hello_title")
                                        font.pixelSize: welcomeRoot.width < 560 ? 22 : 28
                                        font.weight: Font.DemiBold
                                    }
                                    Txt {
                                        Layout.fillWidth: true
                                        wrapMode: Text.WordWrap
                                        text: Theme.tr("wizard_hello_sub")
                                        color: Theme.soft
                                        font.pixelSize: 14
                                    }
                                }
                            }
                        }
                    }

                    // Live language picker
                    Card {
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

                    // Live accent color picker
                    Card {
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
                                    height: 38
                                    width: wizAccRow.implicitWidth + 24
                                    radius: 19
                                    color: sel ? Theme.navActive : (wizAccHover.hovered ? Theme.cardInner : Theme.btn)
                                    border.width: 1
                                    border.color: sel ? modelData.hex : (wizAccHover.hovered ? modelData.hex : Theme.border3)
                                    scale: wizAccMouse.pressed ? 0.95 : 1.0
                                    Behavior on color { ColorAnimation { duration: 150; easing.type: Easing.OutCubic } }
                                    Behavior on border.color { ColorAnimation { duration: 150; easing.type: Easing.OutCubic } }
                                    Behavior on scale { NumberAnimation { duration: 100; easing.type: Easing.OutCubic } }
                                    HoverHandler { id: wizAccHover }
                                    RowLayout {
                                        id: wizAccRow
                                        anchors.centerIn: parent
                                        spacing: 8
                                        Rectangle { width: 10; height: 10; radius: 5; color: modelData.hex }
                                        Txt { text: Theme.tr(modelData.key); font.pixelSize: 13; color: sel ? "#FFFFFF" : Theme.soft }
                                    }
                                    MouseArea {
                                        id: wizAccMouse
                                        anchors.fill: parent
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: backend.setAccent(modelData.id)
                                    }
                                }
                            }
                        }
                    }
                }

                // ==================== STEP 1: HARDWARE COMPATIBILITY SCAN ====================
                ColumnLayout {
                    visible: welcomeRoot.step === 1
                    Layout.fillWidth: true
                    spacing: 18

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: heroBox.implicitHeight + 40
                        radius: 20
                        border.width: 1
                        border.color: Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.30)
                        gradient: Gradient {
                            orientation: Gradient.Horizontal
                            GradientStop { position: 0.0; color: Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.16) }
                            GradientStop { position: 0.6; color: Theme.card }
                            GradientStop { position: 1.0; color: Theme.card }
                        }

                        ColumnLayout {
                            id: heroBox
                            anchors.fill: parent
                            anchors.margins: 20
                            spacing: 14

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 14
                                Rectangle {
                                    implicitWidth: 46
                                    implicitHeight: 46
                                    radius: 13
                                    color: Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.18)
                                    border.width: 1
                                    border.color: Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.38)
                                    Icon { anchors.centerIn: parent; name: "pulse"; size: 22; color: Theme.accent }
                                }
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    Layout.minimumWidth: 0
                                    spacing: 3
                                    Txt {
                                        Layout.fillWidth: true
                                        wrapMode: Text.WordWrap
                                        text: Theme.tr("welcome_title")
                                        font.pixelSize: welcomeRoot.width < 560 ? 20 : 24
                                        font.weight: Font.DemiBold
                                    }
                                    Txt {
                                        Layout.fillWidth: true
                                        wrapMode: Text.WordWrap
                                        text: Theme.tr("welcome_sub")
                                        color: Theme.muted
                                        font.pixelSize: 13
                                    }
                                }
                            }

                            Flow {
                                visible: !!(d && d.ready)
                                Layout.fillWidth: true
                                spacing: 8
                                Chip {
                                    big: true
                                    kind: "info"
                                    icon: (welcomeRoot.w.formFactor === "desktop") ? "monitor" : "layers"
                                    text: String(welcomeRoot.w.formLabel || "") + (welcomeRoot.w.model ? (" · " + String(welcomeRoot.w.model)) : "")
                                }
                                Chip {
                                    big: true
                                    kind: "info"
                                    icon: "cpu"
                                    text: String(welcomeRoot.w.cpu || welcomeRoot.w.cpuVendorLabel || "CPU")
                                }
                                Chip {
                                    big: true
                                    kind: "info"
                                    icon: "monitor"
                                    text: String(welcomeRoot.w.gpu || "")
                                }
                                Chip {
                                    big: true
                                    kind: "ok"
                                    icon: "grid"
                                    text: String(welcomeRoot.w.desktop || "Linux") + (welcomeRoot.w.kernel ? (" · " + String(welcomeRoot.w.kernel)) : "")
                                }
                            }
                        }
                    }

                    Card {
                        visible: !(d && d.ready)
                        Layout.fillWidth: true
                        Txt {
                            Layout.fillWidth: true
                            horizontalAlignment: Text.AlignHCenter
                            text: Theme.tr("welcome_scanning")
                            color: Theme.muted
                            font.pixelSize: 15
                        }
                    }

                    Card {
                        visible: !!(d && d.ready) && welcomeRoot.workingList.length > 0
                        Layout.fillWidth: true
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Icon { name: "check"; size: 17; color: Theme.ok }
                            Txt {
                                Layout.fillWidth: true
                                text: Theme.tr("welcome_working_title").replace("{n}", String(welcomeRoot.workingList.length))
                                font.pixelSize: 16
                                font.weight: Font.DemiBold
                            }
                        }
                        GridLayout {
                            Layout.fillWidth: true
                            columns: welcomeCol.width >= 660 ? 2 : 1
                            columnSpacing: 10
                            rowSpacing: 10
                            Repeater {
                                model: welcomeRoot.workingList
                                delegate: Rectangle {
                                    Layout.fillWidth: true
                                    Layout.minimumWidth: 0
                                    implicitHeight: wkRow.implicitHeight + 20
                                    radius: 11
                                    color: Theme.cardInner
                                    border.width: 1
                                    border.color: Qt.rgba(0.298, 0.765, 0.541, 0.28)
                                    RowLayout {
                                        id: wkRow
                                        anchors.fill: parent
                                        anchors.margins: 10
                                        spacing: 10
                                        Rectangle {
                                            implicitWidth: 30
                                            implicitHeight: 30
                                            radius: 8
                                            color: Qt.rgba(0.298, 0.765, 0.541, 0.14)
                                            Icon { anchors.centerIn: parent; name: String(modelData.icon || "check"); size: 15; color: Theme.ok }
                                        }
                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            Layout.minimumWidth: 0
                                            spacing: 2
                                            Txt { Layout.fillWidth: true; elide: Text.ElideRight; text: String(modelData.title || ""); font.pixelSize: 13; font.weight: Font.DemiBold }
                                            Txt { Layout.fillWidth: true; wrapMode: Text.WordWrap; text: String(modelData.detail || ""); color: Theme.muted; font.pixelSize: 12 }
                                        }
                                    }
                                }
                            }
                        }
                    }

                    Card {
                        visible: !!(d && d.ready) && welcomeRoot.setupList.length > 0
                        Layout.fillWidth: true
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Icon { name: "wrench"; size: 17; color: Theme.warn }
                            Txt {
                                Layout.fillWidth: true
                                text: Theme.tr("welcome_setup_title").replace("{n}", String(welcomeRoot.setupList.length))
                                font.pixelSize: 16
                                font.weight: Font.DemiBold
                            }
                        }
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 8
                            Repeater {
                                model: welcomeRoot.setupList
                                delegate: Rectangle {
                                    Layout.fillWidth: true
                                    Layout.minimumWidth: 0
                                    implicitHeight: stCol.implicitHeight + 20
                                    radius: 11
                                    color: Theme.cardInner
                                    border.width: 1
                                    border.color: Qt.rgba(0.961, 0.725, 0.259, 0.30)
                                    ColumnLayout {
                                        id: stCol
                                        anchors.fill: parent
                                        anchors.margins: 10
                                        spacing: 4
                                        RowLayout {
                                            Layout.fillWidth: true
                                            spacing: 10
                                            Icon { name: String(modelData.icon || "wrench"); size: 15; color: Theme.warn }
                                            Txt { Layout.fillWidth: true; elide: Text.ElideRight; text: String(modelData.title || ""); font.pixelSize: 13; font.weight: Font.DemiBold }
                                        }
                                        Txt { Layout.fillWidth: true; wrapMode: Text.WordWrap; text: String(modelData.detail || ""); color: Theme.soft; font.pixelSize: 12 }
                                        Txt {
                                            visible: !!(modelData.hint && String(modelData.hint) !== "")
                                            Layout.fillWidth: true
                                            wrapMode: Text.WordWrap
                                            text: Theme.tr("how_to_fix") + String(modelData.hint || "")
                                            color: Theme.warn
                                            font.pixelSize: 12
                                        }
                                    }
                                }
                            }
                        }
                    }

                    Card {
                        visible: !!(d && d.ready) && welcomeRoot.unavailList.length > 0
                        Layout.fillWidth: true
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Icon { name: "x"; size: 16; color: Theme.muted }
                            Txt {
                                Layout.fillWidth: true
                                text: Theme.tr("welcome_unavail_title").replace("{n}", String(welcomeRoot.unavailList.length))
                                font.pixelSize: 16
                                font.weight: Font.DemiBold
                            }
                            Btn {
                                implicitHeight: 30
                                text: Theme.tr("report_github_btn")
                                tip: Theme.tr("report_github_tip")
                                onClicked: backend.openIssue("device")
                            }
                        }
                        GridLayout {
                            Layout.fillWidth: true
                            columns: welcomeCol.width >= 660 ? 2 : 1
                            columnSpacing: 10
                            rowSpacing: 10
                            Repeater {
                                model: welcomeRoot.unavailList
                                delegate: Rectangle {
                                    Layout.fillWidth: true
                                    Layout.minimumWidth: 0
                                    implicitHeight: unRow.implicitHeight + 20
                                    radius: 11
                                    color: Theme.cardInner
                                    border.width: 1
                                    border.color: Theme.border2
                                    RowLayout {
                                        id: unRow
                                        anchors.fill: parent
                                        anchors.margins: 10
                                        spacing: 10
                                        Rectangle {
                                            implicitWidth: 30
                                            implicitHeight: 30
                                            radius: 8
                                            color: Theme.card
                                            Icon { anchors.centerIn: parent; name: String(modelData.icon || "x"); size: 15; color: Theme.muted }
                                        }
                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            Layout.minimumWidth: 0
                                            spacing: 2
                                            Txt { Layout.fillWidth: true; elide: Text.ElideRight; text: String(modelData.title || ""); font.pixelSize: 13; font.weight: Font.Medium; color: Theme.soft }
                                            Txt { Layout.fillWidth: true; wrapMode: Text.WordWrap; text: String(modelData.detail || ""); color: Theme.muted; font.pixelSize: 12 }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                // ==================== STEP 2: QUICK PREFERENCES ====================
                ColumnLayout {
                    visible: welcomeRoot.step === 2
                    Layout.fillWidth: true
                    spacing: 18

                    Card {
                        Layout.fillWidth: true
                        Txt {
                            Layout.fillWidth: true
                            wrapMode: Text.WordWrap
                            text: Theme.tr("wizard_prefs_title")
                            font.pixelSize: 20
                            font.weight: Font.DemiBold
                        }
                        Txt {
                            Layout.fillWidth: true
                            wrapMode: Text.WordWrap
                            text: Theme.tr("wizard_prefs_sub")
                            color: Theme.muted
                            font.pixelSize: 13
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
                            icon: "zap"
                            label: Theme.tr("autostart")
                            tip: Theme.tr("autostart_tip")
                            on: d.settings ? d.settings.autostart === true : false
                            onToggled: backend.setAutostart(!on)
                        }
                        ToggleCard {
                            Layout.fillWidth: true
                            icon: "pulse"
                            label: Theme.tr("notifications")
                            tip: Theme.tr("notifications_tip")
                            on: d.settings ? d.settings.notify === true : false
                            can: d.settings ? d.settings.notifyAvailable === true : false
                            onToggled: backend.setNotify(!on)
                        }

                        Txt {
                            Layout.fillWidth: true
                            wrapMode: Text.WordWrap
                            color: Theme.okText
                            font.pixelSize: 13
                            text: Theme.tr("wizard_prefs_note")
                        }
                    }
                }
            }

            // Wizard navigation footer
            RowLayout {
                Layout.fillWidth: true
                spacing: 12
                Btn {
                    visible: welcomeRoot.step > 0
                    implicitHeight: 42
                    text: "← " + Theme.tr("wizard_back")
                    onClicked: welcomeRoot.goStep(welcomeRoot.step - 1)
                }
                Item { Layout.fillWidth: true }
                Btn {
                    visible: welcomeRoot.step === 2 && (welcomeRoot.setupList.length > 0 || welcomeRoot.unavailList.length > 0)
                    implicitHeight: 42
                    text: Theme.tr("welcome_open_diag_btn")
                    onClicked: welcomeRoot.done("diagnostics")
                }
                Btn {
                    primary: true
                    implicitHeight: 42
                    text: welcomeRoot.step < 2 ? (Theme.tr("wizard_next") + " →") : Theme.tr("welcome_start_btn")
                    onClicked: {
                        if (welcomeRoot.step < 2)
                            welcomeRoot.goStep(welcomeRoot.step + 1)
                        else
                            welcomeRoot.done("overview")
                    }
                }
            }
        }
    }
}
