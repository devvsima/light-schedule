"""
Модуль для отслеживания изменений расписания света и отправки уведомлений пользователям
"""

from datetime import datetime
from typing import Callable

import pytz
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from database.services.user import User
from utils.light_schedule import (
    format_schedule_to_text,
    get_changed_groups,
    load_previous_schedule,
    parse_electricity_schedule,
    save_current_schedule,
)


class ScheduleWatcher:
    """Класс для отслеживания изменений расписания"""

    def __init__(self, bot: Bot, user_service: User):
        self.bot = bot
        self.user_service = user_service
        self.scheduler = AsyncIOScheduler()

    async def check_schedule_changes(self) -> None:
        """
        Проверяет расписание на изменения и отправляет уведомления пользователям
        """
        try:
            # Загружаем предыдущее расписание
            previous_schedule = load_previous_schedule()

            # Получаем текущее расписание
            current_schedule = parse_electricity_schedule()

            if not current_schedule:
                print(f"[{datetime.now()}] Не удалось получить расписание")
                return

            # Сравниваем расписания
            changed_groups = get_changed_groups(previous_schedule, current_schedule)

            if changed_groups:
                print(f"[{datetime.now()}] Найдены изменения в {len(changed_groups)} группах")

                # Обрабатываем каждую измененную группу
                for change_info in changed_groups:
                    await self._notify_group_users(change_info)

                # Сохраняем новое расписание
                save_current_schedule()
                print(f"[{datetime.now()}] Расписание обновлено")
            else:
                print(f"[{datetime.now()}] Изменений не найдено")

        except Exception as e:
            print(f"[{datetime.now()}] Ошибка при проверке расписания: {e}")

    async def _notify_group_users(self, change_info: dict) -> None:
        """
        Отправляет уведомление пользователям группы об изменении расписания

        Args:
            change_info: Информация об изменении группы
        """
        group_name = change_info["group_name"]
        change_type = change_info["type"]

        # Извлекаем номер линии из названия группы (например, "Група 3.1" -> "3.1")
        try:
            line = group_name.split()[-1]  # Берем последний элемент
        except Exception:
            line = group_name

        try:
            # Получаем всех пользователей с этой линией
            users = await self.user_service.get_users_by_line(line)

            if not users:
                print(f"Пользователи с линией {line} не найдены")
                return

            for user in users:
                try:
                    if change_type == "updated":
                        # Отправляем обновленное расписание
                        new_schedule = change_info["new_schedule"]
                        message_text = f"⚡ <b>Расписание изменилось!</b>\n\n{format_schedule_to_text(new_schedule)}"
                    elif change_type == "new":
                        # Новая группа
                        schedule = change_info["schedule"]
                        message_text = f"✨ <b>Новая группа добавлена!</b>\n\n{format_schedule_to_text(schedule)}"
                    elif change_type == "deleted":
                        # Группа удалена
                        message_text = f"❌ <b>Группа {group_name} больше не активна</b>"
                    else:
                        continue

                    await self.bot.send_message(user.user_id, message_text, parse_mode="HTML")
                    print(
                        f"Уведомление отправлено пользователю {user.user_id} о группе {group_name}"
                    )

                except Exception as e:
                    print(f"Ошибка при отправке сообщения пользователю {user.user_id}: {e}")

        except Exception as e:
            print(f"Ошибка при получении пользователей линии {line}: {e}")

    def start(self, interval_minutes: int = 30) -> None:
        """
        Запускает планировщик для проверки расписания в 00:05 по Киеву

        Args:
            interval_minutes: Не используется, расписание проверяется в 00:05 по Киеву
        """
        # Устанавливаем временную зону Киева
        kyiv_tz = pytz.timezone("Europe/Kyiv")

        self.scheduler.add_job(
            self.check_schedule_changes,
            "cron",
            hour=0,
            minute=5,
            timezone=kyiv_tz,
            id="schedule_watcher",
            replace_existing=True,
        )

        if not self.scheduler.running:
            self.scheduler.start()
            print("ScheduleWatcher запущен, проверка расписания в 00:05 по Киеву")

    async def stop(self) -> None:
        """Останавливает планировщик"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            print("ScheduleWatcher остановлен")
