from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.database import SessionLocal
from models.lead import Lead
from schemas.lead import LeadCreate, LeadResponse


router = APIRouter(
    prefix="/leads",
    tags=["Leads"]
)


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


@router.post("/", response_model=LeadResponse)
def create_lead(
    lead: LeadCreate,
    db: Session = Depends(get_db)
):
    new_lead = Lead(
        customer_name=lead.customer_name,
        phone=lead.phone,
        product=lead.product,
        product_category=lead.product_category,
        product_variant=lead.product_variant,
        product_specification=lead.product_specification,
        application=lead.application,
        customer_category=lead.customer_category,
        language=lead.language,
        lead_potential=lead.lead_potential,
        quantity=lead.quantity,
        unit=lead.unit,
        required_length=lead.required_length,
        required_height=lead.required_height,
        required_thickness=lead.required_thickness,
        budget=lead.budget,
        installation_required=lead.installation_required,
        city=lead.city,
        next_follow_up_date=lead.next_follow_up_date,
        notes=lead.notes,
        ai_summary=lead.ai_summary,
    )

    db.add(new_lead)
    db.commit()
    db.refresh(new_lead)

    return new_lead


@router.get("/", response_model=list[LeadResponse])
def get_leads(
    db: Session = Depends(get_db)
):
    leads = db.query(Lead).all()
    return leads


@router.get("/{lead_id}", response_model=LeadResponse)
def get_lead(
    lead_id: int,
    db: Session = Depends(get_db)
):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()

    if not lead:
        raise HTTPException(
            status_code=404,
            detail="Lead not found"
        )

    return lead


@router.put("/{lead_id}", response_model=LeadResponse)
def update_lead(
    lead_id: int,
    lead_data: LeadCreate,
    db: Session = Depends(get_db)
):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()

    if not lead:
        raise HTTPException(
            status_code=404,
            detail="Lead not found"
        )

    lead.customer_name = lead_data.customer_name
    lead.phone = lead_data.phone
    lead.product = lead_data.product
    lead.product_category = lead_data.product_category
    lead.product_variant = lead_data.product_variant
    lead.product_specification = lead_data.product_specification
    lead.application = lead_data.application
    lead.customer_category = lead_data.customer_category
    lead.language = lead_data.language
    lead.lead_potential = lead_data.lead_potential
    lead.quantity = lead_data.quantity
    lead.unit = lead_data.unit
    lead.required_length = lead_data.required_length
    lead.required_height = lead_data.required_height
    lead.required_thickness = lead_data.required_thickness
    lead.budget = lead_data.budget
    lead.installation_required = lead_data.installation_required
    lead.city = lead_data.city
    lead.next_follow_up_date = lead_data.next_follow_up_date
    lead.notes = lead_data.notes
    lead.ai_summary = lead_data.ai_summary

    db.commit()
    db.refresh(lead)

    return lead