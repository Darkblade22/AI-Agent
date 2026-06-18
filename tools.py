"""Инструменты агента: поиск в интернете, память, файлы, напоминания.

Формат описаний — OpenAI function calling (Fireworks его поддерживает).
"""
from pathlib import Path

import config
import memory


def _fn(name: str, description: str, properties: dict, required: list[str]) -> dict:
    """Удобный конструктор схемы инструмента в формате OpenAI."""
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        },
    }


# ---------------------------------------------------------------------------
# Схемы инструментов (их "видит" модель и решает, когда вызвать)
# ---------------------------------------------------------------------------

TOOLS = [
    _fn(
        "web_search",
        "Найти актуальную информацию в интернете через DuckDuckGo. "
        "Используй для свежих данных, новостей, фактов, которых ты можешь не знать.",
        {"query": {"type": "string", "description": "Поисковый запрос"}},
        ["query"],
    ),
    _fn(
        "remember_fact",
        "Сохранить факт о пользователе в долговременную память "
        "(имя, предпочтения, дела, важные детали). Вызывай, когда узнаёшь что-то, "
        "что стоит помнить в будущих диалогах.",
        {"fact": {"type": "string", "description": "Факт одним предложением"}},
        ["fact"],
    ),
    _fn(
        "list_facts",
        "Показать всё, что сохранено в памяти о пользователе.",
        {},
        [],
    ),
    _fn(
        "forget_fact",
        "Удалить факт из памяти по его номеру или по тексту.",
        {"query": {"type": "string", "description": "Номер факта или часть текста"}},
        ["query"],
    ),
    _fn(
        "write_file",
        "Создать или перезаписать текстовый файл-заметку в рабочей папке.",
        {
            "filename": {"type": "string", "description": "Имя файла, напр. 'заметки.txt'"},
            "content": {"type": "string", "description": "Содержимое файла"},
        },
        ["filename", "content"],
    ),
    _fn(
        "read_file",
        "Прочитать текстовый файл из рабочей папки.",
        {"filename": {"type": "string", "description": "Имя файла"}},
        ["filename"],
    ),
    _fn(
        "list_files",
        "Показать список файлов в рабочей папке.",
        {},
        [],
    ),
    _fn(
        "set_reminder",
        "Поставить напоминание — бот пришлёт сообщение в указанное время. "
        "Время в ISO-формате с учётом текущей даты/времени из системного промпта, "
        "например '2026-06-19T10:00:00'.",
        {
            "when": {"type": "string", "description": "Дата и время в ISO-формате"},
            "text": {"type": "string", "description": "Текст напоминания"},
        },
        ["when", "text"],
    ),
    _fn(
        "list_reminders",
        "Показать активные напоминания.",
        {},
        [],
    ),
]


# ---------------------------------------------------------------------------
# Поиск в интернете (DuckDuckGo, без ключа)
# ---------------------------------------------------------------------------

def _web_search(query: str, max_results: int = 5) -> str:
    try:
        from ddgs import DDGS
    except ImportError:  # старое название пакета
        from duckduckgo_search import DDGS  # type: ignore

    with DDGS() as ddgs:
        results = list(ddgs.text(query, max_results=max_results))

    if not results:
        return "По запросу ничего не найдено."

    lines = []
    for r in results:
        title = r.get("title", "")
        body = r.get("body", "")
        href = r.get("href", "")
        lines.append(f"• {title}\n  {body}\n  Источник: {href}")
    return "\n\n".join(lines)


# ---------------------------------------------------------------------------
# Безопасная работа с файлами (только внутри workspace/)
# ---------------------------------------------------------------------------

def _safe_path(filename: str) -> Path:
    name = Path(filename).name  # отбрасываем любые ../ и пути
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

def execute(name: str, args: dict, ctx: dict) -> str:
    """Выполнить инструмент. ctx содержит коллбэки от бота."""
    try:
        if name == "web_search":
            return _web_search(args["query"])
        if name == "remember_fact":
            return memory.add_fact(args["fact"])
        if name == "list_facts":
            facts = memory.list_facts()
            return "\n".join(f"{i}. {f}" for i, f in enumerate(facts, 1)) or "Память пуста."
        if name == "forget_fact":
            return memory.forget_fact(args["query"])
        if name == "write_file":
            return _write_file(args["filename"], args["content"])
        if name == "read_file":
            return _read_file(args["filename"])
        if name == "list_files":
            return _list_files()
        if name == "set_reminder":
            return ctx["set_reminder"](args["when"], args["text"])
        if name == "list_reminders":
            return ctx["list_reminders"]()
        return f"Неизвестный инструмент: {name}"
    except Exception as e:  # noqa: BLE001 — отдаём ошибку модели как текст
        return f"Ошибка при выполнении '{name}': {e}"
