import colorsys
import threading
import time

from dmx_party_programs import PartyProgram


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


class MovingHeadFixture:
    def __init__(self, name, start_channel):
        self.name = name
        self.start_channel = start_channel

    def values_for(self, pan, tilt, color, pan_fine=0, tilt_fine=0):
        return {
            self.start_channel: pan,
            self.start_channel + 1: pan_fine,
            self.start_channel + 2: tilt,
            self.start_channel + 3: tilt_fine,
            self.start_channel + 4: color,
            self.start_channel + 5: 17,
            self.start_channel + 6: 255,
            self.start_channel + 7: 255
        }


class DmxLightingController:
    STATIC_MOVING_HEAD_VALUES = {
        1: 22,
        2: 0,
        3: 52,
        4: 55,
        5: 59,
        6: 21,
        7: 255,
        8: 255,
        17: 154,
        18: 0,
        19: 56,
        20: 0,
        21: 55,
        22: 21,
        23: 255,
        24: 255,
    }

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
            RgbFixture("Lightbar 4", 82, 83, 84, 85, 86, 87, 88, 89),
            RgbFixture("Lightbar 5", 97, 98, 99, 100, 101, 102, 103, 104),
            RgbFixture("Lightbar 6", 113, 114, 115, 116, 117, 118, 119, 120),
        ]
        self.moving_heads = [
            MovingHeadFixture("MovingHead 1", 1),
            MovingHeadFixture("MovingHead 2", 17),
        ]
        self.moving_head_scenes = (
            ((22, 46, 50), (234, 46, 66), 0.85, 0.35),
            ((54, 132, 42), (202, 132, 82), 1.0, 0.25),
            ((92, 178, 100), (164, 178, 116), 0.8, 0.55),
            ((134, 96, 66), (122, 188, 50), 0.75, 0.2),
            ((202, 154, 82), (54, 154, 42), 1.0, 0.35),
            ((236, 198, 130), (20, 94, 130), 1.15, 0.45),
            ((68, 214, 116), (188, 74, 100), 0.9, 0.6),
            ((188, 74, 27), (68, 214, 50), 0.9, 0.25),
            ((128, 222, 82), (128, 54, 116), 1.25, 0.75),
            ((36, 126, 100), (220, 186, 66), 0.85, 0.35),
            ((220, 186, 42), (36, 126, 130), 0.85, 0.35),
            ((102, 232, 50), (154, 232, 82), 0.7, 0.7),
        )
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
            self.blackout_all()
            return

        mode = status.get("mode", "static")
        brightness = status.get("brightness", 100)

        if mode == "static":
            self._stop_effect()
            self.set_moving_heads_static_target()
            red, green, blue = self._hex_to_rgb(status.get("color", "#ff0000"))
            self.set_lightbars_rgb(red, green, blue, brightness)
            return

        if mode == "party":
            self._start_effect("party")
            return

        if mode == "slow_fade":
            self.set_moving_heads_blackout()
            self._start_effect("slow_fade")

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
            is_active = index in stage.active_indexes or program is not None
            if program is not None:
                program = self._dmx_value(program)
                values.update(fixture.program_values_for(
                    program,
                    speed,
                    party_dimmer,
                    *active_rgb,
                    fade=fade
                ))
            elif is_active:
                values.update(fixture.values_for(
                    *active_rgb,
                    party_dimmer
                ))
            else:
                values.update(fixture.values_for(*inactive_rgb, inactive_dimmer))

        self.driver.set_channels(values)

    def set_moving_head_scene(self, scene, next_scene, progress):
        values = {}
        eased_progress = self._ease_in_out(progress)

        for fixture, current, target in zip(self.moving_heads, scene[:2], next_scene[:2]):
            pan = self._interpolate_dmx(current[0], target[0], eased_progress)
            tilt = self._interpolate_dmx(current[1], target[1], eased_progress)
            color = current[2]
            values.update(fixture.values_for(pan, tilt, color))

        self.driver.set_channels(values)

    def set_moving_heads_blackout(self):
        values = {}
        for fixture in self.moving_heads:
            values.update({
                fixture.start_channel + 5: 17,
                fixture.start_channel + 6: 255,
                fixture.start_channel + 7: 0
            })

        self.driver.set_channels(values)

    def set_moving_heads_static_target(self):
        self.driver.set_channels(self.STATIC_MOVING_HEAD_VALUES)

    def set_manual_channels(self, values):
        self._stop_effect()
        self.driver.set_channels(values)

    def blackout_all(self):
        self._stop_effect()
        self.driver.blackout()

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
        moving_scene_index = 0
        moving_scene_started = time.monotonic()
        next_lightbar_stage_at = 0

        while True:
            with self.lock:
                if not self.effect_running:
                    return
                status = dict(self.ceiling_status)
                mode = self.effect_mode

            speed = self._percent(status.get("speed", 50))
            brightness = status.get("brightness", 100)
            now = time.monotonic()

            if mode != "party":
                if mode == "slow_fade":
                    cycle = self._slow_fade_cycle_seconds(speed)
                    hue = (now / cycle) % 1.0
                    red, green, blue = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
                    self.set_lightbars_rgb(red * 255, green * 255, blue * 255, brightness)
                    time.sleep(0.04)
                    continue

                time.sleep(0.05)
                continue

            if now >= next_lightbar_stage_at:
                stage = party_program.next_stage()
                self.set_lightbar_program_chase_stage(stage, speed, brightness)
                next_lightbar_stage_at = now + self._party_chase_step_seconds(speed) * stage.hold

            scene = self.moving_head_scenes[moving_scene_index % len(self.moving_head_scenes)]
            next_scene = self.moving_head_scenes[(moving_scene_index + 1) % len(self.moving_head_scenes)]
            move_seconds = self._moving_head_scene_seconds(speed) * scene[2]
            hold_seconds = self._moving_head_hold_seconds(speed) * scene[3]
            elapsed = now - moving_scene_started
            progress = 0 if elapsed < hold_seconds else (elapsed - hold_seconds) / move_seconds

            if progress >= 1:
                moving_scene_index += 1
                moving_scene_started = now
                progress = 0
                scene = self.moving_head_scenes[moving_scene_index % len(self.moving_head_scenes)]
                next_scene = self.moving_head_scenes[(moving_scene_index + 1) % len(self.moving_head_scenes)]

            self.set_moving_head_scene(scene, next_scene, progress)

            time.sleep(0.04)

    @staticmethod
    def _party_chase_step_seconds(speed):
        speed = max(0, min(100, int(speed)))
        if speed <= 50:
            return 10.0 - speed * (5.0 / 50)

        return 5.0 - (speed - 50) * (4.0 / 50)

    @staticmethod
    def _slow_fade_cycle_seconds(speed):
        speed = max(0, min(100, int(speed)))
        if speed <= 50:
            return 24.0 - speed * (12.0 / 50)

        return 12.0 - (speed - 50) * (8.0 / 50)

    @staticmethod
    def _moving_head_scene_seconds(speed):
        speed = max(0, min(100, int(speed)))
        if speed <= 50:
            return 7.0 - speed * (4.0 / 50)

        return 3.0 - (speed - 50) * (1.9 / 50)

    @staticmethod
    def _moving_head_hold_seconds(speed):
        speed = max(0, min(100, int(speed)))
        if speed <= 50:
            return 1.25 - speed * (0.45 / 50)

        return 0.8 - (speed - 50) * (0.5 / 50)

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

    @staticmethod
    def _interpolate_dmx(start, end, progress):
        progress = max(0.0, min(1.0, float(progress)))
        return DmxLightingController._dmx_value(round(start + (end - start) * progress))

    @staticmethod
    def _ease_in_out(progress):
        progress = max(0.0, min(1.0, float(progress)))
        return progress * progress * (3 - 2 * progress)
