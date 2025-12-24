import asyncio
import json
from pathlib import Path
from typing import Dict, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from data.config import DIR
from database.models.user import UserModel
from loader import bot
from utils.light_schedule import (
    format_schedule_to_text,
    get_changed_groups,
    parse_electricity_schedule,
)
from utils.logging import logger

# Путь к файлу с сохраненным расписанием
SCHEDULE_FILE = Path(DIR) / "data" / "current_schedule.json"


class ScheduleMonitor:
    """Сервис для мониторинга изменений расписания и отправки уведомлений"""

    def __init__(self):
        self.schedule_file = SCHEDULE_FILE
        # Создаем директорию если не существует
        self.schedule_file.parent.mkdir(parents=True, exist_ok=True)

    async def check_and_notify(self, session: AsyncSession) -> None:
        """
        Проверяет расписание на изменения и отправляет уведомления

        Args:
            session: Сессия БД для получения пользователей
        """
        try:
            logger.log("SCHEDULE", "Начинаю проверку расписания")

            # Получаем текущее расписание
            current_schedules = parse_electricity_schedule()

            if not current_schedules:
                logger.error("Не удалось получить текущее расписание")
                return

            # Загружаем предыдущее расписание
            previous_schedules = self._load_previous_schedule()

            # Если это первый запуск - просто сохраняем расписание
            if not previous_schedules:
                self._save_schedule(current_schedules)
                logger.log("SCHEDULE", "Первое сохранение расписания")
                return

            # Сравниваем расписания
            changed_groups = get_changed_groups(previous_schedules, current_schedules)

            if changed_groups:
                logger.log("SCHEDULE", f"Обнаружены изменения в {len(changed_groups)} группах")
                await self._send_notifications(session, changed_groups)

                # Сохраняем новое расписание
                self._save_schedule(current_schedules)
            else:
                logger.log("SCHEDULE", "Изменений в расписании не обнаружено")

        except Exception as e:
            logger.error(f"Ошибка при проверке расписания: {e}")

    async def _send_notifications(self, session: AsyncSession, changed_groups: List[Dict]) -> None:
        """
        Отправляет уведомления пользователям об изменениях расписания

        Args:
            session: Сессия БД
            changed_groups: Список изменившихся групп
        """
        for change in changed_groups:
            group_name = change["group_name"]
            change_type = change["type"]

            try:
                # Извлекаем номер группы из названия (например, "Група 3.1" -> 3.1)
                group_number = self._extract_group_number(group_name)

                if not group_number:
                    logger.warning(f"Не удалось извлечь номер группы из '{group_name}'")
                    continue

                # Получаем пользователей этой группы с включенными уведомлениями
                users = await self._get_users_with_alerts(session, group_number)

                if not users:
                    logger.log(
                        "SCHEDULE", f"Нет пользователей с уведомлениями для группы {group_name}"
                    )
                    continue

                # Формируем текст уведомления
                notification_text = self._format_notification(change)

                # Отправляем уведомления всем пользователям
                sent_count = 0
                for user in users:
                    try:
                        await bot.send_message(
                            chat_id=user.id, text=notification_text, parse_mode="HTML"
                        )
                        sent_count += 1
                        # Небольшая задержка между отправками
                        await asyncio.sleep(0.05)
                    except Exception as e:
                        logger.error(f"Ошибка отправки уведомления пользователю {user.id}: {e}")

                logger.log(
                    "SCHEDULE",
                    f"Отправлено {sent_count} уведомлений для группы {group_name}",
                )

            except Exception as e:
                logger.error(f"Ошибка при обработке группы {group_name}: {e}")

    @staticmethod
    def _extract_group_number(group_name: str) -> float | None:
        """
        Извлекает номер группы из названия

        Args:
            group_name: Название группы (например, "Група 3.1")

        Returns:
            Номер группы в виде float или None
        """
        import re

        # Ищем паттерн вида "число.число" или просто "число"
        match = re.search(r"(\d+\.?\d*)", group_name)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None
        return None

    @staticmethod
    async def _get_users_with_alerts(session: AsyncSession, group_number: float) -> List[UserModel]:
        """
        Получает пользователей группы с включенными уведомлениями

        Args:
            session: Сессия БД
            group_number: Номер группы

        Returns:
            Список пользователей
        """
        stmt = (
            select(UserModel)
            .where(UserModel.group == group_number)
            .where(UserModel.is_alerts == True)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    def _format_notification(change: Dict) -> str:
        """
        Форматирует текст уведомления об изменении расписания

        Args:
            change: Словарь с информацией об изменении

        Returns:
            Форматированный текст уведомления
        """
        change_type = change["type"]
        group_name = change["group_name"]

        if change_type == "new":
            text = f"🆕 <b>Новое расписание для {group_name}</b>\n\n"
            text += format_schedule_to_text(change["schedule"])
        elif change_type == "updated":
            text = f"🔄 <b>Расписание изменилось для {group_name}</b>\n\n"
            text += "<b>Новое расписание:</b>\n"
            text += format_schedule_to_text(change["new_schedule"])
        elif change_type == "deleted":
            text = f"⚠️ <b>Расписание удалено для {group_name}</b>\n\n"
            text += "Пожалуйста, проверьте актуальную информацию."
        else:
            text = f"ℹ️ Изменение в расписании для {group_name}"

        return text

    def _load_previous_schedule(self) -> List[Dict]:
        """
        Загружает предыдущее сохраненное расписание

        Returns:
            Список расписаний или пустой список
        """
        try:
            if not self.schedule_file.exists():
                return []

            with open(self.schedule_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("schedules", [])
        except Exception as e:
            logger.error(f"Ошибка при загрузке предыдущего расписания: {e}")
            return []

    def _save_schedule(self, schedules: List[Dict]) -> None:
        """
        Сохраняет расписание в файл

        Args:
            schedules: Список расписаний
        """
        try:
            from datetime import datetime

            output = {
                "timestamp": datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
                "schedules": schedules,
            }

            with open(self.schedule_file, "w", encoding="utf-8") as f:
                json.dump(output, f, ensure_ascii=False, indent=2)

            logger.log("SCHEDULE", f"Расписание сохранено в {self.schedule_file}")
        except Exception as e:
            logger.error(f"Ошибка при сохранении расписания: {e}")


# Создаем глобальный экземпляр монитора
schedule_monitor = ScheduleMonitor()
