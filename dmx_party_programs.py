from dataclasses import dataclass


LIGHTBAR_INDEX = {
    1: 0,
    2: 1,
    3: 2,
    4: 3,
    5: 4,
    6: 5,
}


PROGRAM_RED_STRIPE = 94
PROGRAM_OUTSIDE_INSIDE = 143
PROGRAM_COLOR_VARIANT = 143
PROGRAM_FULL_MODE = 129
PROGRAM_SLOW_FADE = 192
SPEED_OUTSIDE_INSIDE = 253
SPEED_COLORFUL = 152
SPEED_SPLIT_COLOR = 165
SPEED_FULL_MODE = 254

# Placeholder program values for other internal Lightbar programs.
# Tune these values once you know which CH5 ranges trigger the best colors.
PROGRAM_COLOR_WHEEL = [94, 108, 122, 136, 150, 164]


@dataclass(frozen=True)
class PartyStage:
    programs: dict
    active_indexes: tuple = ()
    hold: float = 1.0
    speed_dmx: int = None
    fade_dmx: int = 253
    rgb: tuple = (255, 255, 255)
    inactive_rgb: tuple = (0, 0, 0)
    inactive_dimmer: int = 0


@dataclass(frozen=True)
class PartyPattern:
    name: str
    stages: tuple
    repeats: int = 1


def stage(
    lightbars,
    program=None,
    hold=1.0,
    speed_dmx=None,
    fade_dmx=253,
    rgb=(255, 255, 255),
    inactive_rgb=(0, 0, 0),
    inactive_dimmer=0
):
    active_indexes = tuple(LIGHTBAR_INDEX[number] for number in lightbars)
    return PartyStage(
        programs={
            LIGHTBAR_INDEX[number]: program
            for number in lightbars
            if program is not None
        },
        active_indexes=active_indexes,
        hold=hold,
        speed_dmx=speed_dmx,
        fade_dmx=fade_dmx,
        rgb=rgb,
        inactive_rgb=inactive_rgb,
        inactive_dimmer=inactive_dimmer
    )


def color_stage(
    assignments,
    hold=1.0,
    speed_dmx=None,
    fade_dmx=253,
    rgb=(255, 255, 255),
    inactive_rgb=(0, 0, 0),
    inactive_dimmer=0
):
    return PartyStage(
        programs={
            LIGHTBAR_INDEX[number]: program
            for number, program in assignments.items()
        },
        active_indexes=tuple(LIGHTBAR_INDEX[number] for number in assignments),
        hold=hold,
        speed_dmx=speed_dmx,
        fade_dmx=fade_dmx,
        rgb=rgb,
        inactive_rgb=inactive_rgb,
        inactive_dimmer=inactive_dimmer
    )


