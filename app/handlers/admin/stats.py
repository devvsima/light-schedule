from aiogram import types
from aiogram.filters import Command
from aiogram.filters.state import StateFilter
from sqlalchemy.ext.asyncio import AsyncSession

from app.routers import admin_router
from database.services.user import User


@admin_router.message(StateFilter(None), Command("stats"))
async def _stats_command(message: types.Message, session: AsyncSession) -> None:
    all_users = await User.get_all(session)
    await message.answer(f"Users: {len(all_users)}")
