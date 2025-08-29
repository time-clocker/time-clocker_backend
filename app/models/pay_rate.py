# app/models/pay_rate.py
import uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Date, Numeric, ForeignKey
from app.db.base import Base

class PayRate(Base):
    __tablename__ = "pay_rates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # NULL = tarifa global; si tiene valor, es específica del empleado
    employee_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Vigencia INCLUSIVA
    start_date: Mapped[Date] = mapped_column(Date, nullable=False)
    end_date:   Mapped[Date] = mapped_column(Date, nullable=False)

    # Tarifa base
    hourly_rate: Mapped[Numeric] = mapped_column(Numeric(10, 2), nullable=False)
