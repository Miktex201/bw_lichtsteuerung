from dataclasses import dataclass


LIGHTBAR_INDEX = {
    1: 0,
    2: 1,
    3: 2,
    4: 3,
    5: 4,
    6: 5,
}


PROGRAM_RED_STRIPE = 96
PROGRAM_OUTSIDE_INSIDE = 140
PROGRAM_COLOR_VARIANT = 140
PROGRAM_FULL_MODE = 126
SPEED_OUTSIDE_INSIDE = 253
SPEED_COLORFUL = 152
SPEED_SPLIT_COLOR = 165
SPEED_FULL_MODE = 254

# Placeholder program values for other internal Lightbar programs.
# Tune these values once you know which CH4 ranges trigger the best colors.
PROGRAM_COLOR_WHEEL = [96, 112, 128, 144, 160, 176]


@dataclass(frozen=True)
class PartyStage:
    programs: dict
    hold: float = 1.0
    speed_dmx: int = None
    effect_dmx: int = 253
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
    program=PROGRAM_RED_STRIPE,
    hold=1.0,
    speed_dmx=None,
    effect_dmx=253,
    rgb=(255, 255, 255),
    inactive_rgb=(0, 0, 0),
    inactive_dimmer=0
):
    return PartyStage(
        programs={LIGHTBAR_INDEX[number]: program for number in lightbars},
        hold=hold,
        speed_dmx=speed_dmx,
        effect_dmx=effect_dmx,
        rgb=rgb,
        inactive_rgb=inactive_rgb,
        inactive_dimmer=inactive_dimmer
    )


def color_stage(
    assignments,
    hold=1.0,
    speed_dmx=None,
    effect_dmx=253,
    rgb=(255, 255, 255),
    inactive_rgb=(0, 0, 0),
    inactive_dimmer=0
):
    return PartyStage(
        programs={
            LIGHTBAR_INDEX[number]: program
            for number, program in assignments.items()
        },
        hold=hold,
        speed_dmx=speed_dmx,
        effect_dmx=effect_dmx,
        rgb=rgb,
        inactive_rgb=inactive_rgb,
        inactive_dimmer=inactive_dimmer
    )


PARTY_PATTERNS = (
    PartyPattern(
        name="outside_inside_color_wave",
        stages=(
            stage((1, 2, 3, 4, 5, 6), PROGRAM_OUTSIDE_INSIDE, hold=1.4, speed_dmx=SPEED_OUTSIDE_INSIDE),
        ),
    ),
    PartyPattern(
        name="full_mode_126",
        stages=(
            stage((1, 2, 3, 4, 5, 6), PROGRAM_FULL_MODE, hold=1.4, speed_dmx=SPEED_FULL_MODE),
        ),
    ),
    PartyPattern(
        name="colorful_program_152",
        stages=(
            stage((1, 2, 3, 4, 5, 6), PROGRAM_COLOR_VARIANT, hold=1.4, speed_dmx=SPEED_COLORFUL),
        ),
    ),
    PartyPattern(
        name="split_color_program_165",
        stages=(
            stage((1, 2, 3, 4, 5, 6), PROGRAM_COLOR_VARIANT, hold=1.4, speed_dmx=SPEED_SPLIT_COLOR),
        ),
    ),
    PartyPattern(
        name="red_stripe_from_heads",
        stages=(
            stage((1, 2), rgb=(255, 0, 0), inactive_rgb=(20, 0, 0), inactive_dimmer=90),
            stage((3, 4), rgb=(255, 0, 0), inactive_rgb=(20, 0, 0), inactive_dimmer=90),
            stage((5, 6), rgb=(255, 0, 0), inactive_rgb=(20, 0, 0), inactive_dimmer=90),
            stage((3, 4), rgb=(255, 0, 0), inactive_rgb=(20, 0, 0), inactive_dimmer=90),
        ),
        repeats=2,
    ),
    PartyPattern(
        name="red_stripe_around_clockwise",
        stages=(
            stage((1,), rgb=(255, 0, 0), inactive_rgb=(20, 0, 0), inactive_dimmer=90),
            stage((3,), rgb=(255, 0, 0), inactive_rgb=(20, 0, 0), inactive_dimmer=90),
            stage((5,), rgb=(255, 0, 0), inactive_rgb=(20, 0, 0), inactive_dimmer=90),
            stage((6,), rgb=(255, 0, 0), inactive_rgb=(20, 0, 0), inactive_dimmer=90),
            stage((4,), rgb=(255, 0, 0), inactive_rgb=(20, 0, 0), inactive_dimmer=90),
            stage((2,), rgb=(255, 0, 0), inactive_rgb=(20, 0, 0), inactive_dimmer=90),
        ),
    ),
    PartyPattern(
        name="red_stripe_around_counter",
        stages=(
            stage((2,), rgb=(255, 0, 0), inactive_rgb=(20, 0, 0), inactive_dimmer=90),
            stage((4,), rgb=(255, 0, 0), inactive_rgb=(20, 0, 0), inactive_dimmer=90),
            stage((6,), rgb=(255, 0, 0), inactive_rgb=(20, 0, 0), inactive_dimmer=90),
            stage((5,), rgb=(255, 0, 0), inactive_rgb=(20, 0, 0), inactive_dimmer=90),
            stage((3,), rgb=(255, 0, 0), inactive_rgb=(20, 0, 0), inactive_dimmer=90),
            stage((1,), rgb=(255, 0, 0), inactive_rgb=(20, 0, 0), inactive_dimmer=90),
        ),
    ),
    PartyPattern(
        name="red_stripe_cross",
        stages=(
            stage((1, 6), rgb=(255, 0, 0), inactive_rgb=(20, 0, 0), inactive_dimmer=90),
            stage((3, 4), rgb=(255, 0, 0), inactive_rgb=(20, 0, 0), inactive_dimmer=90),
            stage((5, 2), rgb=(255, 0, 0), inactive_rgb=(20, 0, 0), inactive_dimmer=90),
            stage((3, 4), rgb=(255, 0, 0), inactive_rgb=(20, 0, 0), inactive_dimmer=90),
        ),
        repeats=2,
    ),
    PartyPattern(
        name="color_orbit",
        stages=(
            color_stage({1: PROGRAM_COLOR_WHEEL[0]}),
            color_stage({3: PROGRAM_COLOR_WHEEL[1]}),
            color_stage({5: PROGRAM_COLOR_WHEEL[2]}),
            color_stage({6: PROGRAM_COLOR_WHEEL[3]}),
            color_stage({4: PROGRAM_COLOR_WHEEL[4]}),
            color_stage({2: PROGRAM_COLOR_WHEEL[5]}),
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
