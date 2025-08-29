import uuid
from datetime import date
from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Date, Numeric, ForeignKey
from app.db.base import Base

class PayRate(Base):
    __tablename__ = "pay_rates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    employee_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date:   Mapped[date | None] = mapped_column(Date, nullable=True)  
    hourly_rate: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
