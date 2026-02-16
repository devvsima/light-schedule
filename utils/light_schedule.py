import json
from datetime import datetime
from typing import Dict, List

import requests
from bs4 import BeautifulSoup

from data.config import schedule_url

url = schedule_url


def parse_electricity_schedule(url: str = url):
    """
    Парсит расписание отключения света с сайта alerts.org.ua
    """
    try:
        # Получаем HTML страницы
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        # Парсим HTML
        soup = BeautifulSoup(response.content, "html.parser")

        schedules = []

        # Ищем все группы расписания
        group_divs = soup.find_all("div", class_="js-group")

        print(f"Найдено групп: {len(group_divs)}\n")

        for group_div in group_divs:
            # Извлекаем ID группы
            group_id = group_div.get("data-group-id", "unknown")

            # Извлекаем имя группы
            group_name = group_div.find("b", class_="group-name")
            if group_name:
                # Очищаем текст от лишних символов
                name_text = group_name.get_text(strip=True)
            else:
                name_text = "Unknown"

            # Ищем периоды времени
            periods = []
            period_divs = group_div.find_all("div", class_="period")

            if period_divs:
                for period_div in period_divs:
                    time_entries = period_div.find_all("div")

                    for entry in time_entries:
                        start_time = entry.get("data-start")
                        end_time = entry.get("data-end")

                        if start_time and end_time:
                            # Определяем статус (ON/OFF)
                            status_elem = entry.find("b", class_=["on", "off"])
                            if status_elem:
                                status = status_elem.get_text(strip=True)
                            else:
                                status = "UNKNOWN"

                            periods.append({"start": start_time, "end": end_time, "status": status})

            if periods:  # Только если есть периоды
                schedules.append(
                    {"group_id": group_id, "group_name": name_text, "periods": periods}
                )

        return schedules

    except requests.exceptions.RequestException as e:
        print(f"Ошибка при загрузке страницы: {e}")
        return []
    except Exception as e:
        print(f"Ошибка при парсинге: {e}")
        return []


def print_schedule(schedules: List[Dict]) -> None:
    """
    Выводит расписание в JSON формате
    """
    if not schedules:
        print(json.dumps({"error": "Расписание не найдено"}, ensure_ascii=False, indent=2))
        return

    output = {"timestamp": datetime.now().strftime("%d.%m.%Y %H:%M:%S"), "schedules": schedules}
    print(json.dumps(output, ensure_ascii=False, indent=2))


def save_schedule_to_file(schedules: List[Dict], filename: str = "schedule.json") -> None:
    """
    Сохраняет расписание в JSON файл
    """
    output = {"timestamp": datetime.now().strftime("%d.%m.%Y %H:%M:%S"), "schedules": schedules}

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nРасписание сохранено в файл: {filename}")


def get_all_groups(url: str = url) -> List[str]:
    """
    Получает список всех доступных групп

    Returns:
        Список названий всех групп
    """
    schedules = parse_electricity_schedule(url)
    return [schedule["group_name"] for schedule in schedules]


def get_group_schedule(group_name: str, url: str = url) -> Dict | None:
    """
    Получает расписание для конкретной группы

    Args:
        group_name: Название группы (например, "Група 3.1")
        url: URL для парсинга

    Returns:
        Словарь с данными группы или None если группа не найдена
    """
    schedules = parse_electricity_schedule(url)

    # Пробуем точное совпадение
    for schedule in schedules:
        if schedule["group_name"].lower() == group_name.lower():
            return schedule

    # Пробуем частичное совпадение (если содержит подстроку)
    for schedule in schedules:
        if group_name.lower() in schedule["group_name"].lower():
            return schedule

    return None


