import hmac
import os
import secrets

from flask import Flask, render_template, redirect, url_for, send_from_directory, jsonify, request, session


class SimpleWebServer:
    def __init__(self, host="127.0.0.1", port=5000, lighting_controller=None):
        self.host = host
        self.port = port
        self.lighting_controller = lighting_controller
        self.app = Flask(
            __name__,
            template_folder="templates",
            static_folder="static"
        )
        self.app.secret_key = os.environ.get("LICHT_SECRET_KEY", secrets.token_hex(32))
        self.app.config["TEMPLATES_AUTO_RELOAD"] = True
        self.password = os.environ.get("LICHT_PASSWORD", "bauwagen")
        trusted_ips = os.environ.get("LICHT_TRUSTED_IPS", "127.0.0.1,::1")
        self.trusted_ips = {
            ip.strip()
            for ip in trusted_ips.split(",")
            if ip.strip()
        }
        self.status = {
            "barlicht_innen": {"on": False, "brightness": 100},
            "barlicht_aussen": {
                "on": True,
                "color": "#ff0000",
                "mode": "pulse",
                "brightness": 100,
                "speed": 50
            },
            "barlichtdecke": {
                "on": False,
                "mode": "static",
                "color": "#ff0000",
                "brightness": 100,
                "speed": 50
            }
        }

        self._setup_routes()

    def _setup_routes(self):
        public_endpoints = {"login", "static", "graphics"}

        @self.app.before_request
        def require_login():
            if request.endpoint in public_endpoints:
                return None

            if request.remote_addr in self.trusted_ips:
                return None

            if session.get("authenticated"):
                return None

            if request.path.startswith("/status"):
                return jsonify({"error": "Nicht angemeldet"}), 401

            return redirect(url_for("login", next=request.path))

        @self.app.after_request
        def disable_cache(response):
            response.headers["Cache-Control"] = "no-store"
            return response

        @self.app.route("/login", methods=["GET", "POST"])
        def login():
            error = None

            if request.method == "POST":
                password = request.form.get("password", "")
                if hmac.compare_digest(password, self.password):
                    session["authenticated"] = True
                    return redirect(request.args.get("next") or url_for("index"))
                error = "Passwort stimmt nicht."

            return render_template("login.html", error=error)

        @self.app.route("/logout", methods=["POST"])
        def logout():
            session.clear()
            return redirect(url_for("login"))

        @self.app.route("/", methods=["GET"])
        def index():
            return render_template("index.html")

        @self.app.route("/barlicht-innen", methods=["GET"])
        def barlicht_innen():
            return render_template(
                "page_innen.html",
                title="Barlicht innen",
                subtitle="Steuere die Innenbeleuchtung der Bar",
                button_text="Zurück zur Übersicht"
            )

        @self.app.route("/bauwagenlogo", methods=["GET"])
        def barlicht_aussen():
            return render_template(
                "page_rgb.html",
                title="Bauwagenlogo",
                button_text="Zurück zur Übersicht"
            )

        @self.app.route("/diskolicht-decke", methods=["GET"])
        def barlicht_decke():
            return render_template(
                "page.html",
                title="Diskolicht Decke",
                subtitle="Steuere die Deckenbeleuchtung der Bar",
                button_text="Zurück zur Übersicht"
            )

        @self.app.route("/barlicht-aussen", methods=["GET"])
        def redirect_barlicht_aussen():
            return redirect(url_for("barlicht_aussen"))

        @self.app.route("/barlichtdecke", methods=["GET"])
        def redirect_barlicht_decke():
            return redirect(url_for("barlicht_decke"))

        @self.app.route('/graphics/<path:filename>')
        def graphics(filename):
            return send_from_directory('graphics', filename)

        @self.app.route('/status', methods=['GET'])
        def get_status():
            return jsonify(self.status)

        @self.app.route('/status/<device>', methods=['POST'])
        def update_status(device):
            if device not in self.status:
                return jsonify({"error": "Unbekanntes Geraet"}), 404

            data = request.get_json(silent=True) or {}
            allowed_keys = set(self.status[device].keys())
            for key, value in data.items():
                if key in allowed_keys:
                    self.status[device][key] = value

            self._apply_device_status(device)

            return jsonify(self.status[device])

    def _apply_device_status(self, device):
        if not self.lighting_controller:
            return

        if device == "barlichtdecke":
            self.lighting_controller.apply_ceiling_status(self.status[device])

    def start(self):
        print(f"Server läuft auf http://{self.host}:{self.port}")
        self.app.run(host=self.host, port=self.port)
