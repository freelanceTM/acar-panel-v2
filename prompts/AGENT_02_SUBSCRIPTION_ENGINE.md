# Агент 02: Движок подписок и кэширование

## Задача
Сделать `/sub/{token}` production-ready: поддержку всех протоколов (VLESS, Trojan, VMess, Shadowsocks), шифрование Happ Crypt, и отказоустойчивый кэш.

## Контекст
- Уже есть MVP в `app/api/subscription.py` и `app/tasks.py`.
- Celery worker фоново парсит Unlimited-ссылки каждые 5 минут.

## Технические требования
1. **Поддержка всех протоколов**:
   - VLESS: `vless://uuid@host:port?type=ws&path=/...&security=tls...#remark`
   - Trojan: `trojan://password@host:port?...#remark`
   - VMess: `vmess://base64json` — парсить base64, вытаскивать `add`, `port`, `ps`, `id`, `aid`, `net`, `type`, `host`, `path`, `tls`.
   - Shadowsocks: `ss://base64(method:password)@host:port#remark` или `ss://method:password@host:port`.
2. **Happ Crypt шифрование**:
   - Добавить интеграцию с `happ.su` API или аналогичным внешним шифратором.
   - Endpoint `POST /api/dealer/keys/{id}/encrypt` — принимает `happ_api_key`, шифрует подписку через внешний API, сохраняет encrypted_url в Redis.
   - При выдаче `/sub/{token}`: если `happ_api_key` настроен, возвращать зашифрованный blob вместо plaintext (или делать прокси-запрос к happ API).
3. **Redis кэширование подписок**:
   - TTL подписки = 5 минут (уже есть в настройках).
   - Добавить Redis-based LRU кэш для parsed конфигов (сериализация JSON).
   - При изменении дилером custom_name/priority — инвалидировать кэш по `sub_cache:{token}` и `servers:{dealer_id}`.
4. **Device Limit детализация**:
   - Вместо `IP|UA` использовать Redis Hash: `dev_limit:{token}` -> поля `device_1`, `device_2`... с JSON `{ip, ua, hwid, last_seen}`.
   - Сделать endpoint `/api/dealer/keys/{id}/devices` для просмотра привязанных устройств.
   - Отображать в панели дилера список устройств (IP, UA, HWID, последний вход).
5. **Fallback**: Если Redis недоступен, fallback на in-memory dict (в рамках одного процесса) и лог warn.

## Исходные файлы
- `app/api/subscription.py` — доработать парсинг, шифрование, device tracking.
- `app/redis_client.py` — добавить hash-операции, инвалидацию.
- `app/tasks.py` — улучшить парсинг для SS/VMess/Trojan.
- `app/models.py` — добавить `happ_api_key` в User или ClientKey (решить где лучше).
- `app/api/dealer.py` — добавить endpoints для просмотра устройств и настройки шифрования.

## Выход
- Работающий `/sub/{token}` с тестовыми ссылками.
- Тестовый curl с VMess / VLESS / Trojan.
