"""Инструменты агента: память, файлы, напоминания.

Поиск в интернете подключается отдельно как серверный инструмент Anthropic
(web_search) — см. agent.py. Здесь только "клиентские" инструменты,
которые выполняются на нашей стороне.
"""
from pathlib import Path

import config
import memory

# ---------------------------------------------------------------------------
# Схемы инструментов (их "видит" Claude и решает, когда вызвать)
# ---------------------------------------------------------------------------

CLIENT_TOOLS = [
    {
        "name": "remember_fact",
        "description": (
            "Сохранить факт о пользователе в долговременную память "
            "(имя, предпочтения, текущие дела, важные детали). "
            "Используй, когда узнаёшь что-то, что стоит помнить в будущих диалогах."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "fact": {"type": "string", "description": "Факт одним предложением"}
            },
            "required": ["fact"],
        },
    },
    {
        "name": "list_facts",
        "description": "Показать всё, что сохранено в долговременной памяти о пользователе.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "forget_fact",
        "description": "Удалить факт из памяти по его номеру или по тексту.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Номер факта (например '2') или часть его текста",
                }
            },
            "required": ["query"],
        },
    },
    {
        "name": "write_file",
        "description": (
            "Создать или перезаписать текстовый файл в рабочей папке. "
            "Используй для заметок, списков, черновиков."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "Имя файла, напр. 'заметки.txt'"},
                "content": {"type": "string", "description": "Содержимое файла"},
            },
            "required": ["filename", "content"],
        },
    },
    {
        "name": "read_file",
        "description": "Прочитать текстовый файл из рабочей папки.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "Имя файла"}
            },
            "required": ["filename"],
        },
    },
    {
        "name": "list_files",
        "description": "Показать список файлов в рабочей папке.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "set_reminder",
        "description": (
            "Поставить напоминание. Бот пришлёт сообщение в указанное время. "
            "Время указывай в ISO-формате с учётом текущей даты/времени из системного "
            "промпта, например '2026-06-19T10:00:00'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "when": {"type": "string", "description": "Дата и время в ISO-формате"},
                "text": {"type": "string", "description": "Текст напоминания"},
            },
            "required": ["when", "text"],
        },
    },
    {
        "name": "list_reminders",
        "description": "Показать активные напоминания.",
        "input_schema": {"type": "object", "properties": {}},
    },
]


# ---------------------------------------------------------------------------
# Безопасная работа с файлами (только внутри workspace/)
# ---------------------------------------------------------------------------

def _safe_path(filename: str) -> Path:
    # Берём только имя файла, отбрасываем любые ../ и пути
    name = Path(filename).name
    return config.WORKSPACE_DIR / name


def _write_file(filename: str, content: str) -> str:
    path = _safe_path(filename)
    path.write_text(content, encoding="utf-8")
    return f"Файл сохранён: {path.name} ({len(content)} символов)"


def _read_file(filename: str) -> str:
    path = _safe_path(filename)
    if not path.exists():
        return f"Файл '{path.name}' не найден."
    try:
        return path.read_text(encoding="utf-8")
    except OSError as e:
        return f"Не удалось прочитать файл: {e}"


def _list_files() -> str:
    files = [p.name for p in config.WORKSPACE_DIR.iterdir() if p.is_file()]
    if not files:
        return "Рабочая папка пуста."
    return "Файлы:\n" + "\n".join(f"- {f}" for f in files)


# ---------------------------------------------------------------------------
# Диспетчер: выполняет инструмент по имени
# ---------------------------------------------------------------------------

def execute(name: str, tool_input: dict, ctx: dict) -> str:
    """Выполнить клиентский инструмент. ctx содержит коллбэки от бота."""
    try:
        if name == "remember_fact":
            return memory.add_fact(tool_input["fact"])
        if name == "list_facts":
            facts = memory.list_facts()
            return "\n".join(f"{i}. {f}" for i, f in enumerate(facts, 1)) or "Память пуста."
        if name == "forget_fact":
            return memory.forget_fact(tool_input["query"])
        if name == "write_file":
            return _write_file(tool_input["filename"], tool_input["content"])
        if name == "read_file":
            return _read_file(tool_input["filename"])
        if name == "list_files":
            return _list_files()
        if name == "set_reminder":
            return ctx["set_reminder"](tool_input["when"], tool_input["text"])
        if name == "list_reminders":
            return ctx["list_reminders"]()
        return f"Неизвестный инструмент: {name}"
    except Exception as e:  # noqa: BLE001 — возвращаем ошибку модели как текст
        return f"Ошибка при выполнении '{name}': {e}"
