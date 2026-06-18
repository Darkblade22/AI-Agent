# 🤖 Личный ИИ-агент в Telegram

Telegram-бот на базе Fireworks AI (модель Qwen2.5 72B). Умеет:

- 💬 общаться и помнить контекст диалога;
- 🌐 искать актуальную информацию в интернете (DuckDuckGo, без ключа);
- 🧠 запоминать факты о тебе между перезапусками;
- 📝 создавать и читать заметки (файлы);
- ⏰ ставить напоминания.

---

## Шаг 1. Получи ключи

### 1.1. Токен Telegram-бота
1. Открой в Telegram бота [@BotFather](https://t.me/BotFather).
2. Отправь команду `/newbot`, придумай имя и username.
3. BotFather пришлёт строку вида `123456:ABC-DEF...` — это токен.

### 1.2. API-ключ Fireworks
1. Зайди на [fireworks.ai](https://fireworks.ai) и зарегистрируйся.
2. Пополни баланс в разделе **Billing** (есть и стартовые кредиты).
3. В разделе **API Keys** создай ключ — строка вида `fw_...`.

### 1.3. Свой Telegram ID
Напиши боту [@userinfobot](https://t.me/userinfobot) — он пришлёт твой числовой ID.

---

## Шаг 2. Настрой проект

```bash
cd "/Users/danilstennikov/Documents/CODING/01. MY PROJECT/AI AGENT"
cp .env.example .env
open -e .env   # впиши токены и сохрани
```

В `.env` заполни:
- `TELEGRAM_BOT_TOKEN` — токен из BotFather
- `FIREWORKS_API_KEY` — ключ из fireworks.ai
- `ALLOWED_USER_IDS` — твой Telegram ID

---

## Шаг 3. Установи зависимости и запусти

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python bot.py
```

Если всё верно, увидишь `✅ Бот запущен`. Открой бота в Telegram,
напиши `/start` и начинай общаться.

> Бот работает, пока запущен процесс и включён Mac. Остановить — **Ctrl+C**.
> Следующий запуск: `source .venv/bin/activate && python bot.py`

---

## Что где лежит

| Файл | Назначение |
|------|------------|
| `bot.py` | запуск, Telegram, напоминания |
| `agent.py` | общение с моделью и обработка инструментов |
| `tools.py` | инструменты: поиск, память, файлы, напоминания |
| `memory.py` | долговременная память (факты о тебе) |
| `config.py` | загрузка настроек из `.env` |
| `data/` | память и напоминания (создаётся автоматически) |
| `workspace/` | заметки/файлы бота (создаётся автоматически) |

---

## Частые вопросы

**Бот отвечает «отвечаю только своему владельцу».**
В `.env` неверный `ALLOWED_USER_IDS`. Впиши свой ID от @userinfobot.

**Хочу другую модель.**
Поменяй `MODEL` в `.env` на любую из каталога Fireworks
(например `accounts/fireworks/models/llama-v3p3-70b-instruct`).

**Хочу, чтобы работал 24/7 без включённого Mac.**
Нужно разместить бота на сервере (Railway, VPS и т.п.) — напиши, настроим.
