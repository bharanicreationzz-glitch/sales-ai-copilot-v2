from datetime import date
from typing import Optional, Literal

from pydantic import BaseModel


Product = Literal[
    "Polyhex",
    "Checks Mesh",
    "Trinity Fence Pole",
    "Lato Fence",
    "Privezy Wall",
    "Plant Wire",
]

CustomerCategory = Literal[
    "B2B",
    "B2C",
    "Dealer",
]

Language = Literal[
    "English",
    "Tamil",
    "Telugu",
    "Kannada",
    "Malayalam",
    "Hindi",
]

LeadPotential = Literal[
    "Hot",
    "Warm",
    "Cold",
]


class LeadCreate(BaseModel):
    customer_name: str
    phone: str

    product: Optional[Product] = None
    customer_category: Optional[CustomerCategory] = None
    language: Optional[Language] = None
    lead_potential: Optional[LeadPotential] = None

    quantity: Optional[str] = None
    city: Optional[str] = None

    next_follow_up_date: Optional[date] = None

    notes: Optional[str] = None
    ai_summary: Optional[str] = None


class LeadResponse(BaseModel):
    id: int

    customer_name: str
    phone: str

    product: Optional[str] = None
    customer_category: Optional[str] = None
    language: Optional[str] = None
    lead_potential: Optional[str] = None

    quantity: Optional[str] = None
    city: Optional[str] = None

    next_follow_up_date: Optional[date] = None

    notes: Optional[str] = None
    ai_summary: Optional[str] = None

    model_config = {
        "from_attributes": True
    }