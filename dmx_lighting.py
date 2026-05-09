import colorsys
import threading
import time


class RgbFixture:
    def __init__(
        self,
        name,
        red_channel,
        green_channel,
        blue_channel,
        program_channel,
        speed_channel,
        dimmer_channel
    ):
        self.name = name
        self.red_channel = red_channel
        self.green_channel = green_channel
        self.blue_channel = blue_channel
        self.program_channel = program_channel
        self.speed_channel = speed_channel
        self.dimmer_channel = dimmer_channel

    def values_for(self, red, green, blue, dimmer):
        return {
            self.red_channel: red,
            self.green_channel: green,
            self.blue_channel: blue,
            self.program_channel: 0,
            self.speed_channel: 0,
            self.dimmer_channel: dimmer
        }

    def program_values_for(self, program, speed, dimmer):
        return {
            self.red_channel: 0,
            self.green_channel: 0,
            self.blue_channel: 0,
            self.program_channel: program,
            self.speed_channel: speed,
            self.dimmer_channel: dimmer
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
            RgbFixture("Lightbar 1", 33, 34, 35, 36, 37, 39),
            RgbFixture("Lightbar 2", 43, 44, 45, 46, 47, 49),
            RgbFixture("Lightbar 3", 53, 54, 55, 56, 57, 59),
            RgbFixture("Lightbar 4", 63, 64, 65, 66, 67, 69),
            RgbFixture("Lightbar 5", 73, 74, 75, 76, 77, 79),
            RgbFixture("Lightbar 6", 83, 84, 85, 86, 87, 89),
        ]
        self.lightbar_channels = {
            channel
            for fixture in self.lightbars
            for channel in (
                fixture.red_channel,
                fixture.green_channel,
                fixture.blue_channel,
                fixture.program_channel,
                fixture.speed_channel,
                fixture.dimmer_channel
            )
        }

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
            self.set_lightbars_rgb(0, 0, 0, 0)
            return

        mode = status.get("mode", "static")
        brightness = status.get("brightness", 100)

        if mode == "static":
            self._stop_effect()
            red, green, blue = self._hex_to_rgb(status.get("color", "#ff0000"))
            self.set_lightbars_rgb(red, green, blue, brightness)
            return

        if mode == "party":
            self._start_effect("party")
            return

        if mode == "slow_fade":
            self._stop_effect()
            self.set_lightbars_program(195, status.get("speed", 50), brightness)

    def set_lightbars_rgb(self, red, green, blue, brightness=100):
        red = self._dmx_value(red)
        green = self._dmx_value(green)
        blue = self._dmx_value(blue)
        dimmer_value = self._brightness_to_dmx(brightness)

        values = {}
        for fixture in self.lightbars:
            values.update(fixture.values_for(red, green, blue, dimmer_value))
        
        self.driver.set_channels(values)

    def set_lightbars_program(self, program, speed, brightness=100):
        program = self._dmx_value(program)
        speed = self._percent_to_dmx(speed, minimum=1)
        dimmer_value = self._brightness_to_dmx(brightness)

        values = {}
        for fixture in self.lightbars:
            values.update(fixture.program_values_for(program, speed, dimmer_value))

        self.driver.set_channels(values)

    def set_manual_channels(self, values):
        values = {
            channel: value
            for channel, value in values.items()
            if channel not in self.lightbar_channels
        }

        if not values:
            return

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

            if self.effect_mode == "party":
                seconds_per_cycle = self._party_cycle_seconds(speed)
                hue = (hue + elapsed / seconds_per_cycle) % 1.0
                red, green, blue = self._party_rgb(hue)
                self.set_lightbars_rgb(red, green, blue, brightness)
                time.sleep(0.05)
                continue

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
    def _party_cycle_seconds(speed):
        return 2.5 - (max(1, min(100, int(speed))) - 1) * (2.0 / 99)

    @staticmethod
    def _party_rgb(hue):
        colors = [
            (255, 0, 180),
            (0, 120, 255),
            (0, 255, 80),
            (255, 255, 0),
            (255, 0, 0),
            (120, 0, 255),
        ]
        return colors[int(hue * len(colors)) % len(colors)]

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
    def _brightness_to_dmx(brightness):
        return round(DmxLightingController._percent(brightness) * 255 / 100)

    @staticmethod
    def _percent_to_dmx(value, minimum=0):
        return round(DmxLightingController._percent(value, minimum=minimum) * 255 / 100)

    @staticmethod
    def _dmx_value(value):
        return max(0, min(255, int(value)))

    @staticmethod
    def _percent(value, minimum=0):
        return max(minimum, min(100, int(value)))

    @staticmethod
    def _hsv_to_rgb(hue, saturation, value):
        red, green, blue = colorsys.hsv_to_rgb(hue, saturation, value)
        return round(red * 255), round(green * 255), round(blue * 255)
