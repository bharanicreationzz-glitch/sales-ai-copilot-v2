from datetime import date
from typing import Optional, Literal

from pydantic import BaseModel


# --------------------------------------------------
# PRODUCT CATALOG
# --------------------------------------------------

Product = Literal[
    # Agriculture
    "Polyhex",
    "Checks Mesh",
    "Trinity Fence Pole",
    "FRP Rod",
    "PET Wire",
    "Shade Net",

    # Decor
    "Lato Fence",
    "Indian Trellis",
    "American Trellis",
    "Australian Trellis",
    "Semi Trellis",
    "Privezy Wall",
    "Antiqo Fence",

    # Security
    "Razor Wire",
    "Concertina Coil",

    # Existing product value — retained for compatibility
    "Plant Wire",
]


ProductCategory = Literal[
    "Agriculture",
    "Decor",
    "Security",
    "Other",
]


# --------------------------------------------------
# CUSTOMER DETAILS
# --------------------------------------------------

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


# --------------------------------------------------
# CREATE LEAD
# --------------------------------------------------

class LeadCreate(BaseModel):
    customer_name: str
    phone: str

    # Core CRM fields
    product: Optional[Product] = None
    customer_category: Optional[CustomerCategory] = None
    language: Optional[Language] = None
    lead_potential: Optional[LeadPotential] = None

    quantity: Optional[str] = None
    city: Optional[str] = None

    next_follow_up_date: Optional[date] = None

    notes: Optional[str] = None
    ai_summary: Optional[str] = None

    # Product qualification fields
    product_category: Optional[ProductCategory] = None
    product_variant: Optional[str] = None
    product_specification: Optional[str] = None

    # Customer requirement
    application: Optional[str] = None
    required_length: Optional[str] = None
    required_height: Optional[str] = None
    required_thickness: Optional[str] = None

    # Purchase details
    unit: Optional[str] = None
    budget: Optional[str] = None
    installation_required: Optional[bool] = None


# --------------------------------------------------
# LEAD RESPONSE
# --------------------------------------------------

class LeadResponse(BaseModel):
    id: int

    customer_name: str
    phone: str

    # Core CRM fields
    product: Optional[str] = None
    customer_category: Optional[str] = None
    language: Optional[str] = None
    lead_potential: Optional[str] = None

    quantity: Optional[str] = None
    city: Optional[str] = None

    next_follow_up_date: Optional[date] = None

    notes: Optional[str] = None
    ai_summary: Optional[str] = None

    # Product qualification fields
    product_category: Optional[str] = None
    product_variant: Optional[str] = None
    product_specification: Optional[str] = None

    # Customer requirement
    application: Optional[str] = None
    required_length: Optional[str] = None
    required_height: Optional[str] = None
    required_thickness: Optional[str] = None

    # Purchase details
    unit: Optional[str] = None
    budget: Optional[str] = None
    installation_required: Optional[bool] = None

    model_config = {
        "from_attributes": True
    }