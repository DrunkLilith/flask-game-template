"""Клиент актуального API игровой сессии LingvoGameOs."""

import os

from flask import request, session
import requests

from constants import API_URL


TIMEOUT = 10


class ApiError(Exception):
    """Ошибка сети, HTTP, конфигурации или формата ответа портала."""


def _capture_game_session() -> tuple[int | None, str | None]:
    """Сохраняет ``session``/``token`` из query точки входа портала."""
    raw_session_id = request.args.get("session")
    if raw_session_id is not None:
        if not raw_session_id.isdigit() or int(raw_session_id) <= 0:
            raise ApiError("Портал передал некорректный ID игровой сессии.")
        return int(raw_session_id), request.args.get("token")
    return session.get("game_session_id"), session.get("game_session_token")


def resolve_game_session() -> dict | None:
    """Проверяет HMAC, GameId и сохраняет профиль пользователя портала."""
    game_session_id, token = _capture_game_session()
    if not game_session_id:
        return None
    if not token:
        raise ApiError("Портал не передал токен игровой сессии.")

    expected_game_id = os.environ.get("LINGVO_GAME_ID")
    if not expected_game_id or not expected_game_id.isdigit():
        raise ApiError("LINGVO_GAME_ID не настроен для этой игры.")

    try:
        response = requests.post(
            f"{API_URL}/game/session/resolve",
            json={"gameSessionId": game_session_id, "token": token},
            timeout=TIMEOUT,
        )
    except requests.RequestException as exc:
        raise ApiError(f"Портал недоступен: {exc}") from exc

    if response.status_code == 401:
        raise ApiError("Портал отклонил подпись игровой сессии.")
    if response.status_code == 404:
        raise ApiError("Игровая сессия не найдена.")
    if response.status_code != 200:
        raise ApiError(f"Ошибка API ({response.status_code}): {response.text}")

    try:
        data = response.json()
    except requests.JSONDecodeError as exc:
        raise ApiError("Портал вернул некорректный JSON.") from exc

    if not isinstance(data, dict) or not data.get("valid") or not data.get("userId"):
        raise ApiError("Портал вернул некорректную игровую сессию.")
    if str(data.get("gameId")) != expected_game_id:
        raise ApiError("Игровая сессия выдана для другой игры.")

    session["game_session_id"] = game_session_id
    session["game_session_token"] = token
    session["portal_user_id"] = data["userId"]
    session["portal_user_name"] = data.get("userName") or "Игрок"
    session["portal_total_points"] = int(data.get("totalUserPoints", 0))
    return data


def post_points(amount: int) -> int:
    """Однократно отправляет итог партии по подтверждённой игровой сессии."""
    game_session_id = session.get("game_session_id")
    token = session.get("game_session_token")
    if not game_session_id or not token:
        raise ApiError("Игра запущена не с портала: сессия не выдана.")
    if not isinstance(amount, int) or amount <= 0:
        raise ApiError("Количество баллов должно быть положительным целым числом.")

    try:
        response = requests.post(
            f"{API_URL}/score",
            json={"gameSessionId": game_session_id, "score": amount, "token": token},
            timeout=TIMEOUT,
        )
    except requests.RequestException as exc:
        raise ApiError(f"Портал недоступен: {exc}") from exc

    if response.status_code != 200:
        raise ApiError(f"Ошибка API ({response.status_code}): {response.text}")

    try:
        data = response.json()
    except requests.JSONDecodeError as exc:
        raise ApiError("Портал вернул некорректный JSON.") from exc
    if not isinstance(data, dict) or "newTotalPoints" not in data:
        raise ApiError("API вернул некорректный ответ на начисление баллов.")

    session["portal_total_points"] = int(data["newTotalPoints"])
    return session["portal_total_points"]
