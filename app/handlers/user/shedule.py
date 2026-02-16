from aiogram import types
from aiogram.filters import Command
from aiogram.filters.state import StateFilter

from app.filters.user import IsShedule
from app.routers import user_router
from database.models.user import UserModel
from utils.github_schedule import format_schedule_text, get_all_available_groups, parse_group_number
from utils.light_schedule import format_schedule_to_text, get_all_groups, get_group_schedule


@user_router.message(StateFilter(None), Command("schedule"))
async def schedule_command(message: types.Message, user: UserModel) -> None:
    """Команда для получения расписания отключений света"""

    # Если у пользователя установлена группа, показываем расписание для неё
    if user.group:
        try:
            text = format_schedule_text(str(user.group))
            await message.answer(text, parse_mode="HTML")
        except Exception as e:
            await message.answer("❌ Помилка при отриманні розкладу. Спробуйте пізніше.")
    else:
        # Если группа не установлена, показываем инструкцию
        groups = get_all_available_groups()
        groups_text = ", ".join([g.replace("GPV", "") for g in groups])

        text = (
            "💡 <b>Розклад відключень світла</b>\n\n"
            "Для отримання розкладу відправте номер вашої групи.\n\n"
            f"Доступні групи: {groups_text}\n\n"
            "Наприклад: <code>3.1</code> або <code>5.2</code>"
        )
        await message.answer(text, parse_mode="HTML")


@user_router.message(StateFilter(None), IsShedule())
async def schedule_button_handler(message: types.Message, user: UserModel) -> None:
    """Обработчик кнопки/команды расписания"""

    # Если у пользователя установлена группа, показываем расписание для неё
    if user.group:
        try:
            text = format_schedule_text(str(user.group))
            await message.answer(text, parse_mode="HTML")
        except Exception as e:
            await message.answer("❌ Помилка при отриманні розкладу. Спробуйте пізніше.")
    else:
        # Если группа не установлена, показываем инструкцию
        groups = get_all_available_groups()
        groups_text = ", ".join([g.replace("GPV", "") for g in groups])

        text = (
            "💡 <b>Розклад відключень світла</b>\n\n"
            "Для отримання розкладу спочатку встановіть вашу групу через кнопку "
            '"🔄 Змінити групу" або відправте номер групи.\n\n'
            f"Доступні групи: {groups_text}\n\n"
            "Наприклад: <code>3.1</code> або <code>5.2</code>"
        )
        await message.answer(text, parse_mode="HTML")


@user_router.message(StateFilter(None))
async def group_number_handler(message: types.Message, user: UserModel) -> None:
    """Обработка прямого ввода номера группы"""

    # Проверяем, что это похоже на номер группы
    group_key = parse_group_number(message.text)

    if not group_key:
        # Не номер группы, игнорируем
        return

    # Пытаемся получить расписание
    try:
        text = format_schedule_text(message.text)
        await message.answer(text, parse_mode="HTML")
    except Exception as e:
        await message.answer(
            "❌ Групу не знайдено. Перевірте правильність введення.\n\n"
            "Приклад: <code>3.1</code> або <code>5.2</code>",
            parse_mode="HTML",
        )
