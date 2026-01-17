import asyncio
import json
import logging
import sys
import json

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
TRUNCATE_LENGTH = 200


def safe_parse_thoughts_and_action(self, message: str):
    """Parse assistant message into thoughts and action for a FaraAgent instance.

    Args:
        self: Active FaraAgent instance.
        message: Full assistant response expected to contain a <tool_call> block.

    Returns:
        Tuple of (thoughts, action dict). Falls back to a stop action when parsing fails.
    """
    thoughts = message.strip()
    agent_logger = getattr(self, "logger", logger)

    # Пытаемся найти блок <tool_call>
    if "<tool_call>" not in message:
        agent_logger.warning("Ответ без <tool_call>; завершаем с текущими мыслями.")
        return thoughts, {
            "name": "computer_use",
            "arguments": {"action": "stop", "thoughts": thoughts}
        }

    # Извлекаем JSON из блока <tool_call>
    try:
        start = message.index("<tool_call>") + len("<tool_call>")
        end = message.index("</tool_call>", start)
        tool_call_json = message[start:end].strip()
        action = json.loads(tool_call_json)
    except (json.JSONDecodeError, ValueError) as e:
        agent_logger.error(f"Не удалось распарсить JSON из tool_call: {e}")
        return thoughts, {
            "name": "computer_use",
            "arguments": {"action": "stop", "thoughts": thoughts}
        }

    # Проверяем, что action содержит обязательные поля
    if not isinstance(action, dict):
        agent_logger.warning("Ответ не является словарем; завершаем с текущими мыслями.")
        return thoughts, {
            "name": "computer_use",
            "arguments": {"action": "stop", "thoughts": thoughts}
        }

    # Если в action уже есть 'name' и 'arguments', возвращаем как есть
    if "name" in action and "arguments" in action:
        return thoughts, action

    # Если есть только 'arguments', добавляем имя по умолчанию
    if "arguments" in action:
        action.setdefault("name", "computer_use")
        return thoughts, action

    # Иначе завершаем с stop
    agent_logger.warning("Ответ без arguments; завершаем с текущими мыслями.")
    return thoughts, {
        "name": "computer_use",
        "arguments": {"action": "stop", "thoughts": thoughts}
    }


async def main():
    logger.info("Запуск FARA...")

    try:
        # Динамический импорт (если FARA не установлен, будет понятная ошибка)
        from fara import FaraAgent
        from fara.browser.browser_bb import BrowserBB

    except ImportError as e:
        logger.error(f"Ошибка импорта FARA: {e}")
        logger.info("Проверьте установку FARA: pip install -e /fara")
        return 1

    # Монки-патч парсинга: возвращаем безопасное действие, если формат ответа не содержит <tool_call>
    def _safe_parse_thoughts_and_action(self, message: str):
        if "<tool_call>" not in message or "</tool_call>" not in message:
            thoughts = message.strip()
            action = {"arguments": {"action": "terminate", "status": "failure", "thoughts": thoughts}}
            return thoughts, action
        try:
            tmp = message.split("<tool_call>\n")
            thoughts = tmp[0].strip()
            action_text = tmp[1].split("\n</tool_call>")[0]
            try:
                action = json.loads(action_text)
            except json.decoder.JSONDecodeError:
                action = eval(action_text)
            return thoughts, action
        except Exception:
            thoughts = message.strip()
            action = {"arguments": {"action": "terminate", "status": "failure", "thoughts": thoughts}}
            return thoughts, action

    FaraAgent._parse_thoughts_and_action = _safe_parse_thoughts_and_action

    # Вариант 1: С Ollama (используем внешний контейнер из сети fara-ollama)
    client_config = {
        "model": "maternion/fara:7b",
        "base_url": "http://host.docker.internal:11434/v1",
        "api_key": "ollama",
        "timeout": 30.0,
        "extra_body": {
            "format": "json"
        },
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "computer_use",
                    "description": "Use a mouse and keyboard to interact with a computer, and take screenshots.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "action": {"type": "string"},
                            "thoughts": {"type": "string"},
                            "coordinate": {"type": "array", "items": {"type": "number"}},
                            "url": {"type": "string"},
                            "text": {"type": "string"},
                            "keys": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["action"],
                        "additionalProperties": True
                    }
                }
            }
        ]
    }

    # Вариант 2: Без LLM (только браузер)
    # client_config = None

    try:
        # Инициализация браузера
        browser_manager = BrowserBB(
            headless=True,
            viewport_height=900,
            viewport_width=1440,
            page_script_path=None,
            browser_channel="chromium",
            downloads_folder="/app/downloads",
            single_tab_mode=True
        )

        # Инициализация агента
        agent = FaraAgent(
            browser_manager=browser_manager,
            client_config=client_config,
            start_page="https://www.google.com",
            downloads_folder="/app/downloads",
            save_screenshots=False,
            max_rounds=10
        )

        if hasattr(agent, "_parse_thoughts_and_action"):
            agent._original_parse_thoughts_and_action = agent._parse_thoughts_and_action
            agent._parse_thoughts_and_action = safe_parse_thoughts_and_action.__get__(
                agent, agent.__class__
            )
        else:
            logger.warning("Не удалось найти _parse_thoughts_and_action для патча.")

        logger.info("Инициализация агента...")
        await agent.initialize()

        # Простая задача
        task = "Go to https://mockup.graphics and return the page title."
        logger.info(f"Выполняем: {task}")

        result = await agent.run(task)
        final_answer, actions, observations = result

        logger.info(f"Задача выполнена! Действий: {len(actions)}")
        logger.info(f"Ответ: {final_answer[:200]}...")

        # Сохраняем результат
        with open("/app/results/result.txt", "w") as f:
            f.write(f"Task: {task}\n")
            f.write(f"Answer: {final_answer}\n")
            f.write(f"Actions: {len(actions)}\n")

        logger.info("Результат сохранен в /app/results/result.txt")

    except Exception as e:
        logger.error(f"Ошибка: {e}")
        return 1
    finally:
        try:
            await agent.close()
        except:
            pass

    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
