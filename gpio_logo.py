import colorsys
import math
import os
import threading
import time


DEFAULT_RED_PIN = 18
DEFAULT_GREEN_PIN = 10
DEFAULT_BLUE_PIN = 17
DEFAULT_FREQUENCY = 500
PULSE_UPDATE_SECONDS = 0.01


class GpioRgbLogoController:
    def __init__(
        self,
        red_pin=DEFAULT_RED_PIN,
        green_pin=DEFAULT_GREEN_PIN,
        blue_pin=DEFAULT_BLUE_PIN,
        frequency=DEFAULT_FREQUENCY,
        enabled=None,
        inverted=False,
    ):
        self.red_pin = int(red_pin)
        self.green_pin = int(green_pin)
        self.blue_pin = int(blue_pin)
        self.frequency = int(frequency)
        self.inverted = inverted
        self.lock = threading.Lock()
        self.status = {}
        self.effect_mode = None
        self.effect_running = False
        self.effect_thread = None
        self.gpio = None
        self.channels = {}

        if enabled is None:
            enabled = True
        self.enabled = enabled

    def start(self):
        if not self.enabled:
            print("Bauwagenlogo GPIO ist deaktiviert.")
            return

        try:
            import RPi.GPIO as GPIO
        except ImportError:
            self.enabled = False
            print("Bauwagenlogo GPIO konnte nicht gestartet werden: RPi.GPIO fehlt.")
            return

        try:
            self.gpio = GPIO
            self.gpio.setmode(GPIO.BCM)
            self.gpio.setwarnings(False)

            for name, pin in self._pins().items():
                self.gpio.setup(pin, self.gpio.OUT)
                channel = self.gpio.PWM(pin, self.frequency)
                channel.start(self._duty(0))
                self.channels[name] = channel

            print(
                "Bauwagenlogo GPIO gestartet: "
                f"Rot GPIO{self.red_pin}, Gruen GPIO{self.green_pin}, Blau GPIO{self.blue_pin}"
            )
        except Exception as exc:
            self.enabled = False
            print(f"Bauwagenlogo GPIO konnte nicht gestartet werden: {exc}")
            self.close()

    def close(self):
        self._stop_effect()
        if self.channels:
            self._set_rgb_percent(0, 0, 0)
            for channel in self.channels.values():
                channel.stop()
            self.channels = {}

        if self.gpio:
            try:
                self.gpio.cleanup(tuple(self._pins().values()))
            except Exception:
                pass
            self.gpio = None

    def apply_status(self, status):
        with self.lock:
            self.status = dict(status)

        if not self.enabled or not self.channels:
            return

        if not status.get("on"):
            self._stop_effect()
            self._set_rgb_percent(0, 0, 0)
            return

        mode = status.get("mode", "static")
        if mode == "static":
            self._stop_effect()
            self._set_status_color(status)
            return

        if mode in ("pulse", "fade"):
            self._start_effect(mode)
            return

        self._stop_effect()
        self._set_status_color(status)

    def _set_status_color(self, status):
        red, green, blue = self._hex_to_rgb(status.get("color", "#ff0000"))
        brightness = self._percent(status.get("brightness", 100)) / 100
        self._set_rgb_percent(
            red * brightness * 100 / 255,
            green * brightness * 100 / 255,
            blue * brightness * 100 / 255,
        )

    def _start_effect(self, mode):
        with self.lock:
            if self.effect_running and self.effect_mode == mode:
                return

        self._stop_effect()

        with self.lock:
            self.effect_mode = mode
            self.effect_running = True
            self.effect_thread = threading.Thread(target=self._effect_loop, daemon=True)
            self.effect_thread.start()

    def _stop_effect(self):
        with self.lock:
            thread = self.effect_thread
            self.effect_running = False
            self.effect_mode = None
            self.effect_thread = None

        if thread and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=1)

    def _effect_loop(self):
        started = time.monotonic()
        while True:
            with self.lock:
                if not self.effect_running:
                    return
                status = dict(self.status)
                mode = self.effect_mode

            speed = self._percent(status.get("speed", 50), minimum=1)
            brightness = self._percent(status.get("brightness", 100)) / 100
            seconds = time.monotonic() - started

            if mode == "pulse":
                red, green, blue = self._hex_to_rgb(status.get("color", "#ff0000"))
                cycle = self._cycle_seconds(speed, slow=9.0, fast=2.2)
                wave = (math.sin(seconds * 2 * math.pi / cycle) + 1) / 2
                level = 0.50 + 0.70 * wave
                scale = brightness * level * 100 / 255
                self._set_rgb_percent(red * scale, green * scale, blue * scale)
            elif mode == "fade":
                cycle = self._cycle_seconds(speed, slow=16.0, fast=2.0)
                hue = (seconds / cycle) % 1.0
                red, green, blue = colorsys.hsv_to_rgb(hue, 1.0, brightness)
                self._set_rgb_percent(red * 100, green * 100, blue * 100)

            time.sleep(PULSE_UPDATE_SECONDS)

    def _set_rgb_percent(self, red, green, blue):
        values = {
            "red": self._percent(red),
            "green": self._percent(green),
            "blue": self._percent(blue),
        }

        for name, value in values.items():
            channel = self.channels.get(name)
            if channel:
                channel.ChangeDutyCycle(self._duty(value))

    def _duty(self, percent):
        percent = self._percent(percent)
        return 100 - percent if self.inverted else percent

    def _pins(self):
        return {
            "red": self.red_pin,
            "green": self.green_pin,
            "blue": self.blue_pin,
        }

    @staticmethod
    def _hex_to_rgb(hex_color):
        value = str(hex_color).lstrip("#")
        if len(value) != 6:
            return 255, 0, 0

        return (
            int(value[0:2], 16),
            int(value[2:4], 16),
            int(value[4:6], 16),
        )

    @staticmethod
    def _cycle_seconds(speed, slow, fast):
        speed = GpioRgbLogoController._percent(speed, minimum=1)
        return slow - ((speed - 1) * (slow - fast) / 99)

    @staticmethod
    def _percent(value, minimum=0):
        try:
            value = float(value)
        except (TypeError, ValueError):
            value = 0
        return max(minimum, min(100, value))


def create_logo_controller_from_env():
    enabled = os.environ.get("LOGO_GPIO_ENABLED")
    if enabled is not None:
        enabled = enabled == "1"

    inverted = os.environ.get("LOGO_GPIO_INVERTED", "0") == "1"
    controller = GpioRgbLogoController(
        red_pin=os.environ.get("LOGO_GPIO_RED", DEFAULT_RED_PIN),
        green_pin=os.environ.get("LOGO_GPIO_GREEN", DEFAULT_GREEN_PIN),
        blue_pin=os.environ.get("LOGO_GPIO_BLUE", DEFAULT_BLUE_PIN),
        frequency=os.environ.get("LOGO_GPIO_FREQUENCY", DEFAULT_FREQUENCY),
        enabled=enabled,
        inverted=inverted,
    )
    controller.start()
    return controller
