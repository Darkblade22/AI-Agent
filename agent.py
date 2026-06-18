"""Агентный цикл: общение с Claude API и обработка инструментов."""
from datetime import datetime

from anthropic import AsyncAnthropic

import config
import memory
import tools

client = AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)

# Серверный инструмент поиска в интернете (выполняется на стороне Anthropic)
WEB_SEARCH_TOOL = {"type": "web_search_20250305", "name": "web_search", "max_uses": 5}

MAX_TOKENS = 2048
MAX_TOOL_ROUNDS = 8  # защита от бесконечного цикла вызовов инструментов


def build_system_prompt() -> str:
    now = datetime.now().astimezone()
    return (
        "Ты — личный ИИ-агент пользователя, общаешься с ним в Telegram.\n"
        "Отвечай дружелюбно, по делу, на языке пользователя (обычно русский).\n"
        "Пиши компактно — это мессенджер, не пиши простыни без необходимости.\n\n"
        f"Текущие дата и время: {now.strftime('%Y-%m-%d %H:%M:%S %Z')} "
        f"(день недели: {now.strftime('%A')}).\n"
        "Используй это время для вычисления моментов напоминаний.\n\n"
        "Что ты умеешь через инструменты:\n"
        "- искать актуальную информацию в интернете (web_search);\n"
        "- запоминать и забывать факты о пользователе (remember_fact / forget_fact / list_facts);\n"
        "- создавать и читать файлы-заметки (write_file / read_file / list_files);\n"
        "- ставить напоминания (set_reminder / list_reminders).\n\n"
        "Сам решай, когда стоит что-то запомнить — без лишних вопросов.\n\n"
        "Что ты уже знаешь о пользователе:\n"
        f"{memory.memory_block()}"
    )


async def run(history: list[dict], user_text: str, ctx: dict) -> str:
    """Обрабатывает одно сообщение пользователя.

    history мутируется (добавляются новые сообщения). Возвращает текст ответа.
    """
    history.append({"role": "user", "content": user_text})

    all_tools = [WEB_SEARCH_TOOL] + tools.CLIENT_TOOLS

    for _ in range(MAX_TOOL_ROUNDS):
        response = await client.messages.create(
            model=config.CLAUDE_MODEL,
            max_tokens=MAX_TOKENS,
            system=build_system_prompt(),
            tools=all_tools,
            messages=history,
        )

        # Сохраняем ответ ассистента в историю
        history.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            return _extract_text(response.content) or "(пустой ответ)"

        # Выполняем все клиентские инструменты, которые запросила модель
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                result = tools.execute(block.name, block.input, ctx)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    }
                )

        if not tool_results:
            # Запрошены только серверные инструменты (web_search) — модель
            # продолжит сама на следующем шаге не должна сюда попасть, но на всякий случай
            return _extract_text(response.content) or "(пустой ответ)"

        history.append({"role": "user", "content": tool_results})

    return "Слишком много шагов с инструментами — останавливаюсь. Попробуй переформулировать."


def _extract_text(content) -> str:
    parts = [b.text for b in content if getattr(b, "type", None) == "text"]
    return "\n".join(parts).strip()
