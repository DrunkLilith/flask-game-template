import os

import requests

from flask import Flask, redirect, render_template, request, session, url_for
from werkzeug.middleware.proxy_fix import ProxyFix

from constants import APP_SECRET_KEY

from api_rudzyng import get_game_session, login as API_login, get_points, post_points

app = Flask(__name__)
app.secret_key = APP_SECRET_KEY
path_base = os.environ.get("GAME_PATH_BASE", "").rstrip("/")
app.config["APPLICATION_ROOT"] = path_base or "/"
app.config["SESSION_COOKIE_PATH"] = path_base or "/"
app.config["SESSION_COOKIE_NAME"] = os.environ.get(
    "GAME_COOKIE_NAME", "lingvogameos_flask_template_session"
)
app.wsgi_app = ProxyFix(
    app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
)


@app.route("/")
def index():
    # Также поддерживаем открытие корня с query для локальной отладки.
    get_game_session()
    user_id = session.get("user_id", None)
    user_points = session.get("user_points", None)
    error = session.pop("error", None)

    return render_template(
        "index.html", user_id=user_id, points=user_points, error=error
    )


@app.route("/start")
def start():
    """Точка входа портала: сохраняет session/token и убирает их из URL."""
    get_game_session()
    return redirect(url_for("index"))



@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email")
    password = request.form.get("password")

    if not (email and password):
        return render_template("login.html", error={"message": "ERROR!!!"})

    try:
        API_login(email, password)
    except requests.exceptions.RequestException as e:
        print(f"Ошибка API login: {e}")
        return render_template("login.html", error={"message": "ERROR!!!"})
    except ValueError:
        return render_template(
            "login.html", error={"message": "Неверный ответ от сервера"}
        )

    return redirect(url_for("index"))


@app.route("/logout")
def logout():
    session.pop("user_id", None)
    session.pop("user_points", None)

    return redirect(url_for("index"))


@app.route("/points", methods=["GET", "POST"])
def points():
    if request.method == "GET":
        session["user_points"] = get_points()
    elif request.method == "POST":
        try:
            points = int(request.form.get("points", 0))
            session["user_points"] = post_points(points)
        except Exception as e:
            session["error"] = str(e)

    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("GAME_PORT", "5000")),
    )
