"""
Модуль для мониторинга изменений в расписании из GitHub
Сравнивает текущее расписание с предыдущим и отправляет уведомления пользователям
"""

import asyncio
import json
from pathlib import Path
from typing import Dict, List, Optional, Set

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from data.config import DIR
from database.models.user import UserModel
from loader import bot
from utils.github_schedule import (
    EMOJI_BULB,
    EMOJI_FLASH,
    SEPARATOR_THICK,
    download_schedule_from_github,
    format_schedule_text,
    get_schedule,
    parse_group_number,
)
from utils.logging import logger

# Путь к файлу с предыдущим расписанием для сравнения
PREVIOUS_SCHEDULE_FILE = Path(DIR) / "data" / "previous_schedule_github.json"


class GitHubScheduleMonitor:
    """Мониторинг изменений расписания из GitHub"""

    def __init__(self):
        self.previous_file = PREVIOUS_SCHEDULE_FILE
        # Создаем директорию если не существует
        self.previous_file.parent.mkdir(parents=True, exist_ok=True)

    async def check_and_notify(self, session: AsyncSession) -> None:
        """
        Проверяет расписание на изменения и отправляет уведомления

        Args:
            session: Сессия БД для получения пользователей
        """
        try:
            logger.log("SCHEDULE", "Начинаю проверку расписания GitHub")

            # Получаем текущее расписание
            current_data = get_schedule()

            if not current_data:
                logger.error("Не удалось получить текущее расписание из GitHub")
                return

            # Загружаем предыдущее расписание
            previous_data = self._load_previous_schedule()

            # Если это первый запуск - просто сохраняем расписание
            if not previous_data:
                self._save_schedule(current_data)
                logger.log("SCHEDULE", "Первое сохранение расписания GitHub")
                return

            # Сравниваем расписания
            changed_groups = self._compare_schedules(previous_data, current_data)

            if changed_groups:
                logger.log("SCHEDULE", f"Обнаружены изменения в {len(changed_groups)} группах")
                await self._send_notifications(session, changed_groups, current_data)

                # Сохраняем новое расписание
                self._save_schedule(current_data)
            else:
                logger.log("SCHEDULE", "Изменений в расписании GitHub не обнаружено")

        except Exception as e:
            logger.error(f"Ошибка при проверке расписания GitHub: {e}")

    def _compare_schedules(self, previous_data: Dict, current_data: Dict) -> Set[str]:
        """
        Сравнивает два расписания и возвращает группы с изменениями

        Args:
            previous_data: Предыдущее расписание
            current_data: Текущее расписание

        Returns:
            Множество ключей групп с изменениями (например, {"GPV3.1", "GPV5.2"})
        """
        changed_groups = set()

        # Получаем данные фактов
        prev_fact = previous_data.get("fact", {}).get("data", {})
        curr_fact = current_data.get("fact", {}).get("data", {})

        # Получаем текущий день
        today = current_data.get("fact", {}).get("today")

        if not today:
            logger.warning("Не удалось определить текущий день")
            return changed_groups

        # Сравниваем расписания на сегодняшнюю дату
        today_str = str(today)
        prev_today = prev_fact.get(today_str, {})
        curr_today = curr_fact.get(today_str, {})

        # Проверяем каждую группу
        all_groups = set(prev_today.keys()) | set(curr_today.keys())

        for group_key in all_groups:
            prev_schedule = prev_today.get(group_key, {})
            curr_schedule = curr_today.get(group_key, {})

            # Сравниваем расписания
            if prev_schedule != curr_schedule:
                changed_groups.add(group_key)
                logger.log("SCHEDULE", f"Изменение обнаружено в группе {group_key}")

        return changed_groups

    async def _send_notifications(
        self, session: AsyncSession, changed_groups: Set[str], current_data: Dict
    ) -> None:
        """
        Отправляет уведомления пользователям об изменениях расписания

        Args:
            session: Сессия БД
            changed_groups: Множество ключей измененных групп
            current_data: Текущие данные расписания
        """
        for group_key in changed_groups:
            try:
                # Извлекаем номер группы из ключа (например, "GPV3.1" -> 3.1)
                group_number = self._extract_group_number(group_key)

                if not group_number:
                    logger.warning(f"Не удалось извлечь номер группы из '{group_key}'")
                    continue

                # Получаем пользователей этой группы с включенными уведомлениями
                users = await self._get_users_with_alerts(session, group_number)

                if not users:
                    logger.log(
                        "SCHEDULE", f"Нет пользователей с уведомлениями для группы {group_key}"
                    )
                    continue

                # Формируем текст уведомления
                notification_text = self._format_notification(group_key, current_data)

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
                    f"Отправлено {sent_count} уведомлений для группы {group_key}",
                )

            except Exception as e:
                logger.error(f"Ошибка при обработке группы {group_key}: {e}")

    @staticmethod
    def _extract_group_number(group_key: str) -> Optional[float]:
        """
        Извлекает номер группы из ключа

        Args:
            group_key: Ключ группы (например, "GPV3.1")

        Returns:
            Номер группы в виде float или None
        """
        import re

        # Убираем префикс GPV и парсим число
        match = re.search(r"GPV(\d+\.?\d*)", group_key)
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

    def _format_notification(self, group_key: str, current_data: Dict) -> str:
        """
        Форматирует текст уведомления об изменении расписания

        Args:
            group_key: Ключ группы (например, "GPV3.1")
            current_data: Текущие данные расписания

        Returns:
            Форматированный текст уведомления
        """
        # Получаем название группы
        preset = current_data.get("preset", {})
        group_names = preset.get("sch_names", {})
        group_name = group_names.get(group_key, group_key)

        # Извлекаем номер для форматирования
        group_number = self._extract_group_number(group_key)

        # Формируем заголовок уведомления
        text = f"{EMOJI_FLASH} <b>УВАГА! Розклад змінився</b>\n"
        text += f"{EMOJI_BULB} <b>Група: {group_name}</b>\n"
        text += f"\n{SEPARATOR_THICK}\n\n"

        # Добавляем актуальное расписание
        if group_number:
            try:
                schedule_text = format_schedule_text(str(group_number))
                # Убираем заголовок и первый разделитель из расписания
                lines = schedule_text.split("\n")
                # Пропускаем первые строки до второго разделителя
                schedule_start = 0
                separator_count = 0
                for i, line in enumerate(lines):
                    if "━" in line:
                        separator_count += 1
                        if separator_count == 1:
                            schedule_start = i + 2  # После разделителя и пустой строки
                            break

                if schedule_start > 0:
                    schedule_body = "\n".join(lines[schedule_start:])
                    text += schedule_body
                else:
                    text += schedule_text

            except Exception as e:
                logger.error(f"Ошибка форматирования расписания для уведомления: {e}")
                text += f"\n{EMOJI_BULB} Перевірте актуальний розклад командою /schedule"
        else:
            text += f"\n{EMOJI_BULB} Перевірте актуальний розклад командою /schedule"

        return text

    def _load_previous_schedule(self) -> Optional[Dict]:
        """
        Загружает предыдущее сохраненное расписание

        Returns:
            Словарь с предыдущим расписанием или None
        """
        try:
            if not self.previous_file.exists():
                return None

            with open(self.previous_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            return data

        except Exception as e:
            logger.error(f"Ошибка при загрузке предыдущего расписания: {e}")
            return None

    def _save_schedule(self, data: Dict) -> None:
        """
        Сохраняет расписание для последующего сравнения

        Args:
            data: Данные расписания для сохранения
        """
        try:
            with open(self.previous_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            logger.log("SCHEDULE", "Расписание GitHub сохранено для последующего сравнения")

        except Exception as e:
            logger.error(f"Ошибка при сохранении расписания: {e}")


# Создаем экземпляр монитора
github_schedule_monitor = GitHubScheduleMonitor()
