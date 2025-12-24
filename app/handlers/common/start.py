from aiogram import types
from aiogram.filters import CommandStart
from aiogram.filters.state import StateFilter

from app.keyboards.default.base import base_kb, set_group_kb
from app.routers import common_router
from app.text import message_text as mt
from database.models.user import UserModel


@common_router.message(StateFilter(None), CommandStart())
async def _start_command(message: types.Message, user: UserModel) -> None:
    text = mt.WELCOME.format(
        message.from_user.id,
        message.from_user.full_name,
    )
    if user.group:
        kb = base_kb
    else:
        kb = set_group_kb
    await message.answer(
        text,
        reply_markup=kb,
    )
