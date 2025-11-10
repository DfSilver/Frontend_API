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
