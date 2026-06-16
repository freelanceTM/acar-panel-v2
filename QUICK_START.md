# Açar🔐 — Быстрый старт (2 минуты)

## 1. Создайте новый GitHub токен (30 сек)

Ваш старый токен скомпрометирован. Создайте новый:

1. Откройте https://github.com/settings/tokens/new
2. Название: `acar-deploy`
3. Срок: **No expiration** (или 30 дней)
4. Галочка: `repo` (весь раздел)
5. **Generate token** → скопируйте `ghp_...` (покажется только один раз!)

## 2. Создайте пустой репозиторий

1. https://github.com/new
2. Repository name: `acar-panel` (или любое другое)
3. **Public** или **Private** — как хотите
4. **НЕ** добавляйте README, .gitignore, license (оставьте пустым)
5. **Create repository**

## 3. Запушьте (30 секунд)

На вашем сервере (где уже есть папка `/opt/relaxpanel`):

```bash
# Вставьте ваши данные:
GITHUB_USER=ВАШ_NICKNAME
GITHUB_REPO=acar-panel
TOKEN=ghp_ВАШ_НОВЫЙ_ТОКЕН

cd /opt/relaxpanel
git remote add origin https://${TOKEN}@github.com/${GITHUB_USER}/${GITHUB_REPO}.git
git branch -M master
git push -u origin master
```

Готово! Код на GitHub.

---

## 4. Деплой на сервер (1 минута)

Если еще не задеплоено:

```bash
cd /opt/relaxpanel
chmod +x scripts/deploy.sh
ADMIN_USER=admin ADMIN_PASS=ВашПароль123 ./scripts/deploy.sh
```

Через 2 минуты получите URL:
```
🌐 Your panel URL:
   https://acar-panel-xxx.trycloudflare.com/app
```

---

## ⚠️ ВАЖНО

После пуша **удалите старый токен** `<your-token-here>`:
https://github.com/settings/tokens
