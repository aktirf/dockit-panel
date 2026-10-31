import QtQuick
import QtQuick.Window
import QtQuick.Layouts
import QtQuick.Controls

Window {
    id: win
    width: 1280
    height: 900
    minimumWidth: 760
    minimumHeight: 520
    visible: true
    title: "DOCKIT"
    color: Theme.bg

    property string page: "overview"
    readonly property var d: backend.state
    readonly property int problems: d.features ? d.features.filter(function (f) { return f.status !== "ok" }).length : 0

    function modeName(id) {
        for (var i = 0; i < d.modes.length; i++)
            if (d.modes[i].id === id) return d.modes[i].name
        return "—"
    }
    function soon() { backend.say("Эта страница ещё в разработке") }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        // ---------- sidebar ----------
        Rectangle {
            Layout.preferredWidth: 240
            Layout.fillHeight: true
            color: Theme.panel

            Rectangle {
                width: 1
                height: parent.height
                anchors.right: parent.right
                color: Theme.border
            }

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 14
                anchors.topMargin: 24
                anchors.bottomMargin: 24
                spacing: 4

                RowLayout {
                    Layout.bottomMargin: 18
                    Layout.leftMargin: 10
                    spacing: 10
                    Rectangle {
                        implicitWidth: 34
                        implicitHeight: 34
                        radius: 10
                        color: "#1B2A3A"
                        Icon { anchors.centerIn: parent; name: "gauge"; size: 19; color: Theme.accent }
                    }
                    ColumnLayout {
                        spacing: 0
                        Txt { text: "DOCKIT"; font.pixelSize: 15; font.weight: Font.DemiBold }
                        Txt { text: d.model || "Ноутбук"; font.pixelSize: 12; color: Theme.muted }
                    }
                }

                NavItem { icon: "grid"; text: "Обзор"; active: win.page === "overview"; onClicked: win.page = "overview" }
                NavItem { icon: "gauge"; text: "Производительность"; ready: false; onClicked: win.soon() }
                NavItem { icon: "battery"; text: "Питание и батарея"; ready: false; onClicked: win.soon() }
                NavItem { icon: "fan"; text: "Охлаждение"; ready: false; onClicked: win.soon() }
                NavItem { icon: "sun"; text: "Подсветка"; ready: false; onClicked: win.soon() }
                NavItem { icon: "mouse"; text: "Периферия"; ready: false; onClicked: win.soon() }
                NavItem { icon: "layers"; text: "Профили"; active: win.page === "profiles"; onClicked: win.page = "profiles" }

                Item { Layout.fillHeight: true }

                NavItem { icon: "pulse"; text: "Диагностика"; badge: win.problems; ready: false; onClicked: win.soon() }
                NavItem { icon: "sliders"; text: "Настройки"; ready: false; onClicked: win.soon() }
            }
        }

        // ---------- content ----------
        ProfilesPage {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: win.page === "profiles"
            d: win.d
        }

        Flickable {
            id: flick
            visible: win.page === "overview"
            Layout.fillWidth: true
            Layout.fillHeight: true
            contentWidth: width
            contentHeight: content.implicitHeight + 68
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar {}

            Txt {
                visible: !d.ready
                anchors.centerIn: parent
                text: "Проверяю ноутбук…"
                color: Theme.muted
                font.pixelSize: 16
            }

            ColumnLayout {
                id: content
                visible: d.ready
                x: 32
                y: 28
                width: flick.width - 64
                spacing: 24

                // header
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 16
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4
                        Txt { text: "Обзор"; font.pixelSize: 28; font.weight: Font.DemiBold }
                        Txt { text: "Всё важное о ноутбуке на одном экране"; color: Theme.muted }
                    }
                    Chip {
                        big: true
                        kind: d.service ? "ok" : "no"
                        text: d.service ? "Фоновая служба работает" : "Фоновая служба не запущена"
                    }
                    Chip {
                        big: true
                        text: d.okCount + " из " + d.total + " функций работают"
                    }
                }

                // mode + scenarios
                Card {
                    Layout.fillWidth: true
                    RowLayout {
                        Layout.fillWidth: true
                        Txt { Layout.fillWidth: true; text: "Режим работы"; font.pixelSize: 16; font.weight: Font.DemiBold }
                        Txt { text: "Сейчас: " + win.modeName(d.currentMode); color: Theme.muted; font.pixelSize: 13 }
                    }
                    GridLayout {
                        Layout.fillWidth: true
                        columns: Math.max(1, Math.min(3, Math.floor((width + 10) / 190)))
                        columnSpacing: 10
                        rowSpacing: 10
                        Repeater {
                            model: d.modes
                            delegate: Rectangle {
                                readonly property bool sel: modelData.id === d.currentMode
                                Layout.fillWidth: true
                                implicitWidth: 170
                                Layout.preferredHeight: 72
                                radius: 12
                                color: sel ? "#1B2D40" : Theme.cardInner
                                border.width: 1
                                border.color: sel ? Theme.accent : Theme.border2
                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: 14
                                    spacing: 4
                                    Txt {
                                        text: modelData.name
                                        font.pixelSize: 15
                                        font.weight: Font.DemiBold
                                        color: sel ? "#FFFFFF" : Theme.text
                                    }
                                    Txt {
                                        text: modelData.hint
                                        font.pixelSize: 12
                                        color: sel ? "#A9D3FF" : Theme.muted
                                    }
                                }
                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: backend.setMode(modelData.id)
                                }
                            }
                        }
                    }
                    Flow {
                        Layout.fillWidth: true
                        spacing: 8
                        Txt {
                            text: "Сценарий"
                            font.pixelSize: 13
                            color: Theme.muted
                            height: 44
                            verticalAlignment: Text.AlignVCenter
                            rightPadding: 4
                        }
                        Repeater {
                            model: d.scenarios
                            delegate: Rectangle {
                                readonly property bool sel: modelData.id === d.scenario
                                height: 44
                                width: pillText.implicitWidth + 36
                                radius: 22
                                color: sel ? Theme.accent : Theme.btn
                                border.width: 1
                                border.color: sel ? Theme.accent : Theme.border3
                                Txt {
                                    id: pillText
                                    anchors.centerIn: parent
                                    text: modelData.name
                                    color: sel ? "#0B1218" : Theme.soft
                                    font.weight: sel ? Font.DemiBold : Font.Medium
                                }
                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: backend.setScenario(modelData.id)
                                }
                            }
                        }
                    }
                }

                // four cards
                GridLayout {
                    Layout.fillWidth: true
                    columns: Math.max(1, Math.floor((width + 16) / 296))
                    columnSpacing: 16
                    rowSpacing: 16

                    Card {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        RowLayout {
                            Layout.fillWidth: true
                            Txt { Layout.fillWidth: true; text: "Процессор"; font.pixelSize: 15; font.weight: Font.DemiBold }
                            Chip {
                                kind: d.cpu.freq && d.cpu.freq !== "—" ? "ok" : "neutral"
                                icon: d.cpu.freq && d.cpu.freq !== "—" ? "check" : ""
                                text: d.cpu.freq && d.cpu.freq !== "—" ? "Работает" : "Нет данных"
                            }
                        }
                        Row {
                            spacing: 8
                            Txt { text: d.cpu.freq || "—"; font.family: Theme.mono; font.pixelSize: 36; font.weight: Font.Medium }
                            Txt { text: "ГГц"; color: Theme.muted; anchors.baseline: parent.children[0].baseline }
                        }
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 6
                            RowLayout {
                                Layout.fillWidth: true
                                Txt { Layout.fillWidth: true; text: "Загрузка"; font.pixelSize: 13; color: Theme.muted }
                                Txt { text: (d.cpu.load !== undefined && d.cpu.load !== null ? d.cpu.load : "—") + " %"; font.family: Theme.mono; font.pixelSize: 13 }
                            }
                            Bar { Layout.fillWidth: true; value: d.cpu.load || 0 }
                        }
                        Spark { Layout.fillWidth: true; Layout.preferredHeight: 40; values: d.cpuHistory }
                        RowLayout {
                            Layout.fillWidth: true
                            Txt { Layout.fillWidth: true; text: "Температура"; color: Theme.soft }
                            Txt { text: (d.cpu.temp || "—") + " °C"; font.family: Theme.mono }
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            Txt { Layout.fillWidth: true; text: "Вентилятор"; color: Theme.soft }
                            Txt { text: (d.cpu.fan || "—") + (d.cpu.fanUnit ? " " + d.cpu.fanUnit : ""); font.family: Theme.mono }
                        }
                    }

                    Card {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        RowLayout {
                            Layout.fillWidth: true
                            Txt { Layout.fillWidth: true; text: "Видеокарта"; font.pixelSize: 15; font.weight: Font.DemiBold }
                            Chip {
                                kind: d.gpu.status || "no"
                                icon: Theme.statusIcon(d.gpu.status || "no")
                                text: d.gpu.statusText || "Нет данных"
                            }
                        }
                        Row {
                            spacing: 8
                            Txt { text: d.gpu.clock || "—"; font.family: Theme.mono; font.pixelSize: 36; font.weight: Font.Medium }
                            Txt { text: "МГц"; color: Theme.muted; anchors.baseline: parent.children[0].baseline }
                        }
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 6
                            RowLayout {
                                Layout.fillWidth: true
                                Txt { Layout.fillWidth: true; text: "Видеопамять"; font.pixelSize: 13; color: Theme.muted }
                                Txt { text: (d.gpu.memUsed || "—") + " / " + (d.gpu.memTotal || "—") + " ГБ"; font.family: Theme.mono; font.pixelSize: 13 }
                            }
                            Bar { Layout.fillWidth: true; value: d.gpu.memPct || 0 }
                        }
                        Spark { Layout.fillWidth: true; Layout.preferredHeight: 40; values: d.gpuHistory }
                        RowLayout {
                            Layout.fillWidth: true
                            Txt { Layout.fillWidth: true; text: "Загрузка"; color: Theme.soft }
                            Txt { text: (d.gpu.util !== undefined && d.gpu.util !== null ? d.gpu.util : "—") + " %"; font.family: Theme.mono }
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            Txt { Layout.fillWidth: true; text: "Температура"; color: Theme.soft }
                            Txt { text: (d.gpu.temp || "—") + " °C"; font.family: Theme.mono }
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            Txt { Layout.fillWidth: true; text: "Потребление"; color: Theme.soft }
                            Txt { text: (d.gpu.power || "—") + " Вт"; font.family: Theme.mono }
                        }
                    }

                    Card {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        RowLayout {
                            Layout.fillWidth: true
                            Txt { Layout.fillWidth: true; text: "Батарея"; font.pixelSize: 15; font.weight: Font.DemiBold }
                            Chip {
                                kind: d.battery.status || "no"
                                icon: Theme.statusIcon(d.battery.status || "no")
                                text: d.battery.statusText || "Нет данных"
                            }
                        }
                        Row {
                            spacing: 8
                            Txt {
                                text: d.battery.percent !== undefined && d.battery.percent !== null ? d.battery.percent : "—"
                                font.family: Theme.mono
                                font.pixelSize: 36
                                font.weight: Font.Medium
                            }
                            Txt { text: "%"; color: Theme.muted; anchors.baseline: parent.children[0].baseline }
                        }
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 6
                            RowLayout {
                                Layout.fillWidth: true
                                Txt { Layout.fillWidth: true; text: d.battery.text || ""; font.pixelSize: 13; color: Theme.muted }
                                Txt { text: d.battery.source || ""; font.pixelSize: 13 }
                            }
                            Bar { Layout.fillWidth: true; value: d.battery.percent || 0; fill: Theme.ok }
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            Txt { Layout.fillWidth: true; text: "Состояние батареи"; color: Theme.soft }
                            Txt { text: (d.battery.health || "—") + " %"; font.family: Theme.mono }
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            Txt { Layout.fillWidth: true; text: "Циклов зарядки"; color: Theme.soft }
                            Txt {
                                text: d.battery.cycles !== undefined && d.battery.cycles !== null ? d.battery.cycles : "—"
                                font.family: Theme.mono
                            }
                        }
                        Item { Layout.fillHeight: true }
                        Rectangle { Layout.fillWidth: true; height: 1; color: Theme.border }
                        RowLayout {
                            Layout.fillWidth: true
                            Txt { Layout.fillWidth: true; text: "Лимит заряда"; color: Theme.soft }
                            Chip {
                                kind: d.limit.status || "no"
                                icon: Theme.statusIcon(d.limit.status || "no")
                                text: d.limit.statusText || "Нет данных"
                            }
                        }
                    }

                    Card {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        RowLayout {
                            Layout.fillWidth: true
                            Txt { Layout.fillWidth: true; text: "Режим графики"; font.pixelSize: 15; font.weight: Font.DemiBold }
                            Chip { kind: "root"; icon: "lock"; text: "Только в BIOS" }
                        }
                        Txt { text: "Не определяется"; font.pixelSize: 22; font.weight: Font.DemiBold }
                        Txt {
                            Layout.fillWidth: true
                            text: "Переключатель MUX (дискретная или гибридная графика) DOCKIT пока не умеет ни читать, ни менять. Его можно поменять в BIOS или в GiMATE на Windows."
                            wrapMode: Text.WordWrap
                            color: Theme.muted
                            lineHeight: 1.25
                        }
                        Item { Layout.fillHeight: true }
                        Rectangle { Layout.fillWidth: true; height: 1; color: Theme.border }
                        Btn {
                            text: "Как это изменить"
                            onClicked: backend.say("MUX меняется в BIOS или в GiMATE (Windows), потом нужна перезагрузка")
                        }
                    }
                }

                // quick toggles
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 12
                    Txt { text: "Быстрые переключатели"; font.pixelSize: 16; font.weight: Font.DemiBold }
                    GridLayout {
                        Layout.fillWidth: true
                        columns: Math.max(1, Math.floor((width + 12) / 222))
                        columnSpacing: 12
                        rowSpacing: 12
                        Repeater {
                            model: d.toggles
                            delegate: ToggleCard {
                                Layout.fillWidth: true
                                label: modelData.label
                                on: modelData.on
                                can: modelData.can
                                onToggled: backend.toggle(modelData.id)
                            }
                        }
                    }
                }

                // feature status list
                Card {
                    Layout.fillWidth: true
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 12
                        Txt { Layout.fillWidth: true; text: "Состояние функций"; font.pixelSize: 16; font.weight: Font.DemiBold }
                        Repeater {
                            model: d.counts
                            delegate: Chip { kind: modelData.status; text: modelData.text }
                        }
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 10
                        Repeater {
                            model: d.features
                            delegate: Rectangle {
                                Layout.fillWidth: true
                                implicitHeight: rowLayout.implicitHeight + 28
                                radius: 12
                                color: Theme.cardInner
                                RowLayout {
                                    id: rowLayout
                                    anchors.fill: parent
                                    anchors.leftMargin: 16
                                    anchors.rightMargin: 16
                                    spacing: 14
                                    Rectangle {
                                        implicitWidth: 36
                                        implicitHeight: 36
                                        radius: 10
                                        color: Theme.statusBg(modelData.status)
                                        Icon {
                                            anchors.centerIn: parent
                                            size: 18
                                            name: Theme.statusIcon(modelData.status)
                                            color: Theme.statusColor(modelData.status)
                                        }
                                    }
                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 2
                                        Txt { text: modelData.name; font.weight: Font.Medium }
                                        Txt {
                                            Layout.fillWidth: true
                                            text: modelData.detail
                                            wrapMode: Text.WordWrap
                                            font.pixelSize: 13
                                            color: Theme.muted
                                        }
                                        Txt {
                                            Layout.fillWidth: true
                                            visible: modelData.hint !== ""
                                            text: "Как исправить: " + modelData.hint
                                            wrapMode: Text.WordWrap
                                            font.pixelSize: 13
                                            color: Theme.warn
                                        }
                                    }
                                    Chip { kind: modelData.status; text: modelData.statusText }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // ---------- message at the bottom ----------
    Rectangle {
        id: toastBox
        visible: backend.toast !== ""
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 28
        width: Math.min(parent.width - 48, toastText.implicitWidth + 40)
        height: 44
        radius: 12
        color: "#223140"
        border.width: 1
        border.color: "#2F5A80"
        Txt {
            id: toastText
            anchors.centerIn: parent
            width: parent.width - 32
            horizontalAlignment: Text.AlignHCenter
            elide: Text.ElideRight
            text: backend.toast
        }
    }
    Timer {
        id: toastTimer
        interval: 4500
        onTriggered: backend.clearToast()
    }
    Connections {
        target: backend
        function onToastChanged() { toastTimer.restart() }
    }
}
