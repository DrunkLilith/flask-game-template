import os

from flask import Flask, redirect, render_template, request, session, url_for
from werkzeug.middleware.proxy_fix import ProxyFix

from constants import APP_SECRET_KEY
from api_rudzyng import ApiError, post_points, resolve_game_session


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
    # Поддерживаем прямое открытие корня с query для локальной отладки.
    if request.args.get("session") is not None:
        try:
            resolve_game_session()
        except ApiError as exc:
            return str(exc), 401

    return render_template(
        "index.html",
        user_name=session.get("portal_user_name"),
        points=session.get("portal_total_points"),
        has_game_session=bool(session.get("game_session_id")),
        error=session.pop("error", None),
    )


@app.route("/start")
def start():
    """Проверенная точка входа портала; query затем убирается из URL."""
    try:
        resolve_game_session()
    except ApiError as exc:
        return str(exc), 401
    return redirect(url_for("index"))


@app.route("/points", methods=["POST"])
def points():
    try:
        amount = int(request.form.get("points", 0))
        post_points(amount)
    except (ApiError, TypeError, ValueError) as exc:
        session["error"] = str(exc)
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("GAME_PORT", "5000")),
    )
