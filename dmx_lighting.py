import threading
import time

from dmx_party_programs import PartyProgram, PROGRAM_SLOW_FADE


class RgbFixture:
    def __init__(
        self,
        name,
        dimmer_channel,
        red_channel,
        green_channel,
        blue_channel,
        program_channel,
        speed_channel,
        fade_channel,
        flash_channel
    ):
        self.name = name
        self.dimmer_channel = dimmer_channel
        self.red_channel = red_channel
        self.green_channel = green_channel
        self.blue_channel = blue_channel
        self.program_channel = program_channel
        self.speed_channel = speed_channel
        self.fade_channel = fade_channel
        self.flash_channel = flash_channel

    def values_for(self, red, green, blue, dimmer):
        return {
            self.dimmer_channel: dimmer,
            self.red_channel: red,
            self.green_channel: green,
            self.blue_channel: blue,
            self.program_channel: 0,
            self.speed_channel: 0,
            self.fade_channel: 0,
            self.flash_channel: 0
        }

    def program_values_for(
        self,
        program,
        speed,
        dimmer,
        red=255,
        green=255,
        blue=255,
        fade=0,
        flash=0
    ):
        return {
            self.dimmer_channel: dimmer,
            self.red_channel: red,
            self.green_channel: green,
            self.blue_channel: blue,
            self.program_channel: program,
            self.speed_channel: speed,
            self.fade_channel: fade,
            self.flash_channel: flash
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
            RgbFixture("Lightbar 1", 33, 34, 35, 36, 37, 38, 39, 40),
            RgbFixture("Lightbar 2", 49, 50, 51, 52, 53, 54, 55, 56),
            RgbFixture("Lightbar 3", 65, 66, 67, 68, 69, 70, 71, 72),
            RgbFixture("Lightbar 4", 81, 82, 83, 84, 85, 86, 87, 88),
            RgbFixture("Lightbar 5", 97, 98, 99, 100, 101, 102, 103, 104),
            RgbFixture("Lightbar 6", 113, 114, 115, 116, 117, 118, 119, 120),
        ]
        self.lightbar_channels = {
            channel
            for fixture in self.lightbars
            for channel in (
                fixture.dimmer_channel,
                fixture.red_channel,
                fixture.green_channel,
                fixture.blue_channel,
                fixture.program_channel,
                fixture.speed_channel,
                fixture.fade_channel,
                fixture.flash_channel
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
            self.set_lightbars_program(PROGRAM_SLOW_FADE, status.get("speed", 50), brightness)

    def set_lightbars_rgb(self, red, green, blue, brightness=100):
        red = self._dmx_value(red)
        green = self._dmx_value(green)
        blue = self._dmx_value(blue)
        dimmer_value = self._brightness_to_dmx(brightness)

        values = {}
        for fixture in self.lightbars:
            values.update(fixture.values_for(red, green, blue, dimmer_value))
        
        self.driver.set_channels(values)

    def set_lightbars_program(self, program, speed, brightness=100, fade=253):
        program = self._dmx_value(program)
        speed = self._program_speed_to_dmx(speed)
        dimmer_value = self._brightness_to_dmx(brightness)
        fade = self._dmx_value(fade)

        values = {}
        for fixture in self.lightbars:
            values.update(fixture.program_values_for(program, speed, dimmer_value, fade=fade))

        self.driver.set_channels(values)

    def set_lightbar_program_chase_stage(self, stage, speed, brightness=100):
        speed_dmx = stage.speed_dmx
        if speed_dmx is None:
            speed = self._party_chase_speed_to_dmx(speed)
        else:
            speed = self._dmx_value(speed_dmx)

        dimmer_value = self._brightness_to_dmx(brightness)
        party_dimmer = max(dimmer_value, 220)
        active_rgb = tuple(self._dmx_value(value) for value in stage.rgb)
        inactive_rgb = tuple(self._dmx_value(value) for value in stage.inactive_rgb)
        inactive_dimmer = self._dmx_value(stage.inactive_dimmer)
        fade = self._dmx_value(stage.fade_dmx)

        values = {}
        for index, fixture in enumerate(self.lightbars):
            program = stage.programs.get(index)
            if program is not None:
                program = self._dmx_value(program)
                values.update(fixture.program_values_for(
                    program,
                    speed,
                    party_dimmer,
                    *active_rgb,
                    fade=fade
                ))
            else:
                values.update(fixture.values_for(*inactive_rgb, inactive_dimmer))

        self.driver.set_channels(values)

    def set_manual_channels(self, values):
        self._stop_effect()
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
        party_program = PartyProgram()

        while True:
            with self.lock:
                if not self.effect_running:
                    return
                status = dict(self.ceiling_status)
                mode = self.effect_mode

            speed = self._percent(status.get("speed", 50))
            brightness = status.get("brightness", 100)

            if mode != "party":
                time.sleep(0.05)
                continue

            stage = party_program.next_stage()
            self.set_lightbar_program_chase_stage(
                stage,
                speed,
                brightness
            )
            self._sleep_while_effect_running(
                self._party_chase_step_seconds(speed) * stage.hold
            )

    @staticmethod
    def _party_chase_step_seconds(speed):
        speed = max(0, min(100, int(speed)))
        if speed <= 50:
            return 10.0 - speed * (5.0 / 50)

        return 5.0 - (speed - 50) * (4.0 / 50)

    def _sleep_while_effect_running(self, seconds):
        end_time = time.monotonic() + seconds
        while time.monotonic() < end_time:
            with self.lock:
                if not self.effect_running:
                    return
            time.sleep(0.05)

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
    def _program_speed_to_dmx(value):
        return DmxLightingController._percent_to_dmx(value)

    @staticmethod
    def _party_chase_speed_to_dmx(value):
        return DmxLightingController._percent_to_dmx(value)

    @staticmethod
    def _dmx_value(value):
        return max(0, min(255, int(value)))

    @staticmethod
    def _percent(value, minimum=0):
        return max(minimum, min(100, int(value)))
