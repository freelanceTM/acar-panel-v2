# Агент 05: Тестирование и нагрузочные тесты

## Задача
Покрыть проект тестами (pytest) и написать нагрузочный скрипт (locust).

## Технические требования
1. **Unit tests** (`tests/`):
   - `test_auth.py` — регистрация, логин, JWT refresh, WebAuthn (mock).
   - `test_dealer_api.py` — CRUD ключей, источников, серверов. Пагинация, поиск.
   - `test_subscription.py` — выдача подписки, блокировка по expired, device limit, HWID, переименование серверов.
   - Использовать `TestClient` от FastAPI и `fakeredis` для мока Redis (или запускать редис в `docker-compose test`).
2. **Integration tests**:
   - Парсинг VMess / VLESS / Trojan / SS ссылок: валидные и невалидные входные данные.
   - Celery task `fetch_single_source` с `responses`/`respx` моком HTTP.
3. **Nagruz tests** (`locustfile.py`):
   - Симулировать 1000 клиентов, запрашивающих `/sub/{token}` с разными User-Agent.
   - Проверить, что 95-й перцентиль ответа < 200ms (кэширование работает).
   - Проверить, что при 10+ устройств на один токен — блокировка срабатывает.
4. **Security tests**:
   - SQL Injection через поиск `q` в `/dealer/keys`.
   - JWT tampering.
   - Brute-force логина (должен вернуть 429).

## Исходные файлы
- Новые: `tests/`, `locustfile.py`, `pytest.ini`.

## Выход
- `pytest` проходит зелёным.
- Отчёт locust (график RPS / latency) в `reports/load_test.md`.
