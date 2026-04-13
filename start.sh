#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE="docker-compose.judge.yaml"
ENV_FILE=".env.judge"
ENV_EXAMPLE=".env.judge.example"
IMAGE_NAME="artyomtula1/open-webui:latest"

echo "╔══════════════════════════════════════════╗"
echo "║         GPTHub — быстрый запуск          ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# ── 1. Проверим Docker ───────────────────────────────────
if ! command -v docker &>/dev/null; then
  echo "❌  Docker не найден. Установите Docker Desktop: https://www.docker.com/products/docker-desktop"
  exit 1
fi

if ! docker info &>/dev/null; then
  echo "❌  Docker не запущен. Запустите Docker Desktop и повторите."
  exit 1
fi

echo "✅  Docker OK"

# ── 2. .env.judge ────────────────────────────────────────
if [ ! -f "$ENV_FILE" ]; then
  cp "$ENV_EXAMPLE" "$ENV_FILE"
fi

# Если ключ не заполнен — спросить
CURRENT_KEY=$(grep -E '^MWS_API_KEY=' "$ENV_FILE" | cut -d= -f2 | tr -d '[:space:]"'"'" || true)

if [ -z "$CURRENT_KEY" ]; then
  echo ""
  echo "🔑  Введите ваш MWS API ключ (начинается с 'sk-'):"
  read -r user_key

  if [ -z "$user_key" ]; then
    echo "❌  Ключ не введён. Откройте .env.judge и заполните MWS_API_KEY вручную."
    exit 1
  fi

  # Обновить ключ в файле (работает на macOS и Linux)
  if [[ "$OSTYPE" == "darwin"* ]]; then
    sed -i '' "s|^MWS_API_KEY=.*|MWS_API_KEY=${user_key}|" "$ENV_FILE"
  else
    sed -i "s|^MWS_API_KEY=.*|MWS_API_KEY=${user_key}|" "$ENV_FILE"
  fi

  echo "✅  API ключ сохранён в $ENV_FILE"
fi

# ── 3. Сборка / запуск ───────────────────────────────────
echo ""

# Проверить, есть ли уже готовый образ на Docker Hub
if docker pull "$IMAGE_NAME" 2>/dev/null; then
  echo "✅  Образ загружен с Docker Hub (~30 сек)"
else
  echo "🔨  Образ не найден на Docker Hub — собираем локально (~10 мин)..."
  docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" build
fi

echo ""
echo "🚀  Запускаем GPTHub..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d

echo ""
echo "════════════════════════════════════════════"
echo "  ✅  GPTHub запущен!"
echo ""
echo "  🌐  Открывайте в браузере:"
echo "      http://localhost:3000"
echo ""
echo "  📋  Зарегистрируйтесь — первый пользователь"
echo "      автоматически становится администратором."
echo ""
echo "  Чтобы остановить: docker compose -f docker-compose.judge.yaml down"
echo "════════════════════════════════════════════"
