from sqlalchemy import Column, Integer, String, Text, Date
from database.database import Base
from sqlalchemy.orm import relationship

class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)

    customer_name = Column(String, nullable=False)
    phone = Column(String, nullable=False)

    product = Column(String, nullable=True)
    customer_category = Column(String, nullable=True)
    language = Column(String, nullable=True)
    lead_potential = Column(String, nullable=True)

    quantity = Column(String, nullable=True)
    city = Column(String, nullable=True)

    next_follow_up_date = Column(Date, nullable=True)

    notes = Column(Text, nullable=True)
    ai_summary = Column(Text, nullable=True)
    call_records = relationship(
    "CallRecord",
    back_populates="lead",
    cascade="all, delete-orphan"
)