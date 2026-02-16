import asyncio

from aiogram.methods import DeleteWebhook

from app.commands import set_default_commands
from app.handlers import setup_handlers
from app.middlewares import setup_middlewares
from data.config import tgbot
from database.services.user import User
from loader import bot, dp
from utils.logging import logger


async def github_schedule_loader_task():
    """Фоновая задача для загрузки расписания с GitHub каждые 20 минут"""
    from utils.github_schedule import download_schedule_from_github

    # Загружаем сразу при старте
    logger.log("GITHUB", "Первоначальная загрузка расписания с GitHub")
    download_schedule_from_github()

    while True:
        try:
            # Ждем 20 минут (1200 секунд)
            await asyncio.sleep(1200)

            # Загружаем расписание
            download_schedule_from_github()
        except Exception as e:
            logger.error(f"Ошибка в задаче загрузки расписания с GitHub: {e}")


async def github_schedule_checker_task():
    """Фоновая задача для проверки изменений в GitHub расписании каждые 20 минут"""
    from app.business.github_schedule_monitor import github_schedule_monitor
    from database.connect import async_session

    # Ждем 2 минуты после запуска бота перед первой проверкой
    # (даем время на первую загрузку)
    await asyncio.sleep(120)

    while True:
        try:
            async with async_session() as session:
                await github_schedule_monitor.check_and_notify(session)
        except Exception as e:
            logger.error(f"Ошибка в задаче проверки GitHub расписания: {e}")

        # Ждем 20 минут (1200 секунд)
        await asyncio.sleep(1200)


async def schedule_checker_task():
    """Фоновая задача для проверки изменений в расписании каждые 30 минут"""
    from app.business.schedule_monitor import schedule_monitor
    from database.connect import async_session

    # Ждем 60 секунд после запуска бота перед первой проверкой
    await asyncio.sleep(60)

    while True:
        try:
            async with async_session() as session:
                await schedule_monitor.check_and_notify(session)
        except Exception as e:
            logger.error(f"Ошибка в задаче проверки расписания: {e}")

        # Ждем 30 минут (1800 секунд)
        await asyncio.sleep(1800)


async def on_startup() -> None:
    await set_default_commands()

    # Запускаем фоновую задачу загрузки расписания с GitHub
    asyncio.create_task(github_schedule_loader_task())

    # Запускаем фоновую задачу проверки изменений GitHub расписания
    asyncio.create_task(github_schedule_checker_task())

    # Запускаем фоновую задачу проверки расписания (старый метод)
    # asyncio.create_task(schedule_checker_task())

    logger.log("BOT", "~ Bot startup")


async def on_shutdown() -> None:
    logger.log("BOT", "~ Bot shutting down...")


async def main():
    setup_middlewares(dp)
    setup_handlers(dp)
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    await bot(DeleteWebhook(drop_pending_updates=tgbot.SKIP_UPDATES))
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
