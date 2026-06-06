import argparse
import colorsys
import math
import os
import sys

from dmx_driver import DmxSerialDriver
from dmx_lighting import DmxLightingController
from gpio_logo import create_logo_controller_from_env


try:
    from PyQt5.QtCore import QPointF, Qt, pyqtSignal
    from PyQt5.QtGui import QColor, QFont, QImage, QPainter, QPen, QPixmap
    from PyQt5.QtWidgets import (
        QApplication,
        QButtonGroup,
        QFrame,
        QGridLayout,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMainWindow,
        QPushButton,
        QSizePolicy,
        QSlider,
        QStackedWidget,
        QStyle,
        QVBoxLayout,
        QWidget,
    )
except ImportError as exc:
    raise SystemExit(
        "PyQt5 ist nicht installiert. Auf dem Raspberry Pi z.B. installieren mit: "
        "sudo apt install python3-pyqt5"
    ) from exc


APP_STYLE = """
* {
    font-family: "Segoe UI", "DejaVu Sans", Arial, sans-serif;
    color: #f8fafc;
}
QPushButton {
    background: rgba(255, 255, 255, 22);
    border: 1px solid rgba(255, 255, 255, 55);
    border-radius: 12px;
    padding: 8px 14px;
    font-size: 16px;
    font-weight: 600;
}
QPushButton:hover {
    background: rgba(255, 255, 255, 36);
    border-color: rgba(255, 255, 255, 90);
}
QPushButton:checked {
    background: rgba(59, 130, 246, 205);
    border-color: rgba(59, 130, 246, 255);
}
QPushButton:disabled {
    color: rgba(248, 250, 252, 90);
    background: rgba(255, 255, 255, 14);
}
QLabel#title {
    font-size: 26px;
    font-weight: 700;
    letter-spacing: 1px;
}
QLabel#subtitle {
    color: rgba(248, 250, 252, 215);
    font-size: 14px;
}
QLabel#sectionLabel {
    font-size: 16px;
    font-weight: 600;
}
QFrame#screen {
    background: rgba(255, 255, 255, 20);
    border: 1px solid rgba(255, 255, 255, 36);
    border-radius: 22px;
}
QFrame#dmxRow {
    background: rgba(255, 255, 255, 20);
    border: 1px solid rgba(255, 255, 255, 46);
    border-radius: 10px;
}
QLineEdit {
    background: rgba(15, 23, 42, 96);
    border: 1px solid rgba(248, 250, 252, 76);
    border-radius: 8px;
    padding: 5px;
    font-size: 15px;
    font-weight: 700;
}
QSlider::groove:horizontal {
    height: 14px;
    border-radius: 7px;
    background: rgba(255, 255, 255, 50);
}
QSlider::handle:horizontal {
    width: 46px;
    height: 46px;
    margin: -16px 0;
    border-radius: 23px;
    background: #f8fafc;
}
"""


