from aiogram import types
from aiogram.filters.state import StateFilter

from app.filters.user import IsShedule
from app.routers import user_router
from database.models.user import UserModel
from utils.light_schedule import format_schedule_to_text, get_all_groups, get_group_schedule


@user_router.message(StateFilter(None), IsShedule())
async def _example_command(message: types.Message, user: UserModel) -> None:
    """Функционал бота ..."""

    schedule = get_group_schedule(group_name=f"Група {user.group}")
    text = format_schedule_to_text(schedule)
    await message.answer(text, parse_mode="HTML")
