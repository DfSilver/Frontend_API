from flask import Flask, render_template, request, redirect, url_for, session, flash
import requests

app = Flask(__name__)
app.secret_key = "frontendsecret"

# URL del backend en Railway
BACKEND_URL = "https://motosapi-production.up.railway.app"

# ------------------ HOME ------------------
@app.route("/")
def home():
    if "email" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

# ------------------ REGISTRO ------------------
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

# ------------------ LOGIN ------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        data = {"email": email, "password": password}
        try:
            response = requests.post(f"{BACKEND_URL}/login", json=data)
            if response.status_code == 200:
                session["email"] = email
                flash("Inicio de sesión exitoso.", "success")
                return redirect(url_for("dashboard"))
            else:
                flash("Credenciales incorrectas.", "danger")
        except requests.exceptions.RequestException:
            flash("Error de conexión con el backend.", "danger")
    return render_template("login.html")

# ------------------ DASHBOARD ------------------
@app.route("/dashboard")
def dashboard():
    if "email" not in session:
        return redirect(url_for("login"))

    try:
        # Pedimos JSON de motos al backend
        response = requests.get(f"{BACKEND_URL}/motorcycles")
        if response.status_code == 200:
            motos = response.json()  # lista de diccionarios
        else:
            motos = []
            flash("Error al cargar las motos.", "danger")
    except requests.exceptions.RequestException:
        motos = []
        flash("No se pudo conectar al backend.", "danger")

    return render_template("users.html", email=session["email"], motos=motos)

# ------------------ LOGOUT ------------------
@app.route("/logout")
def logout():
    session.pop("email", None)
    flash("Has cerrado sesión.", "success")
    return redirect(url_for("login"))

# ------------------ RUN SERVER ------------------
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)
