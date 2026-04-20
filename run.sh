#!/bin/bash

image_name="gpthub"
container_name="gpthub"
host_port="${OPEN_WEBUI_PORT:-3000}"
container_port=8080

docker build -t "$image_name" .
docker stop "$container_name" &>/dev/null || true
docker rm "$container_name" &>/dev/null || true

docker run -d -p "$host_port":"$container_port" \
    --add-host=host.docker.internal:host-gateway \
    -v "${image_name}:/app/backend/data" \
    --name "$container_name" \
    --restart unless-stopped \
    --env-file .env \
    "$image_name"

docker image prune -f
