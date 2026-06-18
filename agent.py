"""Агентный цикл: общение с моделью (Fireworks, OpenAI-совместимый API)
и обработка инструментов."""
import json
from datetime import datetime

from openai import AsyncOpenAI

import config
import memory
import tools

client = AsyncOpenAI(
    api_key=config.FIREWORKS_API_KEY,
    base_url=config.FIREWORKS_BASE_URL,
)

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
        "Доступные инструменты:\n"
        "- web_search — искать актуальную информацию в интернете;\n"
        "- remember_fact / forget_fact / list_facts — память о пользователе;\n"
        "- write_file / read_file / list_files — заметки и файлы;\n"
        "- set_reminder / list_reminders — напоминания.\n\n"
        "Сам решай, когда стоит что-то запомнить или поискать — без лишних вопросов.\n\n"
        "Что ты уже знаешь о пользователе:\n"
        f"{memory.memory_block()}"
    )


async def run(history: list[dict], user_text: str, ctx: dict) -> str:
    """Обрабатывает одно сообщение. history мутируется. Возвращает текст ответа."""
    history.append({"role": "user", "content": user_text})

    for _ in range(MAX_TOOL_ROUNDS):
        response = await client.chat.completions.create(
            model=config.MODEL,
            max_tokens=MAX_TOKENS,
            messages=[{"role": "system", "content": build_system_prompt()}] + history,
            tools=tools.TOOLS,
        )
        msg = response.choices[0].message
        history.append(_assistant_to_dict(msg))

        if not msg.tool_calls:
            return (msg.content or "").strip() or "(пустой ответ)"

        # Выполняем все запрошенные инструменты
        for tc in msg.tool_calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            result = tools.execute(tc.function.name, args, ctx)
            history.append(
                {"role": "tool", "tool_call_id": tc.id, "content": result}
            )

    return "Слишком много шагов с инструментами — останавливаюсь. Попробуй переформулировать."


def _assistant_to_dict(msg) -> dict:
    """Превращает ответ модели в обычный dict для истории."""
    out: dict = {"role": "assistant", "content": msg.content or ""}
    if msg.tool_calls:
        out["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                },
            }
            for tc in msg.tool_calls
        ]
    return out
