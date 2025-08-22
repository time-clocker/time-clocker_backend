import uuid
from datetime import date
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Date, Float
from app.db.base import Base

class PayRule(Base):
    __tablename__ = "pay_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)  # inclusive

    daily_overtime_threshold_hours: Mapped[float] = mapped_column(Float, default=8.0)
    overtime_multiplier: Mapped[float] = mapped_column(Float, default=1.5)
