## Описание

- **FastAPI** — основной HTTP API
- **Celery** — асинхронная загрузка партий (через Redis)
- **Redis** — брокер сообщений для Celery и кэш
- **PostgreSQL** — хранение пользователей и партий
- **Docker Compose** — быстрый запуск и деплой

- Авторизация через Lichess OAuth2
- Получение профиля пользователя и рейтингов
- Синхронизация и хранение истории партий
- Пагинация, фильтрация, защита от дубликатов
- JWT-авторизация

## Архитектура

- FastAPI — REST API
- Celery — фоновая синхронизация партий
- Redis — брокер задач и кэш
- PostgreSQL — база данных
- Docker Compose — orchestration

## Быстрый старт

1. Клонируйте репозиторий:
   ```bash
   git clone https://github.com/Alishkoo/Lichess_backend.git
   cd Lichess_backend
   ```
2. Скопируйте и настройте переменные окружения:
   ```bash
   cp .env.example .env
   # Заполните .env
   ```
3. Запустите сервисы:
   ```bash
   docker compose up --build
   ```

## Основные переменные .env

- `DATABASE_URL` — строка подключения к PostgreSQL
- `REDIS_URL` — строка подключения к Redis
- `LICHESS_CLIENT_ID` — OAuth2 client ID
- `LICHESS_REDIRECT_URI` — callback URL для Lichess
- `SECRET_KEY` — секрет для JWT
- `FRONTEND_URL` — адрес фронтенда для редиректа

## API

- `POST /auth/login` — авторизация через Lichess
- `GET /auth/me` — профиль пользователя
- `POST /auth/logout` — выход
- `POST /api/games/sync` — синхронизация партий
- `GET /api/games` — список партий (пагинация, фильтрация)
- `GET /api/games/stats` — статистика по партиям

- Все сервисы запускаются через Docker
- Для production используйте свои значения в .env
- Для фронтенда используйте переменную FRONTEND_URL