def format_schedule_to_text(schedule: Dict) -> str:
    """
    Преобразует расписание в удобный текстовый формат

    Args:
        schedule: Словарь со расписанием группы

    Returns:
        Форматированная строка расписания
    """
    if not schedule:
        return "Расписание не найдено"

    group_name = schedule.get("group_name", "Unknown")
    periods = schedule.get("periods", [])

    # Telegram-эмодзи для статусов
    EMOJI_ON = '<tg-emoji emoji-id="5228957330934111865">🌞</tg-emoji>'
    EMOJI_OFF = '<tg-emoji emoji-id="5228852207314573962">🌑</tg-emoji>'
    EMOJI_UNKNOWN = '<tg-emoji emoji-id="5228758276379809110">🤷‍♂️</tg-emoji>'

    text = f"💡 <b>{group_name}</b>\n\n"

    # Подсчет часов
    total_hours_on = 0.0
    total_hours_off = 0.0

    for period in periods:
        start = period.get("start", "??:??")
        end = period.get("end", "??:??")
        status = period.get("status", "UNKNOWN")

        # Вычисляем длительность периода
        duration_hours = 0.0
        duration_text = ""
        try:
            start_h, start_m = map(int, start.split(":"))
            end_h, end_m = map(int, end.split(":"))

            # Конвертируем в минуты
            start_minutes = start_h * 60 + start_m
            end_minutes = end_h * 60 + end_m

            # Обрабатываем переход через полночь
            if end_minutes < start_minutes:
                end_minutes += 24 * 60

            duration_hours = (end_minutes - start_minutes) / 60

            # Форматируем длительность
            if duration_hours == int(duration_hours):
                hours_int = int(duration_hours)
                if hours_int == 1:
                    duration_text = f" ({hours_int} год)"
                else:
                    duration_text = f" ({hours_int} год)"
            else:
                duration_text = f" ({duration_hours:.1f} год)"

            if status == "ON":
                total_hours_on += duration_hours
            elif status == "OFF":
                total_hours_off += duration_hours
        except:
            pass

        # Иконка в зависимости от статуса
        icon = EMOJI_ON if status == "ON" else EMOJI_OFF if status == "OFF" else EMOJI_UNKNOWN
        status_text = (
            "включено" if status == "ON" else "отключено" if status == "OFF" else "невідомо"
        )

        text += f"{icon} <code>{start} - {end}</code>:{duration_text} {status_text}\n"

    # Добавляем итоговую статистику
    text += "\n" + "─" * 30 + "\n"
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

    text += f"{EMOJI_ON} Світло буде: <b>{hours_on_str}</b> год.\n"
    text += f"{EMOJI_OFF} Світла не буде: <b>{hours_off_str}</b> год.\n"

    return text


def save_current_schedule(filename: str = "current_schedule.json") -> None:
    """
    Сохраняет текущее расписание для последующего сравнения
    """
    schedules = parse_electricity_schedule()
    save_schedule_to_file(schedules, filename)


def load_previous_schedule(filename: str = "current_schedule.json") -> List[Dict]:
    """
    Загружает последнее сохраненное расписание
    """
    try:
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("schedules", [])
    except FileNotFoundError:
        return []
    except Exception as e:
        print(f"Ошибка при загрузке расписания: {e}")
        return []


def get_changed_groups(previous: List[Dict], current: List[Dict]) -> List[Dict]:
    """
    Сравнивает два расписания и возвращает группы, которые изменились

    Args:
        previous: Предыдущее расписание
        current: Текущее расписание

    Returns:
        Список групп с изменениями и информацией о них
    """
    changed_groups = []

    # Создаем словари для быстрого поиска
    prev_map = {s["group_name"]: s for s in previous}
    curr_map = {s["group_name"]: s for s in current}

    # Проверяем все текущие группы
    for group_name, curr_schedule in curr_map.items():
        if group_name not in prev_map:
            # Новая группа
            changed_groups.append(
                {"group_name": group_name, "type": "new", "schedule": curr_schedule}
            )
        else:
            prev_schedule = prev_map[group_name]
            # Сравниваем периоды
            if prev_schedule["periods"] != curr_schedule["periods"]:
                changed_groups.append(
                    {
                        "group_name": group_name,
                        "type": "updated",
                        "old_schedule": prev_schedule,
                        "new_schedule": curr_schedule,
                    }
                )

    # Проверяем удаленные группы
    for group_name in prev_map:
        if group_name not in curr_map:
            changed_groups.append({"group_name": group_name, "type": "deleted"})

    return changed_groups
