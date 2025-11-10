# app.py
import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import timedelta

from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, session, flash
import requests

# --- Cargar variables de entorno ---
load_dotenv()  # lee .env en la raiz del proyecto

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:5000")
SECRET_KEY = os.getenv("SECRET_KEY", "change_me_in_production")
LOG_FILE = os.getenv("LOG_FILE", "frontend.log")

# --- Configurar la app Flask ---
app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=2)

# --- Logging profesional: consola + archivo con rotación ---
logger = logging.getLogger("motos_frontend")
logger.setLevel(logging.INFO)

# Console handler
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
ch_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
ch.setFormatter(ch_formatter)
logger.addHandler(ch)

# File handler rotativo
fh = RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3)
fh.setLevel(logging.INFO)
fh.setFormatter(ch_formatter)
logger.addHandler(fh)

logger.info("Frontend starting. API_BASE_URL=%s", API_BASE_URL)


# ---- Helpers ----
def api_post(path: str, json=None, token: str | None = None):
    """POST request to backend API with optional bearer token."""
    url = f"{API_BASE_URL.rstrip('/')}/{path.lstrip('/')}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    logger.debug("POST %s (token=%s)", url, bool(token))
    resp = requests.post(url, json=json, headers=headers, timeout=10)
    return resp


def api_get(path: str, token: str | None = None, params: dict | None = None):
    url = f"{API_BASE_URL.rstrip('/')}/{path.lstrip('/')}"
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    logger.debug("GET %s (token=%s)", url, bool(token))
    resp = requests.get(url, headers=headers, params=params, timeout=10)
    return resp


# ---- Routes ----

@app.route("/")
def index():
    # Si ya hay token en sesión, ir a users; si no, ir a login
    if session.get("token"):
        return redirect(url_for("users"))
    return redirect(url_for("login"))


# ------- REGISTER -------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    # POST -> enviar al API
    email = request.form.get("email")
    password = request.form.get("password")
    role = request.form.get("role", "user")

    if not email or not password:
        flash("Email y contraseña son obligatorios", "warning")
        return redirect(url_for("register"))

    try:
        logger.info("Register attempt for %s", email)
        resp = api_post("/register", json={"email": email, "password": password, "role": role})
        if resp.status_code in (200, 201):
            flash("Registro exitoso. Ahora inicia sesión.", "success")
            return redirect(url_for("login"))
        else:
            logger.warning("Register failed %s -> %s", resp.status_code, resp.text)
            flash(f"Registro fallido: {resp.json().get('error', resp.text)}", "danger")
            return redirect(url_for("register"))
    except Exception as e:
        logger.exception("Error registrando usuario")
        flash("Error de conexión con el servidor", "danger")
        return redirect(url_for("register"))


# ------- LOGIN -------
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
        logger.info("Login attempt for %s", email)
        resp = api_post("/login", json={"email": email, "password": password})
        if resp.status_code == 200:
            data = resp.json()
            # Esperamos que la API devuelva el token en 'token' o 'access_token'
            token = data.get("token") or data.get("access_token") or data.get("accessToken")
            if not token:
                logger.error("Login succeeded but no token returned: %s", data)
                flash("Servidor no devolvió token", "danger")
                return redirect(url_for("login"))

            session.permanent = True
            session["token"] = token
            logger.info("Login success for %s", email)
            return redirect(url_for("users"))
        else:
            logger.warning("Login failed %s -> %s", resp.status_code, resp.text)
            flash("Credenciales inválidas", "danger")
            return redirect(url_for("login"))
    except Exception:
        logger.exception("Error during login request")
        flash("Error de conexión con el servidor", "danger")
        return redirect(url_for("login"))


# ------- LOGOUT -------
@app.route("/logout")
def logout():
    user_info = session.get("user_email", "unknown")
    session.clear()
    logger.info("User logged out: %s", user_info)
    flash("Sesión cerrada", "info")
    return redirect(url_for("login"))


# ------- USERS (protegido: necesita token) -------
@app.route("/users")
def users():
    token = session.get("token")
    if not token:
        logger.info("Access to /users without token -> redirect to login")
        return redirect(url_for("login"))

    try:
        resp = api_get("/users", token=token)
        if resp.status_code == 200:
            users_list = resp.json()
            # optional: store short info in session
            return render_template("users.html", users=users_list)
        elif resp.status_code == 401:
            logger.warning("Token invalid/expired -> redirect login")
            flash("Token inválido o expirado. Inicia sesión de nuevo.", "warning")
            session.clear()
            return redirect(url_for("login"))
        else:
            logger.error("Failed fetching users %s -> %s", resp.status_code, resp.text)
            flash("Error al obtener usuarios", "danger")
            return render_template("users.html", users=[])
    except Exception:
        logger.exception("Error fetching users from API")
        flash("Error de conexión con el servidor", "danger")
        return render_template("users.html", users=[])


# ------- Ruta para debug sencillo (no expuesta en producción) -------
@app.route("/health")
def health():
    return {"status": "ok"}, 200


# ---- Run the app ----
if __name__ == "__main__":
    # No usar reloader en production; aquí es dev
    app.run(host="0.0.0.0", port=3000, debug=False)
