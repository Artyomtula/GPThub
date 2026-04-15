# GPThub

AI-чат на базе MWS GPT: текст, изображения, голос, RAG, память.

## Быстрый старт

**Требования:** Docker Desktop, API-ключ MWS GPT.

### macOS / Linux

```bash
git clone https://git.truetecharena.ru/tta/true-tech-hack2026-gpthub/team-3d89e9b6/task-repo.git && cd open-webui
sh start.sh
```

### Windows (CMD)

```bat
git clone https://git.truetecharena.ru/tta/true-tech-hack2026-gpthub/team-3d89e9b6/task-repo.git && cd open-webui && start.bat
```

Скрипт спросит API-ключ, создаст `.env` и запустит сборку.  
Первый запуск ~5-10 мин. После открыть **http://localhost:3000**

> Важно: сразу после сборки страница на `http://localhost:3000` может временно показывать `Not Found`.  
> Это нормально: бэкенд ещё поднимается. Подождите 30-120 секунд и обновите страницу.

Остановить: `docker compose down`
