"""Долговременная память бота: факты о пользователе в JSON-файле."""
import json

import config


def _load() -> list[str]:
    if not config.MEMORY_FILE.exists():
        return []
    try:
        return json.loads(config.MEMORY_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _save(facts: list[str]) -> None:
    config.MEMORY_FILE.write_text(
        json.dumps(facts, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def add_fact(fact: str) -> str:
    fact = fact.strip()
    if not fact:
        return "Пустой факт — нечего запоминать."
    facts = _load()
    if fact in facts:
        return "Уже знаю это."
    facts.append(fact)
    _save(facts)
    return f"Запомнил: {fact}"


def list_facts() -> list[str]:
    return _load()


def forget_fact(query: str) -> str:
    """Удаляет факт по номеру (с 1) или по точному/частичному совпадению."""
    facts = _load()
    query = query.strip()

    # По номеру
    if query.isdigit():
        idx = int(query) - 1
        if 0 <= idx < len(facts):
            removed = facts.pop(idx)
            _save(facts)
            return f"Забыл: {removed}"
        return "Нет факта с таким номером."

    # По совпадению текста
    matches = [f for f in facts if query.lower() in f.lower()]
    if not matches:
        return "Не нашёл подходящего факта."
    for m in matches:
        facts.remove(m)
    _save(facts)
    return "Забыл: " + "; ".join(matches)


def memory_block() -> str:
    """Текст для вставки в системный промпт."""
    facts = _load()
    if not facts:
        return "(пока ничего не известно о пользователе)"
    return "\n".join(f"{i}. {f}" for i, f in enumerate(facts, 1))
