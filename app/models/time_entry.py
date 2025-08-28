import uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import ForeignKey, DateTime, String, func
from app.db.base import Base

class TimeEntry(Base):
    __tablename__ = "time_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE"), index=True)
    clock_in: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    clock_out: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    tz: Mapped[str] = mapped_column(String(64), default="America/Bogota")

    employee = relationship("Employee", back_populates="time_entries")
