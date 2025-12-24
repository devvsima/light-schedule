from aiogram.filters import Filter
from aiogram.types import Message

GROUP_CHANGE_TUPLE = (
    "/group",
    "Указать группу",
    "🔄 Поменять группу",
)
SHEDULE_TUPLE = (
    "/schedule",
    "🗓 Расписание",
)
ALERTS_TOGGLE_TUPLE = (
    "/alerts",
    "🔔 Уведомления",
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
