# Bauwagen Lichtsteuerung

## Notfall-Hotspot

Falls der Raspberry Pi kein WLAN findet, kann ein Handy-Hotspot mit folgenden Daten geöffnet werden:

SSID: NichtOeffentlich
Passwort: BauwagaRenga2016Tex

Der Raspberry Pi verbindet sich automatisch damit, sobald der Hotspot verfügbar ist.

SSH-Zugriff dann über die im Handy angezeigte IP-Adresse:

ssh bw@<IP-Adresse>


## Bauwagenlogo Verkabelung

Die GPIO-Nummern sind BCM-Nummern.

| Kabel | Funktion | Raspberry Pi |
| --- | --- | --- |
| Schwarz | Ground / GND | GND |
| Weiss | Blau | GPIO 17 |
| Gelb | Rot | GPIO 18 |
| Orange | Gruen | GPIO 10 |

Wichtig: Das LED-Band wird nicht direkt vom GPIO versorgt. Die GPIOs steuern nur die MOSFET-Gates. Raspberry-GND und LED-Netzteil-GND muessen verbunden sein.

## MOSFET-Testprogramm

Einzelkanal testen:

```bash
/usr/bin/python3 gpio_pwm_test.py --pin 17 --hold 20 --off-hold 5
```

RGB testen:

```bash
/usr/bin/python3 gpio_pwm_test.py --rgb 18 10 17 --hold 5 --off-hold 3
```

Falls die Schaltung invertiert reagiert:

```bash
/usr/bin/python3 gpio_pwm_test.py --rgb 18 10 17 --inverted
```

## Website Start

Python-venv fuer den Webserver:

```bash
cd ~/bw_lichtsteuerung
python3 -m venv --system-site-packages venv
source venv/bin/activate
pip install -r requirements.txt
```

```bash
cd ~/bw_lichtsteuerung
source venv/bin/activate
LICHT_DMX_ENABLED=1 LOGO_GPIO_ENABLED=1 python main.py
```

Danach im Browser:

```text
http://<raspberry-ip>:8080
```

Das Bauwagenlogo wird in der Website ueber die Seite `Bauwagenlogo` per GPIO-PWM gesteuert.

Default beim Start:

```text
Bauwagenlogo: an
Modus: Pulsierend
Farbe: Weiss
Helligkeit: 100 Prozent
Geschwindigkeit: 5 Prozent
```

## PyQt Start auf Raspberry Pi OS Lite

Einmalig benoetigte Pakete:

```bash
sudo apt install xserver-xorg xserver-xorg-legacy xinit openbox python3-pyqt5 python3-serial python3-rpi.gpio
sudo sh -c 'printf "allowed_users=anybody\nneeds_root_rights=yes\n" > /etc/X11/Xwrapper.config'
```

PyQt5 wird auf dem Raspberry Pi per `apt` installiert, nicht per `pip`. Darum steht `PyQt5` nicht in `requirements.txt`.

Start per PuTTY/SSH:

```bash
cd ~/bw_lichtsteuerung
chmod +x start_pyqt_x.sh start_pyqt_from_ssh.sh
./start_pyqt_from_ssh.sh
```

PyQt neu starten:

```bash
sudo pkill -f pyqt_app.py
sudo pkill -f Xorg
cd ~/bw_lichtsteuerung
./start_pyqt_from_ssh.sh
```

Wenn Webserver und PyQt gleichzeitig laufen sollen, sollte PyQt auf dem Pi nur die Oberflaeche anzeigen und die Hardware ueber den Webserver steuern:

```bash
PYQT_USE_WEBSERVER=1 PYQT_API_BASE=http://127.0.0.1:8080 ./start_pyqt_from_ssh.sh
```

Autostart fuer Webserver und PyQt installieren:

```bash
cd ~/bw_lichtsteuerung
chmod +x install_autostart.sh start_pyqt_x.sh start_pyqt_from_ssh.sh
./install_autostart.sh
sudo reboot
```

Dabei laeuft der Webserver mit niedrigerer Prioritaet und PyQt mit hoeherer Prioritaet.

## Wenn der Bildschirm kurz schwarz wird

Wenn beim Tippen kurz "Kein Signal" erscheint, ist das meistens kein normales PyQt-Layoutproblem, sondern HDMI/X11/Spannung:

```bash
journalctl -u bw-pyqt.service -n 80 --no-pager
journalctl -u bw-web.service -n 80 --no-pager
dmesg | grep -i -E "under-voltage|voltage|hdmi|drm|xorg"
vcgencmd get_throttled
```

`vcgencmd get_throttled` sollte `throttled=0x0` zeigen. Wenn dort ein anderer Wert steht, gab es Unterspannung oder CPU-Drosselung.

Hilfreiche Tests:

```bash
sudo systemctl stop bw-web.service
./start_pyqt_from_ssh.sh
```

Wenn es ohne Webserver stabil ist, ist es Last oder ein Hardware-Zugriffskonflikt. Dann PyQt mit `PYQT_USE_WEBSERVER=1` verwenden.

## Wichtige Umgebungsvariablen

DMX:

```bash
LICHT_DMX_ENABLED=1
LICHT_DMX_DEVICE=/dev/ttyUSB0
LICHT_DMX_FPS=44
```

Bauwagenlogo:

```bash
LOGO_GPIO_ENABLED=1
LOGO_GPIO_RED=18
LOGO_GPIO_GREEN=10
LOGO_GPIO_BLUE=17
LOGO_GPIO_FREQUENCY=500
```

Falls die MOSFET-Schaltung invertiert ist:

```bash
LOGO_GPIO_INVERTED=1
```
