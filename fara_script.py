import asyncio
import json
import logging
import sys

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def safe_parse_thoughts_and_action(self, message: str):
    """Parse assistant message into thoughts and action; fall back to stop on malformed input."""
    thoughts = message.strip()
    try:
        before_tool, separator, after_tool = message.partition("<tool_call>")
        if not separator:
            self.logger.warning("Ответ без <tool_call>; завершаем с текущими мыслями.")
            return thoughts, {"arguments": {"action": "stop", "thoughts": thoughts}}

        thoughts = before_tool.strip()
        if "</tool_call>" not in after_tool:
            self.logger.warning(
                "Ответ без закрывающего </tool_call>; завершаем с текущими мыслями."
            )
            return thoughts, {"arguments": {"action": "stop", "thoughts": thoughts}}

        tool_call_block = after_tool.split("</tool_call>", 1)[0]
        action_text = tool_call_block.strip()
        try:
            action = json.loads(action_text)
        except json.JSONDecodeError:
            truncated_action_text = action_text[:200]
            self.logger.error(
                f"Invalid action text (truncated): {truncated_action_text}",
                exc_info=True,
            )
            action = {"arguments": {"action": "stop", "thoughts": thoughts}}

        if not isinstance(action, dict) or "arguments" not in action:
            self.logger.warning("Ответ без arguments; завершаем с текущими мыслями.")
            action = {"arguments": {"action": "stop", "thoughts": thoughts}}
        elif "action" not in action["arguments"]:
            self.logger.warning("Ответ без action; завершаем с текущими мыслями.")
            action = {"arguments": {"action": "stop", "thoughts": thoughts}}

        return thoughts, action
    except Exception:
        self.logger.error(
            f"Error parsing thoughts and action: {message[:200]}", exc_info=True
        )
        return thoughts, {"arguments": {"action": "stop", "thoughts": thoughts}}


async def main():
    logger.info("Запуск FARA...")

    try:
        # Динамический импорт (если FARA не установлен, будет понятная ошибка)
        from fara import FaraAgent
        from fara.browser.browser_bb import BrowserBB

        if hasattr(FaraAgent, "_parse_thoughts_and_action"):
            FaraAgent._original_parse_thoughts_and_action = (
                FaraAgent._parse_thoughts_and_action
            )
            FaraAgent._parse_thoughts_and_action = safe_parse_thoughts_and_action
        else:
            logger.warning("Не удалось найти _parse_thoughts_and_action для патча.")
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
        }
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

        logger.info("Инициализация агента...")
        await agent.initialize()

        # Простая задача
        task = "Go to https://example.com and return the page title."
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
