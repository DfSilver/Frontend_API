# app.py
import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import timedelta

from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, session, flash
import requests

# --- Cargar variables de entorno ---
load_dotenv()

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:5000")
SECRET_KEY = os.getenv("SECRET_KEY", "change_me_in_production")
LOG_FILE = os.getenv("LOG_FILE", "frontend.log")

# --- Configurar Flask ---
app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=2)

# --- Configurar Logging ---
logger = logging.getLogger("motos_frontend")
logger.setLevel(logging.INFO)

formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

# Consola
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
ch.setFormatter(formatter)
logger.addHandler(ch)

# Archivo rotativo
fh = RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3)
fh.setLevel(logging.INFO)
fh.setFormatter(formatter)
logger.addHandler(fh)

logger.info("Frontend iniciado. API_BASE_URL=%s", API_BASE_URL)

# --- Helpers ---
def api_post(path: str, json=None, token: str | None = None):
    url = f"{API_BASE_URL.rstrip('/')}/{path.lstrip('/')}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    logger.debug("POST %s", url)
    return requests.post(url, json=json, headers=headers, timeout=10)


def api_get(path: str, token: str | None = None, params: dict | None = None):
    url = f"{API_BASE_URL.rstrip('/')}/{path.lstrip('/')}"
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    logger.debug("GET %s", url)
    return requests.get(url, headers=headers, params=params, timeout=10)


# --- Rutas ---
@app.route("/")
def index():
    if session.get("token"):
        return redirect(url_for("users"))
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    email = request.form.get("email")
    password = request.form.get("password")
    role = request.form.get("role", "user")

    if not email or not password:
        flash("Email y contraseña son obligatorios", "warning")
        return redirect(url_for("register"))

    try:
        resp = api_post("/register", json={"email": email, "password": password, "role": role})
        if resp.status_code in (200, 201):
            flash("Registro exitoso. Inicia sesión ahora.", "success")
            return redirect(url_for("login"))
        else:
            flash(f"Error en registro: {resp.json().get('error', 'Intenta nuevamente')}", "danger")
            return redirect(url_for("register"))
    except Exception as e:
        logger.exception("Error registrando usuario")
        flash("Error de conexión con el servidor", "danger")
        return redirect(url_for("register"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email")
    password = request.form.get("password")

    if not email or not password:
        flash("Email y contraseña son requeridos", "warning")
        return redirect(url_for("login"))

    try:
        resp = api_post("/login", json={"email": email, "password": password})
        if resp.status_code == 200:
            data = resp.json()
            token = data.get("token") or data.get("access_token") or data.get("accessToken")
            if not token:
                flash("El servidor no devolvió un token válido", "danger")
                return redirect(url_for("login"))

            session.permanent = True
            session["token"] = token
            flash("Inicio de sesión exitoso", "success")
            return redirect(url_for("users"))
        else:
            flash("Credenciales inválidas", "danger")
            return redirect(url_for("login"))
    except Exception:
        logger.exception("Error durante la autenticación")
        flash("Error de conexión con el servidor", "danger")
        return redirect(url_for("login"))


@app.route("/logout")
def logout():
    session.clear()
    flash("Sesión cerrada correctamente", "info")
    return redirect(url_for("login"))


@app.route("/users")
def users():
    token = session.get("token")
    if not token:
        return redirect(url_for("login"))

    try:
        resp = api_get("/users", token=token)
        if resp.status_code == 200:
            users_list = resp.json()
            return render_template("users.html", users=users_list)
        elif resp.status_code == 401:
            flash("Token expirado o inválido. Vuelve a iniciar sesión.", "warning")
            session.clear()
            return redirect(url_for("login"))
        else:
            flash("Error al obtener usuarios", "danger")
            return render_template("users.html", users=[])
    except Exception:
        logger.exception("Error al comunicarse con la API")
        flash("Error de conexión con el servidor", "danger")
        return render_template("users.html", users=[])


@app.route("/health")
def health():
    return {"status": "ok"}, 200


# --- Run ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=False)
