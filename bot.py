"""Telegram-бот: связывает Telegram с агентом на Claude."""
import json
import logging
import uuid
from datetime import datetime

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import agent
import config

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s", level=logging.INFO
)
log = logging.getLogger("bot")

# История диалога по чату: chat_id -> список сообщений для Claude
histories: dict[int, list] = {}

MAX_HISTORY = 40  # сколько последних сообщений держим в контексте


# ---------------------------------------------------------------------------
# Напоминания: хранение в JSON + планирование через JobQueue
# ---------------------------------------------------------------------------

def _local_tz():
    return datetime.now().astimezone().tzinfo


def _load_reminders() -> list[dict]:
    if not config.REMINDERS_FILE.exists():
        return []
    try:
        return json.loads(config.REMINDERS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _save_reminders(rem: list[dict]) -> None:
    config.REMINDERS_FILE.write_text(
        json.dumps(rem, ensure_ascii=False, indent=2), encoding="utf-8"
    )


async def _send_reminder(context: ContextTypes.DEFAULT_TYPE) -> None:
    job = context.job
    await context.bot.send_message(
        chat_id=job.chat_id, text=f"⏰ Напоминание: {job.data['text']}"
    )
    rem = [r for r in _load_reminders() if r["id"] != job.data["id"]]
    _save_reminders(rem)


def _make_ctx(chat_id: int, job_queue) -> dict:
    """Коллбэки для инструментов, привязанные к конкретному чату."""

    def set_reminder(when: str, text: str) -> str:
        try:
            dt = datetime.fromisoformat(when)
        except ValueError:
            return "Не понял время. Нужен формат вроде 2026-06-19T10:00:00."
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=_local_tz())
        if dt <= datetime.now(tz=_local_tz()):
            return "Это время уже прошло — поставь напоминание на будущее."
        rid = uuid.uuid4().hex[:8]
        job_queue.run_once(
            _send_reminder, when=dt, chat_id=chat_id,
            data={"text": text, "id": rid}, name=rid,
        )
        rem = _load_reminders()
        rem.append({"id": rid, "chat_id": chat_id, "when": dt.isoformat(), "text": text})
        _save_reminders(rem)
        return f"Готово, напомню {dt.strftime('%d.%m.%Y в %H:%M')}: {text}"

    def list_reminders() -> str:
        mine = [r for r in _load_reminders() if r["chat_id"] == chat_id]
        if not mine:
            return "Активных напоминаний нет."
        mine.sort(key=lambda r: r["when"])
        return "Напоминания:\n" + "\n".join(
            f"- {datetime.fromisoformat(r['when']).strftime('%d.%m %H:%M')}: {r['text']}"
            for r in mine
        )

    return {"set_reminder": set_reminder, "list_reminders": list_reminders}


# ---------------------------------------------------------------------------
# Вспомогательное
# ---------------------------------------------------------------------------

def _is_allowed(update: Update) -> bool:
    user = update.effective_user
    return user is not None and user.id in config.ALLOWED_USER_IDS


def _is_user_text(msg: dict) -> bool:
    return msg.get("role") == "user" and isinstance(msg.get("content"), str)


def _trim_history(history: list) -> None:
    if len(history) <= MAX_HISTORY:
        return
    del history[: len(history) - MAX_HISTORY]
    # Обрезаем начало, пока не дойдём до обычного сообщения пользователя
    # (иначе можно разорвать пару tool_use / tool_result)
    while history and not _is_user_text(history[0]):
        history.pop(0)


# ---------------------------------------------------------------------------
# Хендлеры
# ---------------------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_allowed(update):
        await update.message.reply_text(
            f"Привет! Этот бот личный. Твой Telegram ID: {update.effective_user.id}"
        )
        return
    await update.message.reply_text(
        "Привет! Я твой ИИ-агент 🤖\n\n"
        "Могу: искать в интернете, запоминать важное, работать с заметками "
        "и ставить напоминания. Просто напиши мне."
    )


async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_allowed(update):
        await update.message.reply_text("Извини, я отвечаю только своему владельцу.")
        return

    chat_id = update.effective_chat.id
    history = histories.setdefault(chat_id, [])
    _trim_history(history)

    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

    ctx = _make_ctx(chat_id, context.application.job_queue)
    try:
        reply = await agent.run(history, update.message.text, ctx)
    except Exception as e:  # noqa: BLE001
        log.exception("Ошибка агента")
        reply = f"Упс, что-то пошло не так: {e}"

    await update.message.reply_text(reply)


async def post_init(app: Application) -> None:
    """При старте восстанавливаем будущие напоминания."""
    now = datetime.now(tz=_local_tz())
    kept = []
    for r in _load_reminders():
        try:
            dt = datetime.fromisoformat(r["when"])
        except ValueError:
            continue
        if dt > now:
            app.job_queue.run_once(
                _send_reminder, when=dt, chat_id=r["chat_id"],
                data={"text": r["text"], "id": r["id"]}, name=r["id"],
            )
            kept.append(r)
    _save_reminders(kept)
    log.info("Восстановлено напоминаний: %d", len(kept))


def main() -> None:
    problems = config.validate()
    if problems:
        print("⚠️  Не могу запуститься — проверь файл .env:")
        for p in problems:
            print("   -", p)
        return

    app = (
        Application.builder()
        .token(config.TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .build()
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))

    print("✅ Бот запущен. Открой Telegram и напиши ему. Ctrl+C — остановить.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
