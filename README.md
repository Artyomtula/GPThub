# GPTHub (based on Open WebUI)

Короткий гайд по запуску проекта для разработки и продакшена.

## Требования

- macOS/Linux
- Node.js `18-22` и npm
- Python `3.11` или `3.12` (Python `3.13` не поддерживается)
- Docker + Docker Compose (для production)

## Development

Запускать фронт и бэк нужно отдельно, в двух терминалах.

### 1) Frontend

Из корня репозитория:

```bash
cp -n .env.example .env
npm install
npm run build
npm run dev
```

Фронт dev-сервер по умолчанию: `http://localhost:5173`.

### 2) Backend

Во втором терминале:

```bash
cd backend
python3.12 -m venv venv
source venv/bin/activate
pip install -U pip setuptools wheel
pip install -r requirements.txt
sh dev.sh
```

Если `python3.12` не найден, установите его и повторите:

```bash
brew install python@3.12
```

Бэкенд поднимается на `http://localhost:8080`.

Открывать приложение для полной работы нужно через backend URL: `http://localhost:8080`.

## Production

### Вариант A: Docker Compose (рекомендуется)

Из корня репозитория:

```bash
docker compose up -d --build
```

По умолчанию:
- Open WebUI: `http://localhost:3000`
- Ollama (внутри compose сети)

Остановить:

```bash
docker compose down
```

### Вариант B: Собрать и запустить только WebUI контейнер

```bash
docker build -t gpthub-openwebui:prod .
docker run -d \
  -p 3000:8080 \
  -v open-webui:/app/backend/data \
  --name gpthub-openwebui \
  --restart unless-stopped \
  gpthub-openwebui:prod
```

## Частые проблемы

### `No matching distribution found ... rapidocr-onnxruntime`

Причина: используется неподдерживаемая версия Python (обычно `3.13`).

Решение: пересоздать venv на Python `3.11`/`3.12` и заново установить зависимости.

### `uvicorn: command not found`

Причина: зависимости не установились до конца.

Решение:

```bash
source backend/venv/bin/activate
pip install -r backend/requirements.txt
```

## Структура репозитория

- `src/` — frontend (Svelte/SvelteKit)
- `backend/` — backend (FastAPI)
- `Dockerfile`, `docker-compose.yaml` — production/runtime
