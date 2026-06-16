# Агент 03: Фронтенд дилера (SPA на Vanilla JS)

## Задача
Довести `/frontend/index.html` до production-уровня: дизайн, drag-and-drop сортировка серверов, визуализация источников, светлая/темная тема.

## Контекст
- Фронтенд — один HTML-файл (`frontend/index.html`) с Tailwind CDN и Vanilla JS.
- Нет React/Vue — всё на Fetch API + DOM.

## Технические требования
1. **Адаптивный дизайн**:
   - Мобильная таблица ключей (card view на <768px).
   - Sticky header, bottom nav на мобильных.
2. **Темы**:
   - Переключатель темной/светлой/системной темы.
   - Сохранение выбора в `localStorage`.
   - Tailwind `dark:` классы уже работают через `<html class="dark">`.
3. **Drag-and-drop сортировка серверов**:
   - В разделе "Серверы" (сейчас `serversPage`) добавить ручки (⋮⋮) и DnD через HTML5 Drag API.
   - При drop делать `PATCH /api/dealer/servers/{id}` с новым `priority` (или batch endpoint `POST /api/dealer/servers/reorder` с массивом `[[id, priority], ...]`).
   - Backend endpoint нужно создать (или просить AGENT_04/мне добавить).
4. **Модальные окна**:
   - Создание/редактирование ключа с календарем `expires_at` (HTML date input).
   - Ввод Unlimited Source с валидацией URL (должен оканчиваться на `.txt` или быть `https://`).
   - Просмотр "привязанных устройств" в модальном окне (endpoint от AGENT_02).
5. **Dashboard статистика**:
   - Карточки: всего ключей, активных, источников, обновление последнего парсинга.
   - Endpoint: `GET /api/dealer/stats` (нужно создать на backend).
6. **Копирование ссылки подписки**:
   - One-click копирование ссылки `https://domain.com/sub/{token}`.
   - QR-code generation (используя библиотеку `qrious` CDN или `QRCode.js` CDN) в модальном окне "Поделиться".
7. **Производительность**:
   - Виртуализация не нужна, но debounce (300ms) на поиске ключей.
   - Skeleton loaders при загрузке страниц.

## Исходные файлы
- `frontend/index.html` — единственный файл фронтенда.
- `app/api/dealer.py` — нужно добавить `POST /dealer/servers/reorder` и `GET /dealer/stats` (сделать самостоятельно или координировать).

## Выход
- Обновлённый `frontend/index.html`.
- Список новых backend endpoints, которые нужны (для передачи backend-агенту).
