import asyncio
import ast
import json
import logging
import sys

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

async def main():
    logger.info("Запуск FARA...")

    try:
        # Динамический импорт (если FARA не установлен, будет понятная ошибка)
        from fara import FaraAgent
        from fara.browser.browser_bb import BrowserBB

        def _safe_parse_thoughts_and_action(self, message: str):
            thoughts = message.strip()
            try:
                tmp = message.split("<tool_call>\n")
                if len(tmp) < 2:
                    self.logger.warning(
                        "Ответ без <tool_call>; завершаем с текущими мыслями."
                    )
                    return thoughts, {"arguments": {"action": "stop", "thoughts": thoughts}}

                thoughts = tmp[0].strip()
                tool_call_block = tmp[1]
                if "\n</tool_call>" not in tool_call_block:
                    self.logger.warning(
                        "Ответ без закрывающего </tool_call>; завершаем с текущими мыслями."
                    )
                    return thoughts, {"arguments": {"action": "stop", "thoughts": thoughts}}

                action_text = tool_call_block.split("\n</tool_call>")[0]
                try:
                    action = json.loads(action_text)
                except json.decoder.JSONDecodeError:
                    self.logger.error(f"Invalid action text: {action_text}", exc_info=True)
                    try:
                        action = ast.literal_eval(action_text)
                    except Exception:
                        self.logger.warning(
                            "Не удалось распарсить действие; завершаем с текущими мыслями."
                        )
                        action = {"arguments": {"action": "stop", "thoughts": thoughts}}

                if not isinstance(action, dict) or "arguments" not in action:
                    self.logger.warning(
                        "Ответ без arguments; завершаем с текущими мыслями."
                    )
                    action = {"arguments": {"action": "stop", "thoughts": thoughts}}
                elif "action" not in action["arguments"]:
                    self.logger.warning(
                        "Ответ без action; завершаем с текущими мыслями."
                    )
                    action = {"arguments": {"action": "stop", "thoughts": thoughts}}

                return thoughts, action
            except Exception:
                self.logger.error(
                    f"Error parsing thoughts and action: {message}", exc_info=True
                )
                return thoughts, {"arguments": {"action": "stop", "thoughts": thoughts}}

        FaraAgent._parse_thoughts_and_action = _safe_parse_thoughts_and_action
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
