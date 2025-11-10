import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import timedelta

from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, session, flash
import requests

# --- Cargar variables de entorno ---
load_dotenv()

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:5000")  # tu backend local
SECRET_KEY = os.getenv("SECRET_KEY", "change_me_in_production")
LOG_FILE = os.getenv("LOG_FILE", "frontend.log")

# --- Configurar la app Flask ---
app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=2)

# --- Logging ---
logger = logging.getLogger("frontend")
logger.setLevel(logging.INFO)

ch = logging.StreamHandler()
ch.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(ch)

fh = RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3)
fh.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(fh)

# ---- Helpers ----
def api_get(path: str):
    """Hace GET al backend."""
    url = f"{API_BASE_URL.rstrip('/')}/{path.lstrip('/')}"
    logger.info(f"GET {url}")
    try:
        resp = requests.get(url, timeout=10)
        return resp
    except Exception as e:
        logger.error(f"Error conectando con el backend: {e}")
        return None


# ---- Rutas ----

@app.route("/")
@app.route("/motorcycles")
def motorcycles():
    """Muestra la tabla de motos desde el backend."""
    resp = api_get("/motorcycles/tabla")
    if resp and resp.status_code == 200:
        # El backend devuelve HTML con la tabla
        html_table = resp.text
        return render_template("motorcycles.html", motorcycles_table=html_table)
    else:
        flash("No se pudieron cargar las motos (error de conexión o backend caído).", "danger")
        return render_template("motorcycles.html", motorcycles_table="<p>Error cargando datos</p>")


@app.route("/health")
def health():
    return {"status": "ok"}, 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
