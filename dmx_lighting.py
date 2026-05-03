import threading


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
        self.driver.close()

    def apply_ceiling_status(self, status):
        with self.lock:
            if not status.get("on"):
                self.driver.blackout()
                return

            mode = status.get("mode", "static")
            brightness = status.get("brightness", 100)

            if mode == "static":
                red, green, blue = self._hex_to_rgb(status.get("color", "#ff0000"))
                self.set_lightbars_rgb(red, green, blue, brightness)
                return

            if mode == "party":
                self.set_lightbars_rgb(255, 0, 180, brightness)
                return

            if mode == "slow_fade":
                self.set_lightbars_rgb(0, 80, 255, brightness)

    def set_lightbars_rgb(self, red, green, blue, brightness=100):
        red, green, blue = self._scale_rgb(red, green, blue, brightness)
        values = {}
        for fixture in self.lightbars:
            values.update(fixture.values_for(red, green, blue))
        self.driver.set_channels(values)

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
        factor = max(0, min(100, int(brightness))) / 100
        return (
            round(red * factor),
            round(green * factor),
            round(blue * factor)
        )
