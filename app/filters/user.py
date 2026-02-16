from aiogram.filters import Filter
from aiogram.types import Message

GROUP_CHANGE_TUPLE = (
    "/group",
    "Вказати групу",
    "🔄 Змінити групу",
)
SHEDULE_TUPLE = (
    "/schedule",
    "🗓 Розклад",
)
ALERTS_TOGGLE_TUPLE = (
    "/alerts",
    "🔔 Сповіщення",
)


class IsGroupChange(Filter):
    async def __call__(self, message: Message) -> bool:
        return bool(message.text in GROUP_CHANGE_TUPLE)


class IsShedule(Filter):
    async def __call__(self, message: Message) -> bool:
        return bool(message.text in SHEDULE_TUPLE)


class IsToggleAlerts(Filter):
    async def __call__(self, message: Message) -> bool:
        return bool(message.text in ALERTS_TOGGLE_TUPLE)
