import QtQuick
import QtQuick.Layouts
import QtQuick.Controls

Rectangle {
    id: welcomeRoot
    property var d: ({})
    signal done(string nextPage)

    readonly property var w: (d && d.welcome) ? d.welcome : ({})
    readonly property var workingList: (w && w.working) ? w.working : []
    readonly property var setupList: (w && w.needsSetup) ? w.needsSetup : []
    readonly property var unavailList: (w && w.unavailable) ? w.unavailable : []
    readonly property int sidePad: width < 560 ? 16 : 36

    color: Theme.bg

    onVisibleChanged: {
        if (visible) enterAnim.restart()
    }
    ParallelAnimation {
        id: enterAnim
        NumberAnimation { target: welcomeFlick; property: "opacity"; from: 0.0; to: 1.0; duration: 240; easing.type: Easing.OutCubic }
        NumberAnimation { target: welcomeSlide; property: "y"; from: 12; to: 0; duration: 260; easing.type: Easing.OutCubic }
    }

    Flickable {
        id: welcomeFlick
        anchors.fill: parent
        transform: Translate { id: welcomeSlide; y: 0 }
        clip: true
        contentWidth: width
        contentHeight: welcomeCol.implicitHeight + 76
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: ScrollBar {}

        ColumnLayout {
            id: welcomeCol
            width: Math.min(Math.max(240, welcomeRoot.width - welcomeRoot.sidePad * 2), 920)
            x: Math.max(welcomeRoot.sidePad, (welcomeRoot.width - width) / 2)
            y: 32
            spacing: 20

            // Hero header
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
                            implicitWidth: 48
                            implicitHeight: 48
                            radius: 14
                            color: Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.18)
                            border.width: 1
                            border.color: Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.38)
                            Icon { anchors.centerIn: parent; name: "gauge"; size: 24; color: Theme.accent }
                        }
                        ColumnLayout {
                            Layout.fillWidth: true
                            Layout.minimumWidth: 0
                            spacing: 3
                            Txt {
                                Layout.fillWidth: true
                                wrapMode: Text.WordWrap
                                text: Theme.tr("welcome_title")
                                font.pixelSize: welcomeRoot.width < 560 ? 20 : 25
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

                    // Hardware identity chips
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

            // Scanning placeholder before first scan completes
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

            // 1. Working features
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

            // 2. Needs setup
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

            // 3. Not supported on this hardware
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

            // Action footer
            RowLayout {
                Layout.fillWidth: true
                spacing: 12
                Item { Layout.fillWidth: true }
                Btn {
                    visible: welcomeRoot.setupList.length > 0 || welcomeRoot.unavailList.length > 0
                    implicitHeight: 42
                    text: Theme.tr("welcome_open_diag_btn")
                    onClicked: welcomeRoot.done("diagnostics")
                }
                Btn {
                    primary: true
                    implicitHeight: 42
                    text: Theme.tr("welcome_start_btn")
                    onClicked: welcomeRoot.done("overview")
                }
            }
        }
    }
}
