from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove

from loader import _

from .kb_generator import simple_kb_generator as gen

del_kb = ReplyKeyboardRemove()

base_kb = gen(["🗓 Розклад"], ["🔄 Змінити групу", "🔔 Сповіщення"])
set_group_kb = gen(["Вказати групу"])


def example_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(
        resize_keyboard=True,
        keyboard=[
            [
                KeyboardButton(text=("example")),
            ],
        ],
        one_time_keyboard=True,
    )
    return kb
