from sqlalchemy import Column, Integer, String, Text, Date, Boolean
from sqlalchemy.orm import relationship

from database.database import Base


class Lead(Base):
    __tablename__ = "leads"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Customer details
    customer_name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    customer_category = Column(String, nullable=True)
    language = Column(String, nullable=True)
    city = Column(String, nullable=True)

    # Lead qualification
    lead_potential = Column(String, nullable=True)
    next_follow_up_date = Column(Date, nullable=True)

    # Product details
    product = Column(String, nullable=True)
    product_category = Column(String, nullable=True)
    product_variant = Column(String, nullable=True)
    product_specification = Column(Text, nullable=True)

    # Customer requirement
    application = Column(Text, nullable=True)
    quantity = Column(String, nullable=True)
    unit = Column(String, nullable=True)

    required_length = Column(String, nullable=True)
    required_height = Column(String, nullable=True)
    required_thickness = Column(String, nullable=True)

    # Purchase details
    budget = Column(String, nullable=True)
    installation_required = Column(Boolean, nullable=True)

    # AI-generated information
    notes = Column(Text, nullable=True)
    ai_summary = Column(Text, nullable=True)

    # Related call records
    call_records = relationship(
        "CallRecord",
        back_populates="lead",
        cascade="all, delete-orphan"
    )