class AppBackground(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logo = QPixmap(find_logo_path())

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#0f172a"))

        if not self.logo.isNull():
            painter.setOpacity(0.10)
            max_width = int(self.width() * 0.86)
            scaled = self.logo.scaledToWidth(max_width, Qt.SmoothTransformation)
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
            painter.setOpacity(1.0)

        super().paintEvent(event)


class ColorWheel(QWidget):
    colorChanged = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.wheel_size = 190
        self.setFixedSize(self.wheel_size, self.wheel_size)
        self.setCursor(Qt.PointingHandCursor)
        self.image = self._build_image(self.wheel_size)
        self.selector = QPointF(self.wheel_size - 12, self.wheel_size / 2)
        self.enabled_for_pick = True

    def set_pick_enabled(self, enabled):
        self.enabled_for_pick = enabled
        self.setEnabled(enabled)
        self.update()

    def set_color(self, hex_color):
        red, green, blue = hex_to_rgb(hex_color)
        hue, saturation, _ = colorsys.rgb_to_hsv(red / 255, green / 255, blue / 255)
        radius = self.width() / 2
        angle = hue * 2 * math.pi
        distance = saturation * radius
        self.selector = QPointF(radius + math.cos(angle) * distance, radius + math.sin(angle) * distance)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setOpacity(1.0 if self.enabled_for_pick else 0.42)
        painter.drawImage(0, 0, self.image)
        painter.setPen(QPen(QColor(248, 250, 252, 72), 3))
        painter.drawEllipse(2, 2, self.width() - 4, self.height() - 4)
        painter.setOpacity(1.0)
        painter.setPen(QPen(QColor("#f8fafc"), 3))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(self.selector, 9, 9)

    def mousePressEvent(self, event):
        self._pick(event.pos())

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            self._pick(event.pos())

    def _pick(self, point):
        if not self.enabled_for_pick:
            return

        radius = self.width() / 2
        dx = point.x() - radius
        dy = point.y() - radius
        distance = math.sqrt(dx * dx + dy * dy)
        if distance > radius:
            return

        hue = math.atan2(dy, dx) / (2 * math.pi)
        if hue < 0:
            hue += 1
        saturation = distance / radius
        red, green, blue = colorsys.hsv_to_rgb(hue, saturation, 1)
        self.selector = QPointF(point)
        self.colorChanged.emit(rgb_to_hex(round(red * 255), round(green * 255), round(blue * 255)))
        self.update()

    @staticmethod
    def _build_image(size):
        image = QImage(size, size, QImage.Format_ARGB32)
        radius = size / 2
        for y in range(size):
            for x in range(size):
                dx = x - radius
                dy = y - radius
                distance = math.sqrt(dx * dx + dy * dy)
                if distance <= radius:
                    hue = math.atan2(dy, dx) / (2 * math.pi)
                    if hue < 0:
                        hue += 1
                    red, green, blue = colorsys.hsv_to_rgb(hue, distance / radius, 1)
                    image.setPixelColor(x, y, QColor(round(red * 255), round(green * 255), round(blue * 255)))
                else:
                    image.setPixelColor(x, y, QColor(0, 0, 0, 0))
        return image


class TouchSlider(QSlider):
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self.setTracking(True)
        self.setSingleStep(1)
        self.setPageStep(1)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._set_value_from_position(event.pos())
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            self._set_value_from_position(event.pos())
            event.accept()
            return

        super().mouseMoveEvent(event)

    def _set_value_from_position(self, position):
        if self.orientation() != Qt.Horizontal:
            return

        width = max(1, self.width())
        x = max(0, min(width, position.x()))
        value = QStyle.sliderValueFromPosition(
            self.minimum(),
            self.maximum(),
            x,
            width,
            self.invertedAppearance(),
        )
        self.setValue(value)


class MainWindow(QMainWindow):
    def __init__(self, lighting_controller, logo_controller=None):
        super().__init__()
        self.lighting_controller = lighting_controller
        self.logo_controller = logo_controller
        self.status = {
            "barlicht_innen": {"on": False, "brightness": 100},
            "barlicht_aussen": {
                "on": True,
                "color": "#ffffff",
                "mode": "pulse",
                "brightness": 100,
                "speed": 5,
            },
            "barlichtdecke": {
                "on": False,
                "mode": "static",
                "color": "#ff0000",
                "brightness": 100,
                "speed": 50,
            },
        }
        self.manual_dmx_values = {channel: 0 for channel in range(1, 256)}

        self.setWindowTitle("Barlicht Steuerung")
        self.resize(1024, 600)

        root = AppBackground()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(12, 12, 12, 12)

        self.screen = QFrame()
        self.screen.setObjectName("screen")
        screen_layout = QVBoxLayout(self.screen)
        screen_layout.setContentsMargins(18, 14, 18, 14)

        self.stack = QStackedWidget()
        screen_layout.addWidget(self.stack)
        root_layout.addWidget(self.screen)
        self.setCentralWidget(root)

        self.inside_page = DimmerPage(self, "Barlicht innen", "Steuere die Innenbeleuchtung der Bar", "barlicht_innen")
        self.logo_page = LogoPage(self)
        self.ceiling_page = CeilingPage(self)
        self.dmx_page = DmxPage(self)
        self.home_page = HomePage(self)

        for page in (self.home_page, self.inside_page, self.logo_page, self.ceiling_page, self.dmx_page):
            self.stack.addWidget(page)

        self.apply_logo_status()
        self.show_home()

    def show_home(self):
        self.stack.setCurrentWidget(self.home_page)

    def show_dmx(self):
        self.dmx_page.enter_page()
        self.stack.setCurrentWidget(self.dmx_page)

    def leave_dmx(self):
        self.apply_ceiling_status()
        self.stack.setCurrentWidget(self.ceiling_page)

    def apply_ceiling_status(self):
        self.lighting_controller.apply_ceiling_status(self.status["barlichtdecke"])

    def update_ceiling(self, **updates):
        self.status["barlichtdecke"].update(updates)
        self.apply_ceiling_status()

    def apply_logo_status(self):
        if self.logo_controller:
            self.logo_controller.apply_status(self.status["barlicht_aussen"])

    def update_logo(self, **updates):
        self.status["barlicht_aussen"].update(updates)
        self.apply_logo_status()

    def set_manual_channel(self, channel, value):
        channel = max(1, min(255, int(channel)))
        value = max(0, min(255, int(value)))
        self.manual_dmx_values[channel] = value
        self.lighting_controller.set_manual_channels({channel: value})


class HomePage(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        button_row = QHBoxLayout()
        button_row.setSpacing(18)
        layout.addLayout(button_row, 1)

        self._add_home_button(button_row, "Barlicht innen", window.inside_page)
        self._add_home_button(button_row, "Bauwagenlogo", window.logo_page)
        self._add_home_button(button_row, "Diskolicht Decke", window.ceiling_page)

    def _add_home_button(self, layout, text, page):
        button = QPushButton(text)
        button.setMinimumSize(0, 0)
        button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        button.setFont(QFont(button.font().family(), 27, QFont.Bold))
        button.clicked.connect(lambda: self.window.stack.setCurrentWidget(page))
        layout.addWidget(button, 1)


class DimmerPage(QWidget):
    def __init__(self, window, title, subtitle, device):
        super().__init__()
        self.window = window
        self.device = device

        layout = centered_panel(self)
        layout.addWidget(title_label(title))
        if subtitle:
            layout.addWidget(subtitle_label(subtitle))

        power_row = QHBoxLayout()
        self.on_button = check_button("An")
        self.off_button = check_button("Aus")
        self.off_button.setChecked(True)
        self.on_button.clicked.connect(lambda: self.set_power(True))
        self.off_button.clicked.connect(lambda: self.set_power(False))
        power_row.addWidget(self.on_button)
        power_row.addWidget(self.off_button)
        layout.addLayout(power_row)

        layout.addWidget(section_label("Helligkeit"))
        self.brightness = value_slider(0, 100, 50)
        self.brightness_label = QLabel("50%")
        self.brightness_label.setAlignment(Qt.AlignCenter)
        self.brightness.valueChanged.connect(self.set_brightness)
        layout.addWidget(self.brightness)
        layout.addWidget(self.brightness_label)
        layout.addWidget(back_button(window.show_home))

    def set_power(self, on):
        self.on_button.setChecked(on)
        self.off_button.setChecked(not on)
        self.window.status[self.device]["on"] = on

    def set_brightness(self, value):
        self.brightness_label.setText(f"{value}%")
        self.window.status[self.device]["brightness"] = value


class LogoPage(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.current_color = "#ffffff"
        self.current_mode = "pulse"

        layout = centered_panel(self)
        layout.addWidget(title_label("Bauwagenlogo"))
        layout.addWidget(subtitle_label("Steuere das Bauwagenlogo"))

        power_row = QHBoxLayout()
        self.on_button = check_button("An")
        self.off_button = check_button("Aus")
        self.on_button.setChecked(True)
        power_row.addWidget(self.on_button)
        power_row.addWidget(self.off_button)
        self.on_button.clicked.connect(lambda: self.set_power(True))
        self.off_button.clicked.connect(lambda: self.set_power(False))
        layout.addLayout(power_row)

        body = QHBoxLayout()
        body.setSpacing(18)
        layout.addLayout(body)

        color_column = QVBoxLayout()
        color_column.setSpacing(7)
        color_column.addWidget(section_label("Farbe waehlen"), alignment=Qt.AlignCenter)
        color_column.addWidget(subtitle_label("Aktiv bei Statisch und Pulsierend"), alignment=Qt.AlignCenter)
        self.wheel = ColorWheel()
        self.wheel.set_color(self.current_color)
        self.wheel.colorChanged.connect(self.set_color)
        color_column.addWidget(self.wheel, alignment=Qt.AlignCenter)
        self.color_value = color_value_label(self.current_color)
        color_column.addWidget(self.color_value, alignment=Qt.AlignCenter)
        body.addLayout(color_column)

        controls = QVBoxLayout()
        controls.setSpacing(7)
        controls.addWidget(section_label("Modus"), alignment=Qt.AlignCenter)
        self.mode_buttons = self.create_mode_buttons(
            controls,
            (("static", "Statisch"), ("pulse", "Pulsierend"), ("fade", "Farbwechselnd")),
        )
        controls.addWidget(section_label("Helligkeit"), alignment=Qt.AlignCenter)
        self.brightness = value_slider(0, 100, 100)
        self.brightness_label = QLabel("100%")
        self.brightness_label.setAlignment(Qt.AlignCenter)
        self.brightness.valueChanged.connect(self.set_brightness)
        controls.addWidget(self.brightness)
        controls.addWidget(self.brightness_label)
        self.speed_title = section_label("Geschwindigkeit")
        controls.addWidget(self.speed_title, alignment=Qt.AlignCenter)
        self.speed = value_slider(1, 100, 5)
        self.speed_label = QLabel("5%")
        self.speed_label.setAlignment(Qt.AlignCenter)
        self.speed.valueChanged.connect(self.set_speed)
        controls.addWidget(self.speed)
        controls.addWidget(self.speed_label)
        body.addLayout(controls)

        layout.addWidget(back_button(window.show_home))
        self.update_mode_ui()

    def create_mode_buttons(self, layout, modes):
        group = QButtonGroup(self)
        group.setExclusive(True)
        buttons = {}
        for mode, label in modes:
            button = check_button(label)
            button.clicked.connect(lambda checked=False, selected=mode: self.set_mode(selected))
            layout.addWidget(button)
            group.addButton(button)
            buttons[mode] = button
        buttons[self.current_mode].setChecked(True)
        return buttons

    def set_power(self, on):
        self.on_button.setChecked(on)
        self.off_button.setChecked(not on)
        self.window.update_logo(on=on)

    def set_color(self, hex_color):
        self.current_color = hex_color
        self.color_value.setText(color_text(hex_color))
        if self.current_mode in ("static", "pulse"):
            self.window.update_logo(color=hex_color)

    def set_mode(self, mode):
        self.current_mode = mode
        update = {"on": True, "mode": mode}
        if mode in ("static", "pulse"):
            update["color"] = self.current_color
        self.on_button.setChecked(True)
        self.off_button.setChecked(False)
        self.window.update_logo(**update)
        self.update_mode_ui()

    def set_brightness(self, value):
        self.brightness_label.setText(f"{value}%")
        self.window.update_logo(on=True, brightness=value)
        self.on_button.setChecked(True)
        self.off_button.setChecked(False)

    def set_speed(self, value):
        self.speed_label.setText(f"{value}%")
        self.window.update_logo(on=True, speed=value)
        self.on_button.setChecked(True)
        self.off_button.setChecked(False)

    def update_mode_ui(self):
        can_pick = self.current_mode in ("static", "pulse")
        uses_speed = self.current_mode in ("pulse", "fade")
        self.wheel.set_pick_enabled(can_pick)
        self.speed_title.setVisible(uses_speed)
        self.speed.setVisible(uses_speed)
        self.speed_label.setVisible(uses_speed)


class CeilingPage(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.current_color = "#ff0000"
        self.current_mode = "static"

        layout = centered_panel(self)
        layout.addWidget(title_label("Diskolicht Decke"))

        power_row = QHBoxLayout()
        self.on_button = check_button("An")
        self.off_button = check_button("Aus")
        self.off_button.setChecked(True)
        self.on_button.clicked.connect(lambda: self.set_power(True))
        self.off_button.clicked.connect(lambda: self.set_power(False))
        power_row.addWidget(self.on_button)
        power_row.addWidget(self.off_button)
        layout.addLayout(power_row)

        body = QHBoxLayout()
        body.setSpacing(18)
        layout.addLayout(body)

        color_column = QVBoxLayout()
        color_column.setSpacing(7)
        color_column.addWidget(section_label("Farbe waehlen"), alignment=Qt.AlignCenter)
        color_column.addWidget(subtitle_label("Nur bei statischem Licht aktiv"), alignment=Qt.AlignCenter)
        self.wheel = ColorWheel()
        self.wheel.colorChanged.connect(self.set_color)
        color_column.addWidget(self.wheel, alignment=Qt.AlignCenter)
        self.color_value = color_value_label(self.current_color)
        color_column.addWidget(self.color_value, alignment=Qt.AlignCenter)
        body.addLayout(color_column)

        controls = QVBoxLayout()
        controls.setSpacing(7)
        controls.addWidget(section_label("Modus"), alignment=Qt.AlignCenter)
        self.mode_group = QButtonGroup(self)
        self.mode_group.setExclusive(True)
        self.mode_buttons = {}
        for mode, label in (("static", "Statisches Licht"), ("slow_fade", "Farbwechsel"), ("party", "Partymodus")):
            button = check_button(label)
            button.clicked.connect(lambda checked=False, selected=mode: self.set_mode(selected))
            controls.addWidget(button)
            self.mode_group.addButton(button)
            self.mode_buttons[mode] = button
        self.mode_buttons["static"].setChecked(True)

        self.brightness_title = section_label("Master-Dimmer")
        controls.addWidget(self.brightness_title, alignment=Qt.AlignCenter)
        self.brightness = value_slider(0, 100, 50)
        self.brightness_label = QLabel("50%")
        self.brightness_label.setAlignment(Qt.AlignCenter)
        self.brightness.valueChanged.connect(self.set_brightness)
        controls.addWidget(self.brightness)
        controls.addWidget(self.brightness_label)

        self.speed_title = section_label("Geschwindigkeit")
        controls.addWidget(self.speed_title, alignment=Qt.AlignCenter)
        self.speed = value_slider(0, 100, 50)
        self.speed_label = QLabel("50%")
        self.speed_label.setAlignment(Qt.AlignCenter)
        self.speed.valueChanged.connect(self.set_speed)
        controls.addWidget(self.speed)
        controls.addWidget(self.speed_label)
        body.addLayout(controls)

        bottom = QHBoxLayout()
        bottom.addWidget(back_button(window.show_home, "Zurueck zur Startseite"), 1)
        settings = QPushButton("DMX")
        settings.setFixedSize(48, 42)
        settings.clicked.connect(window.show_dmx)
        bottom.addWidget(settings)
        layout.addLayout(bottom)

        self.update_mode_ui()

    def set_power(self, on):
        self.on_button.setChecked(on)
        self.off_button.setChecked(not on)
        self.window.update_ceiling(on=on)

    def set_color(self, hex_color):
        self.current_color = hex_color
        self.color_value.setText(color_text(hex_color))
        if self.current_mode == "static":
            self.window.update_ceiling(on=True, mode="static", color=hex_color)
            self.on_button.setChecked(True)
            self.off_button.setChecked(False)

    def set_mode(self, mode):
        self.current_mode = mode
        update = {"on": True, "mode": mode}
        if mode == "static":
            update["color"] = self.current_color
        self.on_button.setChecked(True)
        self.off_button.setChecked(False)
        self.window.update_ceiling(**update)
        self.update_mode_ui()

    def set_brightness(self, value):
        self.brightness_label.setText(f"{value}%")
        self.window.update_ceiling(on=True, brightness=value)
        self.on_button.setChecked(True)
        self.off_button.setChecked(False)

    def set_speed(self, value):
        self.speed_label.setText(f"{value}%")
        self.window.update_ceiling(on=True, speed=value)
        self.on_button.setChecked(True)
        self.off_button.setChecked(False)

    def update_mode_ui(self):
        is_static = self.current_mode == "static"
        uses_speed = self.current_mode in ("party", "slow_fade")
        self.wheel.set_pick_enabled(is_static)
        self.brightness_title.setVisible(is_static)
        self.brightness.setVisible(is_static)
        self.brightness_label.setVisible(is_static)
        self.speed_title.setVisible(uses_speed)
        self.speed.setVisible(uses_speed)
        self.speed_label.setVisible(uses_speed)


class DmxPage(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.current_page = 0
        self.channels_per_page = 8
        self.max_channel = 255
        self.max_page = (self.max_channel - 1) // self.channels_per_page
        self.channel_rows = []

        layout = centered_panel(self)
        layout.addWidget(title_label("DMX Einstellungen"))
        layout.addWidget(subtitle_label("Manuelle Steuerung der Diskolicht-Decke"))

        nav = QHBoxLayout()
        self.prev_button = QPushButton("<")
        self.prev_button.setFixedSize(46, 42)
        self.prev_button.clicked.connect(self.previous_page)
        self.range_label = QLabel()
        self.range_label.setObjectName("title")
        self.range_label.setAlignment(Qt.AlignCenter)
        self.next_button = QPushButton(">")
        self.next_button.setFixedSize(46, 42)
        self.next_button.clicked.connect(self.next_page)
        nav.addWidget(self.prev_button)
        nav.addWidget(self.range_label, 1)
        nav.addWidget(self.next_button)
        layout.addLayout(nav)

        self.rows_layout = QVBoxLayout()
        self.rows_layout.setSpacing(6)
        layout.addLayout(self.rows_layout)

        for _ in range(self.channels_per_page):
            row_frame = QFrame()
            row_frame.setObjectName("dmxRow")
            row = QHBoxLayout(row_frame)
            row.setContentsMargins(10, 5, 10, 5)
            label = QLabel()
            label.setMinimumWidth(58)
            label.setFont(QFont(label.font().family(), 15, QFont.Bold))
            slider = value_slider(0, 255, 0)
            number = QLineEdit("0")
            number.setFixedWidth(62)
            number.setAlignment(Qt.AlignCenter)
            row.addWidget(label)
            row.addWidget(slider, 1)
            row.addWidget(number)
            self.rows_layout.addWidget(row_frame)
            self.channel_rows.append((label, slider, number))

        layout.addWidget(back_button(window.leave_dmx, "Zurueck zur Decke"))
        self.render()

    def enter_page(self):
        self.render()

    def previous_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.render()

    def next_page(self):
        if self.current_page < self.max_page:
            self.current_page += 1
            self.render()

    def render(self):
        start = self.current_page * self.channels_per_page + 1
        end = min(start + self.channels_per_page - 1, self.max_channel)
        self.range_label.setText(f"CH{start} - CH{end}")
        self.prev_button.setEnabled(self.current_page > 0)
        self.next_button.setEnabled(self.current_page < self.max_page)

        for offset, (label, slider, number) in enumerate(self.channel_rows):
            channel = start + offset
            value = self.window.manual_dmx_values.get(channel, 0)
            label.setText(f"CH{channel}")
            reconnect_slider(slider, lambda new_value, ch=channel, num=number: self.set_channel(ch, new_value, num))
            reconnect_line_edit(number, lambda text, ch=channel, sl=slider: self.set_channel_from_text(ch, text, sl))
            slider.blockSignals(True)
            slider.setValue(value)
            slider.blockSignals(False)
            number.blockSignals(True)
            number.setText(str(value))
            number.blockSignals(False)

    def set_channel(self, channel, value, number):
        value = max(0, min(255, int(value)))
        number.blockSignals(True)
        number.setText(str(value))
        number.blockSignals(False)
        self.window.set_manual_channel(channel, value)

    def set_channel_from_text(self, channel, text, slider):
        try:
            value = int(text)
        except ValueError:
            value = 0
        value = max(0, min(255, value))
        slider.blockSignals(True)
        slider.setValue(value)
        slider.blockSignals(False)
        self.window.set_manual_channel(channel, value)


def centered_panel(widget):
    layout = QVBoxLayout(widget)
    layout.setContentsMargins(70, 0, 70, 0)
    layout.setSpacing(10)
    layout.addStretch(1)
    panel = QVBoxLayout()
    panel.setSpacing(10)
    layout.addLayout(panel)
    layout.addStretch(1)
    return panel


def title_label(text):
    label = QLabel(text)
    label.setObjectName("title")
    label.setAlignment(Qt.AlignCenter)
    return label


def subtitle_label(text):
    label = QLabel(text)
    label.setObjectName("subtitle")
    label.setAlignment(Qt.AlignCenter)
    label.setWordWrap(True)
    return label


def section_label(text):
    label = QLabel(text)
    label.setObjectName("sectionLabel")
    label.setAlignment(Qt.AlignCenter)
    return label


def check_button(text):
    button = QPushButton(text)
    button.setCheckable(True)
    button.setMinimumHeight(42)
    button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    return button


def back_button(callback, text="Zurueck zur Startseite"):
    button = QPushButton(text)
    button.setMinimumWidth(190)
    button.setMinimumHeight(38)
    button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    button.clicked.connect(callback)
    return button


def value_slider(minimum, maximum, value):
    slider = TouchSlider(Qt.Horizontal)
    slider.setRange(minimum, maximum)
    slider.setValue(value)
    slider.setMinimumWidth(210)
    return slider


def color_value_label(hex_color):
    label = QLabel(color_text(hex_color))
    label.setAlignment(Qt.AlignCenter)
    return label


def color_text(hex_color):
    red, green, blue = hex_to_rgb(hex_color)
    return f"{hex_color} - RGB {red}, {green}, {blue}"


def hex_to_rgb(hex_color):
    value = hex_color.lstrip("#")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def rgb_to_hex(red, green, blue):
    return f"#{red:02x}{green:02x}{blue:02x}"


def find_logo_path():
    graphics_dir = os.path.join(os.path.dirname(__file__), "graphics")
    if not os.path.isdir(graphics_dir):
        return ""

    for filename in os.listdir(graphics_dir):
        if filename.lower().startswith("bauwaga logo") and filename.lower().endswith(".png"):
            return os.path.join(graphics_dir, filename)

    return ""


def reconnect_slider(slider, callback):
    try:
        slider.valueChanged.disconnect()
    except TypeError:
        pass
    slider.valueChanged.connect(callback)


def reconnect_line_edit(line_edit, callback):
    try:
        line_edit.textChanged.disconnect()
    except TypeError:
        pass
    line_edit.textChanged.connect(callback)


def create_lighting_controller():
    dmx_enabled = os.environ.get("LICHT_DMX_ENABLED")
    if dmx_enabled is not None:
        dmx_enabled = dmx_enabled == "1"

    default_device = "COM34" if os.name == "nt" else "/dev/ttyUSB1"
    dmx_driver = DmxSerialDriver(
        device=os.environ.get("LICHT_DMX_DEVICE", default_device),
        fps=int(os.environ.get("LICHT_DMX_FPS", "44")),
        enabled=dmx_enabled,
    )
    controller = DmxLightingController(dmx_driver)
    controller.start()
    return controller


def parse_args():
    parser = argparse.ArgumentParser(description="Native PyQt Oberflaeche fuer die DMX Lichtsteuerung")
    parser.add_argument("--fullscreen", action="store_true", help="im Vollbild starten")
    return parser.parse_args()


def main():
    args = parse_args()
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_STYLE)
    controller = create_lighting_controller()
    logo_controller = create_logo_controller_from_env()
    window = MainWindow(controller, logo_controller)
    if args.fullscreen:
        window.showFullScreen()
    else:
        window.show()

    try:
        return app.exec_()
    finally:
        logo_controller.close()
        controller.close()


if __name__ == "__main__":
    sys.exit(main())
