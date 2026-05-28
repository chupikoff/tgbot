# 🤖 Personal Telegram Bot

Личный бот-помощник на базе Telegram с системой ролей, заметками, мониторингом сервера и управлением торрентами.

## Стек

- Python 3.12 + aiogram 3
- PostgreSQL + SQLAlchemy 2
- Redis
- Docker Compose

## Роли

| Роль | Описание |
|---|---|
| 👑 Owner | Полный доступ |
| 🔧 Admin | Управление пользователями, мониторинг, торренты |
| 👤 User | Заметки, медиатека |
| 👣 Guest | Только главное меню |

## Функционал

- ✅ Авторизация по Telegram ID
- ✅ Система ролей (owner / admin / user / guest)
- ✅ Заметки (личные и общие, категории, поиск)
- ✅ Медиатека (видео по file_id)
- ✅ Мониторинг сервера (CPU, RAM, диск, температура)
- ✅ Управление сервисами (transmission, samba, minidlna, docker)
- ✅ Управление торрентами (Transmission)
- ✅ Бэкапы (база данных, конфиги, автобэкап в 03:00)
- 🔜 Мониторинг Docker контейнеров
- 🔜 Уведомления мониторинга
- 🔜 AI /ask

## Запуск

```bash
cp .env.example .env
# заполни .env своими данными
docker compose up --build -d
```

## Установка на хост

Перед запуском Docker необходимо установить на хост два файла для управления сервисами.

### 1. HTTP API для управления сервисами

Создай файл `/usr/local/bin/bot-service-api.py`:

```python
#!/usr/bin/env python3
from http.server import HTTPServer, BaseHTTPRequestHandler
import subprocess
import json
import urllib.parse

ALLOWED_SERVICES = ["transmission-daemon", "smbd", "minidlna", "docker"]
ALLOWED_ACTIONS = ["status", "restart", "start", "stop"]
API_TOKEN = "вставь_свой_токен"

class ServiceHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        token = params.get("token", [""])[0]
        if token != API_TOKEN:
            self.send_response(403)
            self.end_headers()
            self.wfile.write(b'{"error": "Forbidden"}')
            return

        action = params.get("action", [""])[0]
        service = params.get("service", [""])[0]

        if action not in ALLOWED_ACTIONS:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'{"error": "Invalid action"}')
            return

        if service not in ALLOWED_SERVICES:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'{"error": "Invalid service"}')
            return

        try:
            if action == "status":
                result = subprocess.run(
                    ["systemctl", "is-active", service],
                    capture_output=True, text=True, timeout=5
                )
                output = result.stdout.strip()
            else:
                result = subprocess.run(
                    ["systemctl", action, service],
                    capture_output=True, text=True, timeout=10
                )
                output = "OK" if result.returncode == 0 else result.stderr.strip()

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"result": output}).encode())

        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def log_message(self, format, *args):
        pass

if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", 7777), ServiceHandler)
    print("Service API running on port 7777")
    server.serve_forever()
```

Сделай исполняемым:
```bash
sudo chmod +x /usr/local/bin/bot-service-api.py
```

### 2. Systemd сервис

Создай файл `/etc/systemd/system/bot-service-api.service`:

```ini
[Unit]
Description=Bot Service API
After=network.target

[Service]
ExecStart=/usr/bin/python3 /usr/local/bin/bot-service-api.py
Restart=always
User=root

[Install]
WantedBy=multi-user.target
```

Запусти:
```bash
sudo systemctl daemon-reload
sudo systemctl enable bot-service-api
sudo systemctl start bot-service-api
```

### 3. Токен

Сгенерируй токен:
```bash
openssl rand -hex 32
```

Вставь его в:
- `/usr/local/bin/bot-service-api.py` — параметр `API_TOKEN`
- `/home/chpk/tgbot/.env` — параметр `SERVICE_API_TOKEN`

## Структура

```
bot/
├── handlers/    # команды и кнопки
├── services/    # бизнес-логика
├── models/      # таблицы БД
├── middlewares/ # авторизация
├── workers/     # фоновые задачи
└── db/          # подключение к БД
```
