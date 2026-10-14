# Flask-шаблон игры LingvoGameOs

Шаблон уже поддерживает актуальный контракт портала:

- запуск через `/start?session=<id>&token=<hmac>`;
- проверку сессии через `POST /api/game/session/resolve` и привязку к `LINGVO_GAME_ID`;
- получение имени и общего счёта только из подтверждённой сессии;
- отправку результата в `POST /api/score` по игровой сессии;
- публикацию игры под внутренним маршрутом `/games/<slug>`;
- отдельные cookie path и cookie name для каждой игры;
- корректные ссылки за reverse proxy через `X-Forwarded-Prefix`.

## Локальный запуск

`.env.example` перечисляет необходимые настройки. Общий `stack.ps1` читает
корневой рабочий `.env` проекта и передаёт значения контейнеру; сам шаблон
никогда не загружает `.env.example`. Для отдельного запуска задайте переменные
окружения процесса:

```powershell
$env:LINGVO_API_URL = "http://localhost:5001/api"
$env:LINGVO_GAME_ID = "123" # реальный ID игры в БД портала
$env:APP_SECRET_KEY = "replace-with-a-long-random-value"
$env:GAME_PORT = "5000"
python -m pip install -r requirements.txt
python server.py
```

Откройте `http://localhost:5000/start?session=1&token=test-token`.

## Подключение к общему Docker-стеку

Для сервиса игры задайте:

```yaml
environment:
  LINGVO_API_URL: http://api:8080/api
  LINGVO_GAME_ID: "123"
  APP_SECRET_KEY: ${GAMES_APP_SECRET}
  GAME_PORT: "8080"
  GAME_PATH_BASE: /games/my-game
  GAME_COOKIE_NAME: lingvogameos_my_game_session
expose:
  - "8080"
```

Порт игры публиковать на хост не требуется: портал проксирует её по
`/games/my-game`, а контейнер остаётся доступен только во внутренней сети.

## Docker

Для автономного локального запуска создайте рабочий `.env` и поднимите игру
одной командой:

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Игра будет доступна на `http://localhost:8080`. Порт хоста можно изменить через
`GAME_HOST_PORT` в `.env`. Контейнер запускает приложение через Gunicorn, от
непривилегированного пользователя и содержит встроенный healthcheck.

`compose.yaml` очищает `GAME_PATH_BASE` только для автономного запуска. В
составе LingvoGameOs передайте `/games/<slug>`, уникальный `GAME_COOKIE_NAME`,
реальный `LINGVO_GAME_ID` и внутренний URL API, а наружу публикуйте только порт
портала.
