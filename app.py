import os
import logging
from datetime import timedelta
from logging.handlers import RotatingFileHandler
from flask import Flask, render_template, request, redirect, url_for, session, flash
from dotenv import load_dotenv
import requests

# --- Configuración base ---
load_dotenv()

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:5000")
SECRET_KEY = os.getenv("SECRET_KEY", "frontendsecret123")
LOG_FILE = os.getenv("LOG_FILE", "frontend.log")

app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=2)

# --- Logging ---
logger = logging.getLogger("frontend")
logger.setLevel(logging.INFO)
fh = RotatingFileHandler(LOG_FILE, maxBytes=5*1024*1024, backupCount=3)
fh.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(fh)


# --- Helpers ---
def api_get(path, token=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return requests.get(f"{API_BASE_URL}{path}", headers=headers, timeout=10)


def api_post(path, json=None):
    return requests.post(f"{API_BASE_URL}{path}", json=json, timeout=10)


# --- Rutas ---
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        if not email or not password:
            flash("Correo y contraseña requeridos", "warning")
            return redirect(url_for("register"))

        try:
            res = api_post("/register", {"email": email, "password": password})
            if res.status_code in (200, 201):
                flash("Registro exitoso. Ahora inicia sesión.", "success")
                return redirect(url_for("login"))
            else:
                flash("Error al registrarse", "danger")
        except Exception as e:
            flash("Error conectando con el servidor", "danger")
            logger.exception(e)

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        try:
            res = api_post("/login", {"email": email, "password": password})
            if res.status_code == 200:
                data = res.json()
                token = data.get("token") or data.get("access_token")
                if token:
                    session["token"] = token
                    flash("Inicio de sesión exitoso", "success")
                    return redirect(url_for("motos"))
                else:
                    flash("El servidor no devolvió token", "danger")
            else:
                flash("Credenciales inválidas", "danger")
        except Exception as e:
            flash("Error conectando con el backend", "danger")
            logger.exception(e)

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Sesión cerrada", "info")
    return redirect(url_for("index"))


@app.route("/motos")
def motos():
    token = session.get("token")
    if not token:
        flash("Inicia sesión para ver la base de datos.", "warning")
        return redirect(url_for("login"))

    try:
        res = api_get("/motorcycles/tabla", token)
        if res.status_code == 200:
            return res.text  # la tabla HTML generada por el backend
        else:
            flash("No se pudo cargar la tabla de motos.", "danger")
            return redirect(url_for("index"))
    except Exception as e:
        logger.exception(e)
        flash("Error al conectar con el backend.", "danger")
        return redirect(url_for("index"))


# --- Health check ---
@app.route("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
