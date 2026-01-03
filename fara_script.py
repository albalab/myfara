import asyncio
import json
import logging
import sys
from typing import Any

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
TRUNCATE_LENGTH = 200
TOOL_CALL_TAG = "<tool_call>"
TOOL_CALL_END_TAG = "</tool_call>"


def safe_parse_thoughts_and_action(self, message: Any):
    """Parse assistant message into thoughts and action for a FaraAgent instance.

    Args:
        self: Active FaraAgent instance (injected via monkey patch).
        message: Assistant response; strings are parsed for a <tool_call> block, other types are delegated.

    Returns:
        Tuple of (thoughts, action dict). Falls back to a stop action when parsing fails.
    """
    agent_logger = getattr(self, "logger", logger)

    def stop_action(thoughts_text: str):
        return {
            "name": "computer_use",
            "arguments": {"action": "stop", "thoughts": thoughts_text}
        }

    def normalize_action(candidate: Any):
        if not isinstance(candidate, dict):
            return None
        arguments = candidate.get("arguments")
        if not isinstance(arguments, dict):
            return None
        result = candidate.copy()
        result.setdefault("name", "computer_use")
        return result

    def delegate_or_stop(thoughts_text: str, incoming: Any):
        original = getattr(self, "_original_parse_thoughts_and_action", None)
        if original:
            try:
                return original(incoming)
            except Exception as exc:
                agent_logger.exception("Default parser error (%s)", type(exc).__name__)
                return thoughts_text, stop_action(thoughts_text)
        return thoughts_text, stop_action(thoughts_text)

    # Delegate to the original parser when the message format is unexpected
    if not isinstance(message, str):
        return delegate_or_stop("", message)

    thoughts = message.strip()

    # Extract JSON from the <tool_call> block
    start = message.find(TOOL_CALL_TAG)
    if start == -1:
        # Try parsing the whole message as JSON action before delegating
        try:
            parsed = normalize_action(json.loads(message))
            if parsed:
                return thoughts, parsed
        except (json.JSONDecodeError, ValueError):
            pass

        agent_logger.warning(f"Response without {TOOL_CALL_TAG}; returning stop action.")
        return thoughts, stop_action(thoughts)

    start += len(TOOL_CALL_TAG)
    end = message.find(TOOL_CALL_END_TAG, start)
    if end == -1:
        agent_logger.error(f"Missing closing {TOOL_CALL_END_TAG} tag.")
        return thoughts, stop_action(thoughts)

    try:
        tool_call_json = message[start:end].strip()
        action = normalize_action(json.loads(tool_call_json))
    except (json.JSONDecodeError, ValueError) as e:
        agent_logger.error(f"Could not parse JSON from tool_call: {e}")
        return thoughts, stop_action(thoughts)

    if not action:
        agent_logger.warning("Action is missing or has invalid arguments; stopping with current thoughts.")
        return thoughts, stop_action(thoughts)

    # Ensure action contains required fields
    # If action already has 'name' and 'arguments', return as is
    if "name" in action and "arguments" in action:
        return thoughts, action

    # Otherwise stop
    agent_logger.warning("Action is missing arguments; stopping with current thoughts.")
    return thoughts, stop_action(thoughts)


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

    # Вариант 1: С Ollama (используем внешний контейнер из сети fara-ollama)
    client_config = {
        "model": "maternion/fara:7b",
        "base_url": "http://host.docker.internal:11434/v1",
        "api_key": "ollama",
        "timeout": 30.0,
        "extra_body": {
            "format": "json"
        },
        "options": {
            "temperature": 0.1,
            "top_p": 0.9,
            "repeat_penalty": 1.05,
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
