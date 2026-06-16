# Açar🔐 — Subscription Manager & Proxy Customizer

Полноценная панель для управления VPN-подписками. Работает как **прокси-кастомизатор**: берёт unlimited-ссылки (VLESS/Trojan/VMess/SS), объединяет сервера из нескольких источников, добавляет кастомные имена, лимиты устройств, HWID-привязку, и выдаёт готовую подписку клиентам.

## Возможности

- **Объединение источников** — 2, 3, 5 unlimited sub → одна подписка клиента
- **Оригинальные домены** — хосты/порты из ваших источников не меняются, только имена серверов
- **Drag-and-Drop сортировка** — между источниками, глобальный порядок серверов
- **Device Limit** — 1-5 устройств, отслеживание по IP + User-Agent
- **HWID Lock** — привязка к устройству (Happ Crypt совместимость)
- **DDoS Protection** — авто-бан IP при >100 req/10sec на подписку
- **Cloudflare Tunnel** — бесплатный HTTPS, скрытие IP сервера
- **Happ Crypt** — готовая интеграция с внешним шифратором
- **SPA Dashboard** — тёмная/светлая тема, QR-коды, мобильная версия

## Стек

- **Backend**: FastAPI + SQLAlchemy + SQLite/PostgreSQL
- **Cache**: Redis (или in-memory fallback)
- **Worker**: Celery + Beat (фоновый парсинг)
- **Frontend**: Vanilla JS + TailwindCSS (SPA, один HTML-файл)
- **Infra**: Docker + Docker Compose + Nginx + Cloudflare Tunnel

## ⚡ Быстрый деплой (Ubuntu/Debian)

### 1. Загрузите папку `relaxpanel` на сервер

```bash
# На вашем компьютере:
scp -r relaxpanel root@ВАШ_IP:/opt/
# Или через rsync, или архив .zip / .tar.gz
```

### 2. Запустите установку

```bash
ssh root@ВАШ_IP
cd /opt/relaxpanel
chmod +x scripts/deploy.sh
ADMIN_USER=admin ADMIN_PASS=ВашПароль123 ./scripts/deploy.sh
```

### 3. Через 2-3 минуты получите URL

Скрипт выведет:
```
🌐 Your panel URL:
   https://acar-panel-123.trycloudflare.com/app
   Admin login: admin / ВашПароль123
```

Сохраните этот URL — он ваш навсегда (если контейнер не перезапускается). Для постоянного URL см. раздел "Постоянный домен".

### 4. Настройка

1. Откройте URL в браузере
2. Войдите как `admin` / ваш пароль
3. Перейдите в **Источники** → добавьте ваши unlimited sub URLs
4. Нажмите **«Обновить сейчас»** на каждом
5. Перейдите в **Серверы** — увидите все сервера из всех источников
6. Перетащите сервера в нужном порядке, нажмите **«Сохранить порядок»**
7. Перейдите в **Ключи** → создайте ключ клиента
8. Скопируйте ссылку подписки (или QR-код) → дайте клиенту

## 🛠️ Ручная установка (если Docker уже есть)

```bash
cd /opt/relaxpanel
# Создайте .env (или используйте пример)
cp .env.example .env
# Отредактируйте .env

# Запуск
docker-compose up -d

# Смотреть логи
docker-compose logs -f app
docker-compose logs -f cloudflared  # URL туннеля
```

## 🔒 Безопасность и DDoS-защита

| Уровень | Механизм | Детали |
|---------|----------|--------|
| **L7 (HTTP)** | Rate Limiting | 5 логинов/10 мин, 60 подписок/мин |
| **L7 DDoS** | Auto-ban | >100 req/10sec на `/sub/` → бан 5 минут |
| **Network** | Cloudflare Tunnel | Ваш IP скрыт, трафик идёт через Cloudflare |
| **API** | Закрытые endpoints | `/docs`, `/openapi.json` отключены |
| **Клиенты** | Device Limit | IP + UA трекинг, сброс в панели |
| **Клиенты** | HWID Lock | Привязка к устройству, сброс в панели |

## 📁 Структура

```
relaxpanel/
├── app/                  # Backend (FastAPI)
│   ├── api/              # Auth, Dealer, Admin, Subscription, Health
│   ├── models.py         # SQLAlchemy модели
│   ├── tasks.py          # Celery парсер VLESS/Trojan/VMess/SS
│   ├── middleware.py     # DDoS protection
│   └── main.py           # Точка входа
├── frontend/
│   └── index.html        # SPA (весь UI)
├── nginx/
│   └── nginx.conf        # Проксирование
├── scripts/
│   ├── deploy.sh         # Авто-установка на сервер
│   ├── test_e2e.py       # Тесты
│   └── backup.sh         # Бэкап БД
├── docker-compose.yml    # Все сервисы + Cloudflare Tunnel
└── README.md
```

## 🔁 Обновление панели

```bash
cd /opt/relaxpanel
git pull  # если используете git
docker-compose down
docker-compose up -d --build
```

## 🗄️ Бэкап

```bash
cd /opt/relaxpanel
docker-compose exec app tar czf /app/data/backup-$(date +%Y%m%d).tar.gz /app/data
docker cp acar_api:/app/data/backup-20250615.tar.gz .
```

## ☁️ Постоянный домен (не временный trycloudflare)

Временный URL меняется при перезапуске. Для постоянного:

1. Зарегистрируйтесь на [Cloudflare](https://dash.cloudflare.com)
2. Создайте **Zero Trust Tunnel** (бесплатно)
3. Получите **Tunnel Token**:
```bash
cloudflared tunnel create acar-panel
cloudflared tunnel token acar-panel
# Скопируйте токен
```
4. В `docker-compose.yml` раскомментируйте и вставьте токен:
```yaml
  cloudflared:
    environment:
      - TUNNEL_TOKEN=ваш_токен_здесь
    command: tunnel run
```
5. `docker-compose up -d cloudflared`
6. В Cloudflare Dashboard назначьте публичный хостнейм (например `acar.yourdomain.com` или `acar-panel-123.trycloudflare.com` если бесплатный)

## ⚠️ Важно: безопасность сервера

- **Не открывайте порт 8000** наружу (только 80/443 через Nginx, или вообще только Cloudflare Tunnel)
- **Измените пароль админа** после первого входа
- **Сохраните `.env`** — там секретный ключ и пароли
- **Не коммитьте `.env`** в git

## 🆘 Поддержка

Если что-то не работает:
```bash
cd /opt/relaxpanel
docker-compose logs -f app       # API ошибки
docker-compose logs -f worker    # Celery ошибки
docker-compose logs -f cloudflared # Туннель
```
