from fastapi import APIRouter, Depends
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
        customer_category=lead.customer_category,
        language=lead.language,
        lead_potential=lead.lead_potential,
        quantity=lead.quantity,
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
        return {"error": "Lead not found"}

    return lead
@router.put("/{lead_id}", response_model=LeadResponse)
def update_lead(
    lead_id: int,
    lead_data: LeadCreate,
    db: Session = Depends(get_db)
):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()

    if not lead:
        return {"error": "Lead not found"}

    lead.customer_name = lead_data.customer_name
    lead.product = lead_data.product
    lead.customer_category = lead_data.customer_category
    lead.language = lead_data.language
    lead.lead_potential = lead_data.lead_potential
    lead.quantity = lead_data.quantity
    lead.city = lead_data.city
    lead.next_follow_up_date = lead_data.next_follow_up_date
    lead.notes = lead_data.notes
    lead.ai_summary = lead_data.ai_summary

    db.commit()
    db.refresh(lead)

    return lead