PARTY_PATTERNS = (
    PartyPattern(
        name="row_chase_from_heads",
        stages=(
            stage((1, 2), hold=0.8, rgb=(255, 35, 0), inactive_rgb=(14, 0, 0), inactive_dimmer=75),
            stage((3, 4), hold=0.8, rgb=(0, 220, 255), inactive_rgb=(0, 8, 12), inactive_dimmer=75),
            stage((5, 6), hold=0.8, rgb=(180, 0, 255), inactive_rgb=(8, 0, 12), inactive_dimmer=75),
            stage((3, 4), hold=0.65, rgb=(255, 230, 0), inactive_rgb=(12, 8, 0), inactive_dimmer=70),
        ),
        repeats=2,
    ),
    PartyPattern(
        name="left_right_pingpong",
        stages=(
            stage((2, 4, 6), hold=0.75, rgb=(0, 255, 120), inactive_rgb=(0, 8, 4), inactive_dimmer=70),
            stage((1, 3, 5), hold=0.75, rgb=(255, 0, 90), inactive_rgb=(12, 0, 4), inactive_dimmer=70),
            stage((2, 4, 6), hold=0.55, rgb=(0, 140, 255), inactive_rgb=(0, 4, 12), inactive_dimmer=70),
            stage((1, 3, 5), hold=0.55, rgb=(255, 170, 0), inactive_rgb=(12, 6, 0), inactive_dimmer=70),
        ),
        repeats=2,
    ),
    PartyPattern(
        name="clockwise_orbit",
        stages=(
            stage((1,), hold=0.42, rgb=(255, 0, 0), inactive_rgb=(8, 0, 0), inactive_dimmer=65),
            stage((3,), hold=0.42, rgb=(255, 110, 0), inactive_rgb=(8, 3, 0), inactive_dimmer=65),
            stage((5,), hold=0.42, rgb=(255, 255, 0), inactive_rgb=(8, 8, 0), inactive_dimmer=65),
            stage((6,), hold=0.42, rgb=(0, 255, 80), inactive_rgb=(0, 8, 3), inactive_dimmer=65),
            stage((4,), hold=0.42, rgb=(0, 160, 255), inactive_rgb=(0, 4, 8), inactive_dimmer=65),
            stage((2,), hold=0.42, rgb=(160, 0, 255), inactive_rgb=(4, 0, 8), inactive_dimmer=65),
        ),
        repeats=3,
    ),
    PartyPattern(
        name="counter_orbit",
        stages=(
            stage((2,), hold=0.48, rgb=(255, 255, 255), inactive_rgb=(6, 6, 6), inactive_dimmer=60),
            stage((4,), hold=0.48, rgb=(0, 255, 255), inactive_rgb=(0, 5, 5), inactive_dimmer=60),
            stage((6,), hold=0.48, rgb=(0, 80, 255), inactive_rgb=(0, 2, 8), inactive_dimmer=60),
            stage((5,), hold=0.48, rgb=(255, 0, 180), inactive_rgb=(8, 0, 5), inactive_dimmer=60),
            stage((3,), hold=0.48, rgb=(255, 60, 0), inactive_rgb=(8, 2, 0), inactive_dimmer=60),
            stage((1,), hold=0.48, rgb=(255, 255, 255), inactive_rgb=(6, 6, 6), inactive_dimmer=60),
        ),
        repeats=2,
    ),
    PartyPattern(
        name="cross_hits",
        stages=(
            stage((1, 6), hold=0.7, rgb=(255, 0, 120), inactive_rgb=(9, 0, 4), inactive_dimmer=70),
            stage((2, 5), hold=0.7, rgb=(0, 210, 255), inactive_rgb=(0, 7, 9), inactive_dimmer=70),
            stage((3, 4), hold=0.7, rgb=(255, 255, 255), inactive_rgb=(6, 6, 6), inactive_dimmer=70),
            stage((1, 2, 3, 4, 5, 6), hold=0.35, rgb=(255, 255, 255), inactive_dimmer=0),
            stage((), hold=0.25),
        ),
        repeats=2,
    ),
    PartyPattern(
        name="full_color_blocks",
        stages=(
            stage((1, 2, 3, 4, 5, 6), hold=0.8, rgb=(255, 0, 0)),
            stage((1, 2, 3, 4, 5, 6), hold=0.8, rgb=(0, 255, 80)),
            stage((1, 2, 3, 4, 5, 6), hold=0.8, rgb=(0, 80, 255)),
            stage((1, 2, 3, 4, 5, 6), hold=0.8, rgb=(255, 255, 255)),
        ),
    ),
    PartyPattern(
        name="all_hit",
        stages=(
            stage((1, 2, 3, 4, 5, 6), hold=1.0),
            stage((), hold=0.5),
        ),
    ),
)


class PartyProgram:
    def __init__(self, patterns=PARTY_PATTERNS):
        self.stages = self._flatten(patterns)
        self.index = 0

    def next_stage(self):
        if not self.stages:
            return PartyStage(programs={})

        current = self.stages[self.index % len(self.stages)]
        self.index += 1
        return current

    @staticmethod
    def _flatten(patterns):
        stages = []
        for pattern in patterns:
            for _ in range(max(1, int(pattern.repeats))):
                stages.extend(pattern.stages)
        return tuple(stages)
