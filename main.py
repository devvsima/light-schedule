import asyncio

from aiogram.methods import DeleteWebhook

from app.business.schedule_watcher import ScheduleWatcher
from app.commands import set_default_commands
from app.handlers import setup_handlers
from app.middlewares import setup_middlewares
from data.config import tgbot
from database.services.user import User
from loader import bot, dp
from utils.logging import logger

# Глобальная переменная для хранения ScheduleWatcher
schedule_watcher = None


async def on_startup() -> None:
    global schedule_watcher
    await set_default_commands()

    schedule_watcher = ScheduleWatcher(bot, User)
    schedule_watcher.start(interval_minutes=30)  # Проверка каждые 30 минут

    logger.log("BOT", "~ Bot startup")


async def on_shutdown() -> None:
    global schedule_watcher
    if schedule_watcher:
        await schedule_watcher.stop()
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
