# Агент 01: Аутентификация и Безопасность

## Задача
Доработать модуль аутентификации и безопасности в существующем FastAPI-приложении (`/home/user/relaxpanel/app/`).

## Контекст
- Уже есть базовая JWT-авторизация, bcrypt, slowapi rate limiting.
- Нужно добавить: WebAuthn (Passkey) опционально, Cloudflare Turnstile защиту при регистрации/логине, логирование подозрительных IP.

## Технические требования
1. **Rate limiting**: Усилить логин — 5 попыток на IP за 10 минут (уже есть в `auth.py`). Добавить rate limiting на `/sub/{token}` — не более 60 запросов в минуту на IP.
2. **Cloudflare Turnstile**: При логине/регистрации требовать `cf-turnstile-response` в форме. Верифицировать на сервере через `https://challenges.cloudflare.com/turnstile/v0/siteverify`.
3. **WebAuthn (опционально)**: Добавить endpoints `/api/auth/webauthn/begin` и `/finish` для регистрации и аутентификации по Passkey. Использовать библиотеку `webauthn`.
4. **Audit log**: Создать таблицу `AuditLog` (user_id, action, ip, user_agent, timestamp, success). Логировать все логины, неудачные попытки, сбросы ключей, создание/удаление источников.
5. **Защита OpenAPI**: Уже отключено в production (`docs_url=None`). Добавить middleware, которое отдаёт 404 на `/openapi.json` и `/docs`, если `x-admin-secret` header не совпадает с `ADMIN_SECRET` из env.

## Исходные файлы (не трогать структуру БД, только добавлять)
- `app/models.py` — добавить модель AuditLog.
- `app/api/auth.py` — добавить Turnstile, WebAuthn endpoints, audit логирование.
- `app/main.py` — подключить новые middleware и роутеры.
- `app/schemas.py` — добавить схемы AuditLog.

## Выход
- PR-style diff или перезаписанные файлы.
- Тестовый curl-пример для проверки Turnstile (с использованием тестового sitekey).
