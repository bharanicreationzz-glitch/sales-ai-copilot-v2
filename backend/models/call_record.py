from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from database.database import Base


class CallRecord(Base):
    __tablename__ = "call_records"

    id = Column(Integer, primary_key=True, index=True)

    lead_id = Column(
        Integer,
        ForeignKey("leads.id"),
        nullable=False
    )

    # Call sequence for each lead
    call_number = Column(
        Integer,
        nullable=True
    )

    recording_path = Column(
        String,
        nullable=True
    )

    transcript = Column(
        Text,
        nullable=True
    )

    ai_summary = Column(
        Text,
        nullable=True
    )

    ai_notes = Column(
        Text,
        nullable=True
    )

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc)
    )

    lead = relationship(
        "Lead",
        back_populates="call_records"
    )