from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
import requests

# ----------------------------------------
# Configuración del Flask app
# ----------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static")
)
app.secret_key = "frontendsecret"

# URL del backend desplegado en Railway
BACKEND_URL = os.getenv("BACKEND_URL", "https://motosapi-production.up.railway.app")

# ----------------------------------------
# Página principal
# ----------------------------------------
@app.route("/")
def home():
    # Redirige a dashboard si ya hay sesión activa
    if "email" in session and "token" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

# ----------------------------------------
# Registro de usuario
# ----------------------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        data = {"email": email, "password": password}
        try:
            response = requests.post(f"{BACKEND_URL}/register", json=data)
            if response.status_code == 201:
                flash("Usuario registrado exitosamente, ahora inicia sesión.", "success")
                return redirect(url_for("login"))
            elif response.status_code == 409:
                flash("El correo ya está registrado.", "warning")
            else:
                flash("Error al registrar usuario.", "danger")
        except requests.exceptions.RequestException:
            flash("Error de conexión con el backend.", "danger")
    return render_template("register.html")

# ----------------------------------------
# Inicio de sesión
# ----------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    # Redirige si ya hay sesión activa
    if "email" in session and "token" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        data = {"email": email, "password": password}
        try:
            response = requests.post(f"{BACKEND_URL}/login", json=data)
            # Ver qué devuelve el backend
            print("RESPUESTA LOGIN:", response.text)
            if response.status_code == 200:
                token = response.json().get("token")
                if token:
                    # Guardar email y token en la sesión
                    session["email"] = email
                    session["token"] = token
                    flash("Inicio de sesión exitoso.", "success")
                    return redirect(url_for("dashboard"))
                else:
                    flash("No se recibió token de autenticación.", "danger")
            else:
                flash("Credenciales incorrectas.", "danger")
        except requests.exceptions.RequestException:
            flash("Error de conexión con el backend.", "danger")
    return render_template("login.html")

# ----------------------------------------
# Dashboard
# ----------------------------------------
@app.route("/dashboard")
def dashboard():
    if "email" not in session or "token" not in session:
        flash("Debes iniciar sesión para acceder al dashboard.", "warning")
        return redirect(url_for("login"))

    headers = {"Authorization": f"Bearer {session.get('token', '')}"}

    try:
        response = requests.get(f"{BACKEND_URL}/motorcycles/tabla", headers=headers)
        if response.status_code == 200:
            motos_html = response.text
        elif response.status_code == 401:
            flash("Token inválido o expirado. Inicia sesión nuevamente.", "danger")
            return redirect(url_for("logout"))
        else:
            motos_html = "<p>Error al cargar las motos.</p>"
            flash("Error al cargar las motos.", "danger")
    except requests.exceptions.RequestException:
        motos_html = "<p>No se pudo conectar al backend.</p>"
        flash("No se pudo conectar al backend.", "danger")

    return render_template("users.html", email=session["email"], motos_html=motos_html)

# ----------------------------------------
# Logout
# ----------------------------------------
@app.route("/logout")
def logout():
    session.pop("email", None)
    session.pop("token", None)
    flash("Has cerrado sesión.", "success")
    return redirect(url_for("login"))

# ----------------------------------------
# Ejecutar app
# ----------------------------------------
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)
