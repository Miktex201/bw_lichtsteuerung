import colorsys
import threading
import time


class RgbFixture:
    def __init__(self, name, red_channel, green_channel, blue_channel):
        self.name = name
        self.red_channel = red_channel
        self.green_channel = green_channel
        self.blue_channel = blue_channel

    def values_for(self, red, green, blue):
        return {
            self.red_channel: red,
            self.green_channel: green,
            self.blue_channel: blue
        }


class DmxLightingController:
    def __init__(self, driver):
        self.driver = driver
        self.lock = threading.Lock()
        self.ceiling_status = {}
        self.effect_mode = None
        self.effect_running = False
        self.effect_thread = None
        self.lightbars = [
            RgbFixture("Lightbar 1", 1, 2, 3),
            RgbFixture("Lightbar 2", 4, 5, 6),
            RgbFixture("Lightbar 3", 7, 8, 9),
            RgbFixture("Lightbar 4", 10, 11, 12),
            RgbFixture("Lightbar 5", 13, 14, 15),
            RgbFixture("Lightbar 6", 16, 17, 18),
        ]

    def start(self):
        self.driver.start()

    def close(self):
        self._stop_effect()
        self.driver.close()

    def apply_ceiling_status(self, status):
        with self.lock:
            self.ceiling_status = dict(status)

        if not status.get("on"):
            self._stop_effect()
            self.driver.blackout()
            return

        mode = status.get("mode", "static")
        brightness = status.get("brightness", 100)

        if mode == "static":
            self._stop_effect()
            red, green, blue = self._hex_to_rgb(status.get("color", "#ff0000"))
            self.set_lightbars_rgb(red, green, blue, brightness)
            return

        if mode == "party":
            self._stop_effect()
            self.set_lightbars_rgb(255, 0, 180, brightness)
            return

        if mode == "slow_fade":
            self._start_effect("slow_fade")

    def set_lightbars_rgb(self, red, green, blue, brightness=100):
        red, green, blue = self._scale_rgb(red, green, blue, brightness)
        values = {}
        for fixture in self.lightbars:
            values.update(fixture.values_for(red, green, blue))
        self.driver.set_channels(values)

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
        hue = 0.0
        last_update = time.monotonic()

        while True:
            with self.lock:
                if not self.effect_running:
                    return
                status = dict(self.ceiling_status)

            now = time.monotonic()
            elapsed = now - last_update
            last_update = now

            speed = self._percent(status.get("speed", 50), minimum=1)
            brightness = status.get("brightness", 100)
            seconds_per_cycle = self._slow_fade_cycle_seconds(speed)
            hue = (hue + elapsed / seconds_per_cycle) % 1.0

            red, green, blue = self._hsv_to_rgb(hue, 1.0, 1.0)
            self.set_lightbars_rgb(red, green, blue, brightness)
            time.sleep(0.05)

    @staticmethod
    def _slow_fade_cycle_seconds(speed):
        # 1 = sehr langsam, 100 = deutlich schneller, aber noch weich.
        return 90 - (max(1, min(100, int(speed))) - 1) * (80 / 99)

    @staticmethod
    def _hex_to_rgb(hex_color):
        value = hex_color.lstrip("#")
        if len(value) != 6:
            return 255, 0, 0

        return (
            int(value[0:2], 16),
            int(value[2:4], 16),
            int(value[4:6], 16)
        )

    @staticmethod
    def _scale_rgb(red, green, blue, brightness):
        factor = DmxLightingController._percent(brightness) / 100
        return (
            round(red * factor),
            round(green * factor),
            round(blue * factor)
        )

    @staticmethod
    def _percent(value, minimum=0):
        return max(minimum, min(100, int(value)))

    @staticmethod
    def _hsv_to_rgb(hue, saturation, value):
        red, green, blue = colorsys.hsv_to_rgb(hue, saturation, value)
        return round(red * 255), round(green * 255), round(blue * 255)
