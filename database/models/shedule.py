from sqlalchemy import BigInteger, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseModel


class SheduleModel(BaseModel):
    __tablename__ = "shedules"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    text: Mapped[str] = mapped_column(String(1000), nullable=False)
    group: Mapped[float] = mapped_column(Float, nullable=False)
