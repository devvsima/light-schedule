from aiogram import types
from aiogram.filters.state import StateFilter
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.filters.user import IsGroupChange
from app.keyboards.default.base import base_kb
from app.routers import user_router
from app.states import GrouoChangeState
from database.models.user import UserModel
from database.services.user import User
from utils.light_schedule import format_schedule_to_text, get_all_groups, get_group_schedule


@user_router.message(StateFilter(None), IsGroupChange())
async def _example_command(message: types.Message, state: FSMContext) -> None:
    """Функционал бота ..."""
    await state.set_state(GrouoChangeState.group_change)

    text = """
Напишите название своей группы в таком формате:
    1.1,
    1.2,
    2.1,
    2.2,
    3.1,
    ...

"""
    await message.answer(text, parse_mode="HTML")


@user_router.message(StateFilter(GrouoChangeState.group_change))
async def _example_command(
    message: types.Message, user: UserModel, state: FSMContext, session: AsyncSession
) -> None:
    if group := to_float_or_none(message.text):
        await User.update(session=session, id=user.id, group=group)
    else:
        await message.answer("Указана неверная группа, попробуйте ещё раз")
        return

    await state.clear()
    await message.answer(
        f"Группа была изминена на:\n{message.text}",
        reply_markup=base_kb,
    )


def to_float_or_none(value: str):
    try:
        return float(value)
    except ValueError:
        return None
