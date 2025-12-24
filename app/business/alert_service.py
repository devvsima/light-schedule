from app.constans import REFERAL_SOURCES
from data.config import tgbot
from database.models.user import UserModel
from loader import bot
from utils.logging import logger

IS_ALERT = tgbot.NEW_USER_ALET_TO_GROUP
GROUP_ID = tgbot.MODERATOR_GROUP_ID


async def send_schedule_change_notification(user: UserModel, notification_text: str) -> bool:
    """
    Отправляет уведомление пользователю об изменении расписания

    Args:
        user: Модель пользователя
        notification_text: Текст уведомления

    Returns:
        True если отправлено успешно, False в случае ошибки
    """
    try:
        await bot.send_message(chat_id=user.id, text=notification_text, parse_mode="HTML")
        return True
    except Exception as e:
        logger.error(f"Ошибка отправки уведомления пользователю {user.id}: {e}")
        return False


async def new_user_alert_to_group(user: UserModel, code: str) -> None:
    """Отправляет уведомление в модераторскую группу о новом пользователе"""
    if IS_ALERT and GROUP_ID:
        try:
            text = "New user!\n<code>{}</code> (@{})".format(user.id, user.username)
            if code:
                text += "\n\nSource: {}".format(REFERAL_SOURCES[code])
            await bot.send_message(chat_id=tgbot.MODERATOR_GROUP_ID, text=text)
        except:
            logger.error("Сообщение в модераторскую группу не отправленно")
