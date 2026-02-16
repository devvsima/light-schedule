"""
Модуль для работы с расписанием отключений света из GitHub
Загружает данные из JSON файла с репозитория Baskerville42/outage-data-ua
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import requests

from data.config import DIR
from utils.logging import logger

# URL для загрузки данных с GitHub
GITHUB_JSON_URL = (
    "https://raw.githubusercontent.com/Baskerville42/outage-data-ua/main/data/kyiv-region.json"
)

# Путь к локальному файлу с расписанием
SCHEDULE_FILE = Path(DIR) / "kyiv-region.json"

# ═══════════════════════════════════════════════════════════════
# НАСТРОЙКА ЭМОДЗИ ДЛЯ СТАТУСОВ СВЕТА
# ═══════════════════════════════════════════════════════════════

# Эмодзи для статусов света
EMOJI_LIGHT_ON = '<tg-emoji emoji-id="5228957330934111865">🌞</tg-emoji>'  # Світло є
EMOJI_LIGHT_OFF = '<tg-emoji emoji-id="5228852207314573962">🌑</tg-emoji>'  # Світла немає
EMOJI_MAYBE_OFF = (
    '<tg-emoji emoji-id="5231399367734235038">🤷‍♂️</tg-emoji>'  # Можливо відключення / частково
)
EMOJI_OFF_FIRST_30 = (
    '<tg-emoji emoji-id="5231399367734235038">🤷‍♂️</tg-emoji>'  # Відключення перші 30 хв
)
EMOJI_OFF_SECOND_30 = (
    '<tg-emoji emoji-id="5231399367734235038">🤷‍♂️</tg-emoji>'  # Відключення другі 30 хв
)
EMOJI_UNKNOWN = "❓"  # Невідомо

# Эмодзи для временных блоков
EMOJI_NIGHT = "🌙"  # Ночь
EMOJI_MORNING = "🌅"  # Утро
EMOJI_DAY = "☀️"  # День
EMOJI_EVENING = "🌆"  # Вечер

# Эмодзи для заголовков и декора
EMOJI_BULB = "💡"  # Лампочка (заголовок)
EMOJI_CALENDAR = "📅"  # Календарь (дата)
EMOJI_CLOCK = "🕐"  # Часы (время обновления)
EMOJI_INFO = "ℹ️"  # Информация
EMOJI_FLASH = "⚡"  # Молния (для акцентов)

# Визуальные разделители
SEPARATOR_THIN = "─" * 10
SEPARATOR_THICK = "━" * 10
SEPARATOR_DOTS = "· · · · · · · · ·"


def download_schedule_from_github() -> Optional[Dict]:
    """
    Загружает расписание с GitHub

    Returns:
        Словарь с данными расписания или None при ошибке
    """
    try:
        logger.log("GITHUB", f"Загрузка расписания с GitHub: {GITHUB_JSON_URL}")
        response = requests.get(GITHUB_JSON_URL, timeout=10)
        response.raise_for_status()

        data = response.json()

        # Сохраняем локально
        with open(SCHEDULE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.log("GITHUB", "✅ Расписание успешно загружено и сохранено")
        return data

    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при загрузке данных с GitHub: {e}")
        return None
    except Exception as e:
        logger.error(f"Неожиданная ошибка при загрузке расписания: {e}")
        return None


def load_local_schedule() -> Optional[Dict]:
    """
    Загружает расписание из локального файла

    Returns:
        Словарь с данными расписания или None если файл не найден
    """
    try:
        if not SCHEDULE_FILE.exists():
            logger.log("GITHUB", "Локальный файл расписания не найден")
            return None

        with open(SCHEDULE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        return data

    except Exception as e:
        logger.error(f"Ошибка при загрузке локального расписания: {e}")
        return None


def get_schedule() -> Optional[Dict]:
    """
    Получает расписание (сначала пытается загрузить из локального файла)

    Returns:
        Словарь с данными расписания
    """
    data = load_local_schedule()

    if not data:
        logger.log("GITHUB", "Локальное расписание не найдено, загружаю с GitHub")
        data = download_schedule_from_github()

    return data


def parse_group_number(group_input: str) -> Optional[str]:
    """
    Преобразует ввод пользователя в ключ группы

    Args:
        group_input: Ввод пользователя (например "3.1", "GPV3.1", "3.2")

    Returns:
        Ключ группы в формате "GPV3.1" или None если не удалось распарсить
    """
    # Убираем пробелы и приводим к верхнему регистру
    group_input = group_input.strip().upper()

    # Если уже в правильном формате
    if group_input.startswith("GPV"):
        return group_input

    # Пытаемся распарсить формат "3.1", "3.2" и т.д.
    try:
        # Удаляем все лишнее, оставляем только цифры и точки
        cleaned = "".join(c for c in group_input if c.isdigit() or c == ".")

        if "." in cleaned:
            parts = cleaned.split(".")
            if len(parts) == 2:
                main_group = parts[0]
                sub_group = parts[1]
                return f"GPV{main_group}.{sub_group}"

    except Exception:
        pass

    return None


def get_group_schedule_for_day(group_key: str, timestamp: Optional[int] = None) -> Optional[Dict]:
    """
    Получает расписание для группы на конкретный день

    Args:
        group_key: Ключ группы (например "GPV3.1")
        timestamp: Unix timestamp дня (если None, берется сегодня)

    Returns:
        Словарь с расписанием по часам или None если не найдено
    """
    data = get_schedule()

    if not data:
        return None

    # Получаем данные фактического расписания
    fact_data = data.get("fact", {}).get("data", {})

    # Если timestamp не указан, берем сегодняшний день
    if timestamp is None:
        timestamp = data.get("fact", {}).get("today")

    if not timestamp:
        logger.error("Не удалось определить текущий день")
        return None

    # Получаем расписание для дня
    day_schedule = fact_data.get(str(timestamp), {})

    # Получаем расписание для группы
    group_schedule = day_schedule.get(group_key)

    return group_schedule


def format_schedule_text(group_input: str, timestamp: Optional[int] = None) -> str:
    """
    Форматирует расписание группы в текстовый вид

    Args:
        group_input: Ввод группы (например "3.1")
        timestamp: Unix timestamp дня

    Returns:
        Форматированная строка с расписанием
    """
    # Парсим номер группы
    group_key = parse_group_number(group_input)

    if not group_key:
        return f"❌ Не удалось определить группу из ввода: {group_input}\n\nПример: 3.1 или GPV3.1"

    # Получаем расписание
    schedule = get_group_schedule_for_day(group_key, timestamp)

    if not schedule:
        return f"❌ Расписание для группы {group_key} не найдено"

    # Получаем данные для форматирования
    data = get_schedule()
    preset = data.get("preset", {})

    # Получаем название группы
    group_names = preset.get("sch_names", {})
    group_name = group_names.get(group_key, group_key)

    # Получаем описания статусов
    time_types = preset.get("time_type", {})

    # ═══════════════════════════════════════════════════════════
    # ФОРМИРУЕМ ЗАГОЛОВОК
    # ═══════════════════════════════════════════════════════════
    text = f"{EMOJI_BULB} <b>{group_name}</b>\n\n"

    # ═══════════════════════════════════════════════════════════
    # ФОРМИРУЕМ КОМПАКТНОЕ РАСПИСАНИЕ (ОБЪЕДИНЯЕМ ПЕРИОДЫ)
    # ═══════════════════════════════════════════════════════════

    # Подсчет часов
    total_hours_on = 0.0
    total_hours_off = 0.0
    total_hours_uncertain = 0.0

    # Группируем последовательные часы с одинаковым статусом
    periods = []
    current_status = None
    period_start = 0

    for hour in range(1, 25):
        status = schedule.get(str(hour), "unknown")

        if status != current_status:
            # Завершаем предыдущий период
            if current_status is not None:
                periods.append({"start": period_start, "end": hour - 1, "status": current_status})

            # Начинаем новый период
            current_status = status
            period_start = hour - 1

    # Завершаем последний период
    if current_status is not None:
        periods.append({"start": period_start, "end": 24, "status": current_status})

    # Выводим периоды
    for period in periods:
        start_time = f"{period['start']:02d}:00"
        end_time = f"{period['end']:02d}:00" if period["end"] < 24 else "24:00"
        status = period["status"]

        # Вычисляем длительность периода
        duration = period["end"] - period["start"]

        # Подсчитываем часы для статистики
        if status == "yes":
            total_hours_on += duration
        elif status == "no":
            total_hours_off += duration
        elif status in ["first", "second"]:
            # Половина часа без света, половина со светом
            total_hours_off += duration * 0.5
            total_hours_on += duration * 0.5
        elif status in ["maybe", "mfirst", "msecond"]:
            total_hours_uncertain += duration

        # Форматируем длительность
        if duration == int(duration):
            duration_int = int(duration)
            duration_text = f" ({duration_int} год)"
        else:
            duration_text = f" ({duration:.1f} год)"

        # Определяем иконку и текст статуса
        icon, status_text = _get_status_icon_and_text(status, time_types)

        text += f"{icon} <code>{start_time} - {end_time}</code>:{duration_text} {status_text}\n\n"

    # ═══════════════════════════════════════════════════════════
    # СТАТИСТИКА
    # ═══════════════════════════════════════════════════════════
    text += f"\n{SEPARATOR_THIN}\n"
    text += f"<b>📊 Загальна статистика:</b>\n"

    # Форматируем часы красиво (целые числа без дробей, дроби с одним знаком)
    hours_on_str = (
        f"{int(total_hours_on)}"
        if total_hours_on == int(total_hours_on)
        else f"{total_hours_on:.1f}"
    )
    hours_off_str = (
        f"{int(total_hours_off)}"
        if total_hours_off == int(total_hours_off)
        else f"{total_hours_off:.1f}"
    )

    text += f"{EMOJI_LIGHT_ON} Світло буде: <b>{hours_on_str}</b> год.\n"
    text += f"{EMOJI_LIGHT_OFF} Світла не буде: <b>{hours_off_str}</b> год.\n"

    if total_hours_uncertain > 0:
        hours_uncertain_str = (
            f"{int(total_hours_uncertain)}"
            if total_hours_uncertain == int(total_hours_uncertain)
            else f"{total_hours_uncertain:.1f}"
        )
        text += f"{EMOJI_MAYBE_OFF} Невідомо: <b>{hours_uncertain_str}</b> год.\n"

    return text


def _get_status_icon_and_text(status: str, time_types: Dict) -> tuple[str, str]:
    """
    Возвращает иконку и текст для статуса

    Args:
        status: Статус из расписания
        time_types: Словарь с описаниями статусов

    Returns:
        Кортеж (иконка, текст_статуса)
    """
    status_map = {
        "yes": (EMOJI_LIGHT_ON, time_types.get("yes", "Світло є")),
        "no": (EMOJI_LIGHT_OFF, time_types.get("no", "Світла немає")),
        "maybe": (EMOJI_MAYBE_OFF, time_types.get("maybe", "Можливо відключення")),
        "first": (EMOJI_OFF_FIRST_30, time_types.get("first", "Світла не буде перші 30 хв.")),
        "second": (EMOJI_OFF_SECOND_30, time_types.get("second", "Світла не буде другі 30 хв")),
        "mfirst": (
            EMOJI_MAYBE_OFF,
            time_types.get("mfirst", "Світла можливо не буде перші 30 хв."),
        ),
        "msecond": (
            EMOJI_MAYBE_OFF,
            time_types.get("msecond", "Світла можливо не буде другі 30 хв"),
        ),
    }

    if status in status_map:
        return status_map[status]
    else:
        return (EMOJI_UNKNOWN, "Невідомо")


def get_all_available_groups() -> List[str]:
    """
    Получает список всех доступных групп

    Returns:
        Список ключей групп
    """
    data = get_schedule()

    if not data:
        return []

    preset = data.get("preset", {})
    group_names = preset.get("sch_names", {})

    return list(group_names.keys())


def get_group_display_name(group_key: str) -> str:
    """
    Получает отображаемое название группы

    Args:
        group_key: Ключ группы (например "GPV3.1")

    Returns:
        Название группы для отображения
    """
    data = get_schedule()

    if not data:
        return group_key

    preset = data.get("preset", {})
    group_names = preset.get("sch_names", {})

    return group_names.get(group_key, group_key)
