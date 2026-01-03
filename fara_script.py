import asyncio
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
    except ImportError as e:
        logger.error(f"Ошибка импорта FARA: {e}")
        logger.info("Проверьте установку FARA: pip install -e /fara")
        return 1

    # Вариант 1: С Ollama (используем внешний контейнер из сети fara-ollama)
    client_config = {
        "model": "maternion/fara:7b",
        "base_url": "http://host.docker.internal:11434/v1",
        "api_key": "ollama",
        "timeout": 30.0
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
