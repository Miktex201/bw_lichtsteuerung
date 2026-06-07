import requests
import time
import os

from dmx_driver import DmxSerialDriver
from dmx_lighting import DmxLightingController
from gpio_logo import create_logo_controller_from_env
from webserver import SimpleWebServer

def get_light_status():
    try:
        response = requests.get('http://127.0.0.1:8080/status')
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except:
        return None

if __name__ == "__main__":
    dmx_enabled = os.environ.get("LICHT_DMX_ENABLED")
    if dmx_enabled is not None:
        dmx_enabled = dmx_enabled == "1"

    default_device = "COM34" if os.name == "nt" else "/dev/ttyUSB0"
    dmx_driver = DmxSerialDriver(
        device=os.environ.get("LICHT_DMX_DEVICE", default_device),
        fps=int(os.environ.get("LICHT_DMX_FPS", "44")),
        enabled=dmx_enabled
    )
    lighting_controller = DmxLightingController(dmx_driver)
    lighting_controller.start()
    logo_controller = create_logo_controller_from_env()

    try:
        server = SimpleWebServer(
            host="0.0.0.0",
            port=8080,
            lighting_controller=lighting_controller,
            logo_controller=logo_controller
        )
        server.start()
    finally:
        logo_controller.close()
        lighting_controller.close()
