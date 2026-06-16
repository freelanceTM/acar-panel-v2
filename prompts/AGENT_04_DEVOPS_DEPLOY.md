# Агент 04: DevOps, Deploy и Cloudflare

## Задача
Подготовить production-ready деплой: Docker, Nginx, SSL, Cloudflare rules, CI/CD, бэкап БД.

## Текущее состояние
- Есть `docker-compose.yml`, `Dockerfile`, `nginx/nginx.conf`.
- SQLite для MVP, но нужно переключение на PostgreSQL.

## Технические требования
1. **PostgreSQL**:
   - Добавить `db` сервис в `docker-compose.yml`.
   - Миграции через `alembic` (инициализировать, создать baseline миграцию на основе `app/models.py`).
   - Скрипт `scripts/init_db.py` для создания первой миграции и применения.
2. **Nginx + SSL**:
   - Генерация самоподписанного сертификата для dev. Для production — `certbot`/`acme.sh` или Cloudflare Origin CA.
   - Nginx rate limiting (limit_req) на `/sub/` — 60r/m на IP.
   - Скрытие версии nginx, заголовков `Server`.
3. **Cloudflare**:
   - Документ `CLOUDFLARE_SETUP.md` с правилами:
     - SSL: Full (strict).
     - Page Rule: `yourdomain.com/sub/*` — Bypass Cache (для подписок, чтобы не кэшировались в CF).
     - Firewall Rule: Rate Limiting 100 requests/10min на `/sub/*` (как дополнительная защита).
     - DNS: A-record -> VPS IP (оранжевая облака включена).
4. **Health checks**:
   - `GET /health` — проверка DB + Redis connectivity.
   - Docker `healthcheck` для app и worker.
5. **Monitoring / Logs**:
   - `docker-compose` с `prometheus` + `grafana` (опционально, но лучше иметь метрики).
   - Или просто `json` логирование через uvicorn.
6. **Backup**:
   - Скрипт `scripts/backup.sh` — дамп SQLite/PostgreSQL + `tar` папки `data/` в S3-compatible storage (или просто `/backups` volume с cron). Для MVP — volume + cron ежедневно.
7. **Secrets**:
   - `.env` не должен быть в git. Создать `.env.example`.
   - Использовать `docker secrets` или просто `env_file` в compose.

## Исходные файлы
- `docker-compose.yml`, `Dockerfile`, `nginx/nginx.conf`.
- `app/main.py` — добавить `/health` endpoint.
- Новые: `scripts/backup.sh`, `CLOUDFLARE_SETUP.md`, `.env.example`, `alembic.ini` + `alembic/`.

## Выход
- Работающий `docker-compose up` с PostgreSQL + Redis + Nginx.
- Инструкция по деплою на VPS (Ubuntu 22.04) с Cloudflare.
