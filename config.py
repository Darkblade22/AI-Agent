"""Загрузка настроек из файла .env."""
import os
from pathlib import Path

from dotenv import load_dotenv

# Корень проекта
BASE_DIR = Path(__file__).resolve().parent

# Загружаем переменные из .env
load_dotenv(BASE_DIR / ".env")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6").strip()

# Список разрешённых Telegram ID (бот отвечает только им)
_raw_ids = os.getenv("ALLOWED_USER_IDS", "").strip()
ALLOWED_USER_IDS = {
    int(x) for x in _raw_ids.replace(" ", "").split(",") if x.isdigit()
}

# Папки для данных
DATA_DIR = BASE_DIR / "data"          # память, напоминания
WORKSPACE_DIR = BASE_DIR / "workspace"  # файлы, с которыми работает бот
DATA_DIR.mkdir(exist_ok=True)
WORKSPACE_DIR.mkdir(exist_ok=True)

MEMORY_FILE = DATA_DIR / "memory.json"
REMINDERS_FILE = DATA_DIR / "reminders.json"


def validate() -> list[str]:
    """Возвращает список проблем в настройках (пустой список = всё ок)."""
    problems = []
    if not TELEGRAM_BOT_TOKEN:
        problems.append("Не задан TELEGRAM_BOT_TOKEN в .env")
    if not ANTHROPIC_API_KEY:
        problems.append("Не задан ANTHROPIC_API_KEY в .env")
    if not ALLOWED_USER_IDS:
        problems.append("Не задан ALLOWED_USER_IDS в .env (твой Telegram ID)")
    return problems
