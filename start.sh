#!/bin/bash
set -e

echo "=== GPThub Quick Start ==="

# Create .env if not exists
if [ ! -f .env ]; then
  if [ ! -f .env.example ]; then
    echo "ERROR: .env.example not found"
    exit 1
  fi
  cp .env.example .env

  read -p "Enter MWS API key: " API_KEY
  if [ -z "$API_KEY" ]; then
    echo "ERROR: API key is required"
    exit 1
  fi

  # Set all API key fields to the provided key
  sed -i.bak \
    -e "s|^MWS_API_KEY=''|MWS_API_KEY='$API_KEY'|" \
    -e "s|^OPENAI_API_KEYS=''|OPENAI_API_KEYS='$API_KEY'|" \
    -e "s|^IMAGES_OPENAI_API_KEY=''|IMAGES_OPENAI_API_KEY='$API_KEY'|" \
    -e "s|^AUDIO_STT_OPENAI_API_KEY=''|AUDIO_STT_OPENAI_API_KEY='$API_KEY'|" \
    -e "s|^RAG_OPENAI_API_KEY=''|RAG_OPENAI_API_KEY='$API_KEY'|" \
    .env
  rm -f .env.bak
  echo ".env created with your API key"
fi

echo ""
echo "Starting GPThub (first build may take 5-10 min)..."
echo "App will be available at http://localhost:3000"
echo ""

docker compose up --build
