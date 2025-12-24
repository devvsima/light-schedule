import asyncio

from aiogram.methods import DeleteWebhook

from app.commands import set_default_commands
from app.handlers import setup_handlers
from app.middlewares import setup_middlewares
from data.config import tgbot
from database.services.user import User
from loader import bot, dp
from utils.logging import logger


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
        await asyncio.sleep(18)


async def on_startup() -> None:
    await set_default_commands()

    # Запускаем фоновую задачу проверки расписания
    asyncio.create_task(schedule_checker_task())

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
