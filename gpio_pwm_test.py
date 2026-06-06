import argparse
import time


DEFAULT_PIN = 17
DEFAULT_RGB_PINS = (18, 10, 17)
DEFAULT_FREQUENCY = 1000


def import_gpio():
    try:
        import RPi.GPIO as GPIO
    except ImportError as exc:
        raise SystemExit(
            "RPi.GPIO ist nicht installiert. Auf dem Raspberry Pi installieren mit: "
            "sudo apt install python3-rpi.gpio"
        ) from exc

    return GPIO


class PwmChannel:
    def __init__(self, gpio, pin, frequency, inverted=False):
        self.gpio = gpio
        self.pin = pin
        self.inverted = inverted
        self.pwm = gpio.PWM(pin, frequency)
        self.pwm.start(self._duty(0))

    def set_percent(self, percent):
        percent = max(0, min(100, int(percent)))
        self.pwm.ChangeDutyCycle(self._duty(percent))

    def stop(self):
        self.pwm.stop()

    def _duty(self, percent):
        return 100 - percent if self.inverted else percent


class DirectChannel:
    def __init__(self, gpio, pin, inverted=False):
        self.gpio = gpio
        self.pin = pin
        self.inverted = inverted
        self.set_percent(0)

    def set_percent(self, percent):
        is_on = float(percent) > 0
        if self.inverted:
            is_on = not is_on
        self.gpio.output(self.pin, self.gpio.HIGH if is_on else self.gpio.LOW)

    def stop(self):
        self.set_percent(0)


def create_channel(gpio, pin, args):
    if args.direct:
        return DirectChannel(gpio, pin, args.inverted)
    return PwmChannel(gpio, pin, args.frequency, args.inverted)


def setup_gpio(gpio, pins):
    gpio.setmode(gpio.BCM)
    gpio.setwarnings(False)
    for pin in pins:
        gpio.setup(pin, gpio.OUT)


def sleep_step(seconds):
    time.sleep(max(0, float(seconds)))


def run_single_pin_test(args):
    gpio = import_gpio()
    setup_gpio(gpio, (args.pin,))
    channel = create_channel(gpio, args.pin, args)

    try:
        for percent, seconds in ((100, args.hold), (50, args.hold), (0, args.off_hold)):
            print(f"GPIO {args.pin}: {percent}%")
            channel.set_percent(percent)
            sleep_step(seconds)
    finally:
        channel.stop()
        gpio.cleanup()


def run_rgb_test(args):
    gpio = import_gpio()
    red_pin, green_pin, blue_pin = args.rgb
    setup_gpio(gpio, args.rgb)
    channels = {
        "Rot": create_channel(gpio, red_pin, args),
        "Gruen": create_channel(gpio, green_pin, args),
        "Blau": create_channel(gpio, blue_pin, args),
    }

    steps = (
        ("Rot 100%", (100, 0, 0), args.hold),
        ("Gruen 100%", (0, 100, 0), args.hold),
        ("Blau 100%", (0, 0, 100), args.hold),
        ("Weiss 100%", (100, 100, 100), args.hold),
        ("Weiss 50%", (50, 50, 50), args.hold),
        ("Aus", (0, 0, 0), args.off_hold),
    )

    try:
        for label, values, seconds in steps:
            print(label)
            for channel, percent in zip(channels.values(), values):
                channel.set_percent(percent)
            sleep_step(seconds)
    finally:
        for channel in channels.values():
            channel.stop()
        gpio.cleanup()


def parse_args():
    parser = argparse.ArgumentParser(
        description="GPIO PWM Test fuer MOSFETs, LED-Band und Bauwagenlogo"
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--pin",
        type=int,
        default=DEFAULT_PIN,
        help=f"einzelner BCM-GPIO fuer den 1-Kanal-Test, Standard: {DEFAULT_PIN}",
    )
    mode.add_argument(
        "--rgb",
        type=int,
        nargs=3,
        metavar=("ROT", "GRUEN", "BLAU"),
        help=(
            "drei BCM-GPIOs fuer RGB-Test, z.B. --rgb 18 10 17. "
            f"Ohne Angabe nutzt der Einzeltest GPIO {DEFAULT_PIN}."
        ),
    )
    parser.add_argument(
        "--frequency",
        type=int,
        default=DEFAULT_FREQUENCY,
        help=f"PWM-Frequenz in Hz, Standard: {DEFAULT_FREQUENCY}",
    )
    parser.add_argument(
        "--hold",
        type=float,
        default=5,
        help="Sekunden pro Teststufe, Standard: 5",
    )
    parser.add_argument(
        "--off-hold",
        type=float,
        default=2,
        help="Sekunden am Ende auf 0 Prozent, Standard: 2",
    )
    parser.add_argument(
        "--inverted",
        action="store_true",
        help="Duty-Cycle invertieren, falls deine Schaltung aktiv-low ist",
    )
    parser.add_argument(
        "--direct",
        action="store_true",
        help="ohne PWM testen: GPIO nur dauerhaft an oder aus schalten",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    if args.rgb:
        run_rgb_test(args)
    else:
        run_single_pin_test(args)


if __name__ == "__main__":
    main()
