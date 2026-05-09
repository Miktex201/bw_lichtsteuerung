import os
import threading
import time


class DmxSerialDriver:
    def __init__(self, device="/dev/ttyUSB0", channels=512, fps=44, enabled=None):
        self.device = device
        self.channels = channels
        self.fps = max(1, min(44, int(fps)))
        self.frame_time = 1 / self.fps
        self.data = bytearray([0] * channels)
        self.lock = threading.Lock()
        self.serial = None
        self.thread = None
        self.running = False

        if enabled is None:
            enabled = os.path.exists(device)
        self.enabled = enabled

    def start(self):
        if not self.enabled:
            print("DMX ist deaktiviert. Setze LICHT_DMX_ENABLED=1 auf dem Raspberry Pi.")
            return

        try:
            import serial

            self.serial = serial.Serial(
                port=self.device,
                baudrate=250000,
                bytesize=8,
                parity=serial.PARITY_NONE,
                stopbits=2
            )
        except Exception as exc:
            self.enabled = False
            print(f"DMX konnte nicht gestartet werden: {exc}")
            return

        self.running = True
        self.thread = threading.Thread(target=self._send_loop, daemon=True)
        self.thread.start()
        print(f"DMX-Ausgabe gestartet auf {self.device} mit {self.fps} FPS")

    def set_channel(self, channel, value):
        if not 1 <= channel <= self.channels:
            return

        with self.lock:
            self.data[channel - 1] = self._clamp(value)

    def set_channels(self, values):
        with self.lock:
            for channel, value in values.items():
                if 1 <= channel <= self.channels:
                    self.data[channel - 1] = self._clamp(value)

    def blackout(self):
        with self.lock:
            self.data = bytearray([0] * self.channels)

    def close(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)
        if self.serial:
            self.serial.close()

    def _send_loop(self):
        while self.running:
            self.send_frame()
            time.sleep(self.frame_time)

    def send_frame(self):
        if not self.serial:
            return

        with self.lock:
            frame = bytes([0]) + bytes(self.data)

        self.serial.break_condition = True
        time.sleep(0.0001)
        self.serial.break_condition = False
        time.sleep(0.000012)
        self.serial.write(frame)
        self.serial.flush()

    @staticmethod
    def _clamp(value):
        return max(0, min(255, int(value)))
