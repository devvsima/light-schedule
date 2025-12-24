from aiogram import types
from aiogram.filters.state import StateFilter
from sqlalchemy.ext.asyncio import AsyncSession

from app.filters.user import IsToggleAlerts
from app.keyboards.default.base import base_kb
from app.routers import user_router
from database.models.user import UserModel
from database.services.user import User


@user_router.message(StateFilter(None), IsToggleAlerts())
async def toggle_alerts_handler(
    message: types.Message, user: UserModel, session: AsyncSession
) -> None:
    """Переключает состояние уведомлений для пользователя"""

    # Переключаем статус уведомлений
    new_status = not user.is_alerts
    await User.update(session=session, id=user.id, is_alerts=new_status)

    if new_status:
        text = "✅ <b>Уведомления включены</b>\n\nТеперь вы будете получать уведомления об изменениях в расписании вашей группы."
    else:
        text = "🔕 <b>Уведомления выключены</b>\n\nВы больше не будете получать уведомления об изменениях в расписании."

    await message.answer(text, reply_markup=base_kb, parse_mode="HTML")
