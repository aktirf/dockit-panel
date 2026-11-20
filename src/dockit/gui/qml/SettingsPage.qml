import QtQuick
import QtQuick.Layouts

PageFrame {
    id: settingsPage
    title: "Настройки"
    subtitle: "Поведение окна, оформление и сведения о программе"

    // Refresh & Overheat using unified SegmentBar
    Card {
        Layout.fillWidth: true
        Txt { text: "Мониторинг и предупреждения"; font.pixelSize: 16; font.weight: Font.DemiBold }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 6
            Txt { text: "Частота обновления данных"; color: Theme.soft; font.pixelSize: 13 }
            SegmentBar {
                current: String(backend.interval)
                options: [
                    { id: "1", label: "1 с", tip: "Максимально плавно" },
                    { id: "3", label: "3 с", tip: "По умолчанию (баланс)" },
                    { id: "5", label: "5 с", tip: "Меньше нагрузка" },
                    { id: "10", label: "10 с", tip: "Экономия батареи" }
                ]
                onPicked: function (val) { backend.setInterval(Number(val)) }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 6
            Txt { text: "Предупреждать о перегреве"; color: Theme.soft; font.pixelSize: 13 }
            SegmentBar {
                current: d.settings && d.settings.warn_temp !== undefined ? String(d.settings.warn_temp) : "90"
                options: [
                    { id: "0", label: "Выкл", tip: "Не предупреждать" },
                    { id: "80", label: "80 °C", tip: "" },
                    { id: "85", label: "85 °C", tip: "" },
                    { id: "90", label: "90 °C", tip: "" },
                    { id: "95", label: "95 °C", tip: "" }
                ]
                onPicked: function (val) { backend.setWarnTemp(Number(val)) }
            }
        }
    }

    // Window & system behavior
    Card {
        Layout.fillWidth: true
        Txt { text: "Окно и запуск"; font.pixelSize: 16; font.weight: Font.DemiBold }
        ToggleCard {
            Layout.fillWidth: true
            icon: "pulse"
            label: "Уведомления"
            tip: "Сообщения о смене профиля и о перегреве (нужен пакет libnotify)."
            on: d.settings ? d.settings.notify === true : false
            can: d.settings ? d.settings.notifyAvailable === true : false
            onToggled: backend.setNotify(!on)
        }
        ToggleCard {
            Layout.fillWidth: true
            icon: "zap"
            label: "Запускать при входе в систему"
            tip: "Окно DOCKIT откроется само после входа. В Hyprland можно также добавить exec-once = dockit gui."
            on: d.settings ? d.settings.autostart === true : false
            onToggled: backend.setAutostart(!on)
        }
        ToggleCard {
            Layout.fillWidth: true
            icon: "layers"
            label: "Значок в трее, закрытие сворачивает окно"
            tip: "Окно не закрывается, а прячется в трей с быстрым меню режимов и камеры."
            on: d.settings ? d.settings.tray === true : false
            can: d.settings ? d.settings.trayAvailable === true : false
            onToggled: backend.setTray(!on)
        }
        ToggleCard {
            Layout.fillWidth: true
            icon: "sliders"
            label: "Всегда компактное боковое меню (только иконки)"
            tip: "Оставляет узкую полоску иконок слева даже на широком окне."
            on: d.settings ? d.settings.compact_nav === true : false
            onToggled: backend.setCompactNav(!on)
        }
    }

    // Accent color picker
    Card {
        id: accentCard
        Layout.fillWidth: true
        Txt { text: "Акцентный цвет"; font.pixelSize: 16; font.weight: Font.DemiBold }
        Txt {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            color: Theme.muted
            font.pixelSize: 13
            text: "Цвет активных кнопок, переключателей и графиков — можно подобрать под тему Hyprland."
        }
        Flow {
            Layout.fillWidth: true
            spacing: 8
            Repeater {
                model: [
                    { id: "blue", name: "Синий", hex: "#5AB0FF" },
                    { id: "mint", name: "Мятный", hex: "#4CC38A" },
                    { id: "purple", name: "Фиолетовый", hex: "#A78BFA" },
                    { id: "amber", name: "Янтарный", hex: "#F5B942" },
                    { id: "coral", name: "Коралловый", hex: "#FF7A7A" }
                ]
                delegate: Rectangle {
                    readonly property bool sel: !!(d.settings && (d.settings.accent || "blue") === modelData.id)
                    height: 36
                    width: accentRow.implicitWidth + 24
                    radius: 18
                    color: sel ? Theme.navActive : Theme.btn
                    border.width: 1
                    border.color: sel ? modelData.hex : Theme.border3
                    RowLayout {
                        id: accentRow
                        anchors.centerIn: parent
                        spacing: 8
                        Rectangle { width: 10; height: 10; radius: 5; color: modelData.hex }
                        Txt { text: modelData.name; font.pixelSize: 13; color: sel ? "#FFFFFF" : Theme.soft }
                    }
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: backend.setAccent(modelData.id)
                    }
                }
            }
        }
    }

    // About card with logo badge and quick report button
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
                    Txt { Layout.fillWidth: true; elide: Text.ElideRight; text: "DOCKIT " + backend.version + " (бета)"; font.pixelSize: 16; font.weight: Font.DemiBold }
                    Txt { Layout.fillWidth: true; elide: Text.ElideRight; text: "GPL-3.0-or-later · github.com/aktirf/dockit-panel"; color: Theme.muted; font.pixelSize: 12 }
                }
            }
            Btn {
                Layout.alignment: settingsPage.width >= 600 ? Qt.AlignRight | Qt.AlignVCenter : Qt.AlignLeft
                text: "Скопировать отчёт"
                implicitHeight: 34
                onClicked: backend.copyReport()
            }
        }
        Txt {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            color: Theme.muted
            font.pixelSize: 12
            text: "Открытая панель управления ноутбуком для Linux. Проверено на Gigabyte Gaming A16 3VH (CachyOS / Hyprland)."
        }
    }
}
