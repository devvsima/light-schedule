from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.services.base import BaseService
from utils.logging import logger

from ..models.user import UserModel


class User(BaseService):
    model = UserModel

    async def get_or_create(
        session: AsyncSession, id: int, username: str = None, language: str = None
    ) -> UserModel:
        if user := await User.get_by_id(session, id):
            return user, False
        await User.create(session, id=id, username=username, language=language)
        user = await User.get_by_id(session, id)
        return user, True

    @staticmethod
    async def increment_referral_count(
        session: AsyncSession, user: UserModel, num: int = 1
    ) -> None:
        """Добавляет приведенного реферала к пользователю {inviter_id}"""
        user.referral += num
        await session.commit()
        logger.log("DATABASE", f"{user.id} (@{user.username}): привел нового пользователя")

    @staticmethod
    async def get_users_by_line(session: AsyncSession, line: str | float) -> list[UserModel]:
        """
        Получает всех пользователей с определенной линией (группой)

        Args:
            session: Сессия БД
            line: Номер линии/группы (например, "3.1")

        Returns:
            Список пользователей с данной линией
        """
        try:
            line_float = float(line)
        except (ValueError, TypeError):
            return []

        stmt = select(UserModel).where(UserModel.line == line_float)
        result = await session.execute(stmt)
        return result.scalars().all()
