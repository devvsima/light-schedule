from aiogram import types
from aiogram.filters import CommandStart
from aiogram.filters.state import StateFilter

from app.keyboards.default.base import base_kb
from app.routers import common_router
from app.text import message_text as mt


@common_router.message(StateFilter(None), CommandStart())
async def _start_command(message: types.Message) -> None:
    text = mt.WELCOME.format(
        message.from_user.id,
        message.from_user.full_name,
    )

    await message.answer(
        text,
        reply_markup=base_kb,
    )
