import json
from datetime import date, datetime
from pathlib import Path
from fastapi import (
    APIRouter,
    Depends,
    File,
    UploadFile,
    HTTPException,
)
from sqlalchemy.orm import Session

from database.database import SessionLocal
from models.lead import Lead
from models.call_record import CallRecord

from services.transcription import transcribe_audio
from services.ai_extraction import extract_crm_fields
from services.conversation_rating import rate_conversation
from services.sales_coach import coach_sales_conversation
from config import UPLOAD_DIR as BASE_UPLOAD_DIR


router = APIRouter(
    prefix="/leads",
    tags=["Call Records"],
)


UPLOAD_DIR = BASE_UPLOAD_DIR / "audio"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# =====================================================
# DATABASE
# =====================================================

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =====================================================
# HELPERS
# =====================================================

INVALID_VALUES = {
    "",
    "NA",
    "N/A",
    "NULL",
    "NONE",
    "UNKNOWN",
}


def is_valid_value(value):
    if value is None:
        return False

    if not isinstance(value, str):
        return True

    return value.strip().upper() not in INVALID_VALUES


def clean_value(value):
    if not is_valid_value(value):
        return None

    if isinstance(value, str):
        return value.strip()

    return value


# =====================================================
# SIMPLE FIELD MERGE
# =====================================================

def merge_simple_field(existing, new_value):
    existing = clean_value(existing)
    new_value = clean_value(new_value)

    # Never overwrite useful existing information
    # with NA/empty values.
    if existing and new_value:
        return existing

    if new_value:
        return new_value

    if existing:
        return existing

    return "NA"


# =====================================================
# CUSTOMER CATEGORY
# =====================================================

def merge_category(existing, new_value):
    valid_categories = {
        "B2B",
        "B2C",
        "DEALER",
    }

    existing = clean_value(existing)
    new_value = clean_value(new_value)

    if new_value:
        normalized = new_value.upper()

        if normalized in valid_categories:
            return normalized

    if existing:
        normalized = existing.upper()

        if normalized in valid_categories:
            return normalized

    return "NA"


# =====================================================
# LEAD POTENTIAL
# =====================================================

def merge_lead_potential(existing, new_value):
    priority = {
        "NA": 0,
        "COLD": 1,
        "WARM": 2,
        "HOT": 3,
    }

    existing_clean = clean_value(existing)
    new_clean = clean_value(new_value)

    existing_normalized = (
        existing_clean.upper()
        if existing_clean
        else "NA"
    )

    new_normalized = (
        new_clean.upper()
        if new_clean
        else "NA"
    )

    existing_score = priority.get(
        existing_normalized,
        0,
    )

    new_score = priority.get(
        new_normalized,
        0,
    )

    if new_score >= existing_score:
        return new_normalized.title()

    return existing_normalized.title()


# =====================================================
# LIST MERGE
# =====================================================

def split_values(value):
    if not is_valid_value(value):
        return []

    values = []

    for item in str(value).split(","):
        cleaned = item.strip()

        if (
            cleaned
            and cleaned.upper() not in INVALID_VALUES
        ):
            values.append(cleaned)

    return values


# =====================================================
# PRODUCT NORMALIZATION
#
# Fiber Mesh = Polyhex Mesh
# =====================================================

PRODUCT_ALIASES = {
    "fiber mesh": "Polyhex Mesh",
    "fibre mesh": "Polyhex Mesh",
    "fiber": "Polyhex Mesh",
    "fibre": "Polyhex Mesh",
    "polyhex": "Polyhex Mesh",
    "polyhex mesh": "Polyhex Mesh",

    "checks mesh": "Checks Mesh",
    "check mesh": "Checks Mesh",

    "trinity pole": "Trinity Fence Pole",
    "trinity poles": "Trinity Fence Pole",
    "trinity fence pole": "Trinity Fence Pole",

    "lato": "Lato Fence",
    "lato fence": "Lato Fence",

    "privezy": "Privezy Wall",
    "privezy wall": "Privezy Wall",

    "plant wire": "Plant Wire",
}


def normalize_product(value):
    if not is_valid_value(value):
        return None

    value = str(value).strip()

    key = value.lower()

    return PRODUCT_ALIASES.get(
        key,
        value,
    )


def merge_product(existing, new_value):
    existing_values = split_values(existing)
    new_values = split_values(new_value)

    merged = []

    for value in existing_values + new_values:

        normalized = normalize_product(value)

        if not normalized:
            continue

        already_exists = any(
            item.lower() == normalized.lower()
            for item in merged
        )

        if not already_exists:
            merged.append(normalized)

    if not merged:
        return "NA"

    return ", ".join(merged)


def merge_list_field(existing, new_value):
    existing_values = split_values(existing)
    new_values = split_values(new_value)

    merged = []

    for value in existing_values + new_values:

        already_exists = any(
            item.lower() == value.lower()
            for item in merged
        )

        if not already_exists:
            merged.append(value)

    if not merged:
        return "NA"

    return ", ".join(merged)


# =====================================================
# NOTES
# =====================================================

def merge_notes(existing, new_value):
    existing = clean_value(existing)
    new_value = clean_value(new_value)

    if not existing and not new_value:
        return "NA"

    if existing and not new_value:
        return existing

    if new_value and not existing:
        return new_value

    if new_value.lower() in existing.lower():
        return existing

    if existing.lower() in new_value.lower():
        return new_value

    return f"{existing} | {new_value}"


# =====================================================
# AI SUMMARY
# =====================================================

def merge_ai_summary(existing, new_value):
    existing = clean_value(existing)
    new_value = clean_value(new_value)

    if new_value:
        return new_value

    if existing:
        return existing

    return "NA"


# =====================================================
# FOLLOW-UP DATE
#
# AI extraction already maps:
#
# Hot  -> next day
# Warm -> approximately 10 days
# Cold -> approximately 18 days
#
# Therefore we use the AI-generated date if valid.
# =====================================================

def merge_follow_up_date(existing, new_value):
    """Return a Python date object suitable for the SQLAlchemy Date column."""

    if new_value:
        try:
            if isinstance(new_value, datetime):
                return new_value.date()

            if isinstance(new_value, date):
                return new_value

            if isinstance(new_value, str):
                cleaned = new_value.strip()

                if cleaned:
                    return date.fromisoformat(cleaned)

        except (ValueError, TypeError):
            # Invalid AI-generated date: preserve the existing value.
            pass

    return existing

# =====================================================
# RATING STORAGE
# =====================================================

def load_saved_rating(call_record):
    try:
        if not call_record.ai_notes:
            return None

        parsed = json.loads(call_record.ai_notes)

        if not isinstance(parsed, dict):
            return None

        return parsed

    except Exception:
        return None


def save_rating(call_record, rating):
    call_record.ai_notes = json.dumps(
        rating,
        ensure_ascii=False,
    )


# =====================================================
# UPLOAD CALL RECORDING
# =====================================================

@router.post("/{lead_id}/calls")
async def upload_call_recording(
    lead_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    lead = (
        db.query(Lead)
        .filter(Lead.id == lead_id)
        .first()
    )

    if not lead:
        raise HTTPException(
            status_code=404,
            detail="Lead not found",
        )

    existing_call_count = (
        db.query(CallRecord)
        .filter(CallRecord.lead_id == lead_id)
        .count()
    )

    next_call_number = existing_call_count + 1

    file_extension = Path(
        file.filename
    ).suffix

    file_name = (
        f"lead_{lead_id}_call_"
        f"{next_call_number}"
        f"{file_extension}"
    )

    file_path = UPLOAD_DIR / file_name

    file_content = await file.read()

    with open(file_path, "wb") as buffer:
        buffer.write(file_content)

    call_record = CallRecord(
        lead_id=lead_id,
        call_number=next_call_number,
        recording_path=str(file_path),
    )

    db.add(call_record)
    db.commit()
    db.refresh(call_record)

    return {
        "message": "Call recording uploaded successfully",
        "call_record_id": call_record.id,
        "lead_id": lead_id,
        "call_number": next_call_number,
        "recording_path": str(file_path),
    }


# =====================================================
# GET ALL CALLS FOR A LEAD
# =====================================================

@router.get("/{lead_id}/calls")
def get_lead_calls(
    lead_id: int,
    db: Session = Depends(get_db),
):
    lead = (
        db.query(Lead)
        .filter(Lead.id == lead_id)
        .first()
    )

    if not lead:
        raise HTTPException(
            status_code=404,
            detail="Lead not found",
        )

    calls = (
        db.query(CallRecord)
        .filter(CallRecord.lead_id == lead_id)
        .order_by(CallRecord.call_number.asc())
        .all()
    )

    result = []

    for call in calls:

        if call.ai_summary:
            status = "Analyzed"
        elif call.transcript:
            status = "Transcribed"
        else:
            status = "Uploaded"

        rating = load_saved_rating(call)

        result.append({
            "id": call.id,
            "call_number": call.call_number,
            "recording_path": call.recording_path,
            "has_transcript": bool(call.transcript),
            "transcript": call.transcript,
            "ai_summary": call.ai_summary,
            "status": status,
            "conversation_rating": rating,
        })

    return result


# =====================================================
# TRANSCRIBE CALL
# =====================================================

@router.post("/calls/{call_id}/transcribe")
def transcribe_call(
    call_id: int,
    db: Session = Depends(get_db),
):
    call_record = (
        db.query(CallRecord)
        .filter(CallRecord.id == call_id)
        .first()
    )

    if not call_record:
        raise HTTPException(
            status_code=404,
            detail="Call record not found",
        )

    if not call_record.recording_path:
        raise HTTPException(
            status_code=400,
            detail="No recording found for this call",
        )

    transcript = transcribe_audio(
        call_record.recording_path
    )

    call_record.transcript = transcript

    db.commit()
    db.refresh(call_record)

    return {
        "message": "Call transcribed successfully",
        "call_record_id": call_record.id,
        "transcript": transcript,
    }


# =====================================================
# ANALYZE CALL
# CRM MERGE + RATING
# =====================================================

@router.post("/calls/{call_id}/analyze")
def analyze_call(
    call_id: int,
    db: Session = Depends(get_db),
):
    call_record = (
        db.query(CallRecord)
        .filter(CallRecord.id == call_id)
        .first()
    )

    if not call_record:
        raise HTTPException(
            status_code=404,
            detail="Call record not found",
        )

    if not call_record.transcript:
        raise HTTPException(
            status_code=400,
            detail="No transcript found for this call",
        )

    lead = (
        db.query(Lead)
        .filter(
            Lead.id == call_record.lead_id
        )
        .first()
    )

    if not lead:
        raise HTTPException(
            status_code=404,
            detail="Lead not found",
        )

    # ---------------------------------------------
    # STEP 1 — AI EXTRACTION
    # ---------------------------------------------

    ai_data = extract_crm_fields(
        call_record.transcript
    )

    # ---------------------------------------------
    # STEP 2 — SMART CRM MERGE
    # ---------------------------------------------

    lead.customer_name = merge_simple_field(
        lead.customer_name,
        ai_data.get("customer_name"),
    )

    lead.phone = merge_simple_field(
        lead.phone,
        ai_data.get("phone"),
    )

    lead.product = merge_product(
        lead.product,
        ai_data.get("product"),
    )

        # Product knowledge fields
    lead.product_category = merge_simple_field(
        lead.product_category,
        ai_data.get("product_category"),
    )

    lead.product_variant = merge_simple_field(
        lead.product_variant,
        ai_data.get("product_variant"),
    )

    lead.product_specification = merge_simple_field(
        lead.product_specification,
        ai_data.get("product_specification"),
    )

    lead.application = merge_simple_field(
        lead.application,
        ai_data.get("application"),
    )

    lead.unit = merge_simple_field(
        lead.unit,
        ai_data.get("unit"),
    )

    lead.required_length = merge_simple_field(
        lead.required_length,
        ai_data.get("required_length"),
    )

    lead.required_height = merge_simple_field(
        lead.required_height,
        ai_data.get("required_height"),
    )

    lead.required_thickness = merge_simple_field(
        lead.required_thickness,
        ai_data.get("required_thickness"),
    )

    lead.budget = merge_simple_field(
        lead.budget,
        ai_data.get("budget"),
    )

    installation_required = clean_value(
        ai_data.get("installation_required")
    )

    if installation_required is not None:
        if isinstance(installation_required, bool):
            lead.installation_required = installation_required
        elif str(installation_required).strip().lower() in {"true", "yes"}:
            lead.installation_required = True
        elif str(installation_required).strip().lower() in {"false", "no"}:
            lead.installation_required = False
    lead.customer_category = merge_category(
        lead.customer_category,
        ai_data.get("customer_category"),
    )

    lead.language = merge_simple_field(
        lead.language,
        ai_data.get("language"),
    )

    lead.lead_potential = merge_lead_potential(
        lead.lead_potential,
        ai_data.get("lead_potential"),
    )

    lead.quantity = merge_list_field(
        lead.quantity,
        ai_data.get("quantity"),
    )

    lead.city = merge_simple_field(
        lead.city,
        ai_data.get("city"),
    )

    lead.next_follow_up_date = merge_follow_up_date(
        lead.next_follow_up_date,
        ai_data.get("next_follow_up_date"),
    )

    lead.notes = merge_notes(
        lead.notes,
        ai_data.get("notes"),
    )

    lead.ai_summary = merge_ai_summary(
        lead.ai_summary,
        ai_data.get("ai_summary"),
    )

    # Individual call summary
    call_record.ai_summary = ai_data.get(
        "ai_summary",
        "NA",
    )

    # ---------------------------------------------
    # STEP 3 — CONVERSATION RATING
    # ---------------------------------------------

    conversation_rating = None
    conversation_rating_error = None

    try:
        conversation_rating = rate_conversation(
            call_record.transcript,
            max_rag_results=10,
        )

        save_rating(
            call_record,
            conversation_rating,
        )

    except Exception as error:
        conversation_rating_error = str(error)

    # ---------------------------------------------
    # SAVE
    # ---------------------------------------------

    db.commit()

    db.refresh(lead)
    db.refresh(call_record)

    return {
        "message": "Call analyzed and merged successfully",
        "call_record_id": call_record.id,
        "lead_id": lead.id,
        "call_number": call_record.call_number,
        "ai_data": ai_data,
        "conversation_rating": conversation_rating,
        "conversation_rating_error": conversation_rating_error,
        "merged_lead":         {
            "customer_name": lead.customer_name,
            "phone": lead.phone,
            "product": lead.product,
            "product_category": lead.product_category,
            "product_variant": lead.product_variant,
            "product_specification": lead.product_specification,
            "application": lead.application,
            "customer_category": lead.customer_category,
            "language": lead.language,
            "lead_potential": lead.lead_potential,
            "quantity": lead.quantity,
            "unit": lead.unit,
            "required_length": lead.required_length,
            "required_height": lead.required_height,
            "required_thickness": lead.required_thickness,
            "budget": lead.budget,
            "installation_required": lead.installation_required,
            "city": lead.city,
            "next_follow_up_date": (
                str(lead.next_follow_up_date)
                if lead.next_follow_up_date
                else None
            ),
            "notes": lead.notes,
            "ai_summary": lead.ai_summary,
        },
    }


# =====================================================
# AI SALES COACH
# COMPLETE CUSTOMER JOURNEY
# =====================================================

@router.post("/{lead_id}/sales-coach")
def generate_sales_coach(
    lead_id: int,
    db: Session = Depends(get_db),
):
    # ---------------------------------------------
    # FIND LEAD
    # ---------------------------------------------

    lead = (
        db.query(Lead)
        .filter(Lead.id == lead_id)
        .first()
    )

    if not lead:
        raise HTTPException(
            status_code=404,
            detail="Lead not found",
        )

    # ---------------------------------------------
    # GET COMPLETE CALL HISTORY
    # ---------------------------------------------

    calls = (
        db.query(CallRecord)
        .filter(
            CallRecord.lead_id == lead_id
        )
        .order_by(
            CallRecord.call_number.asc()
        )
        .all()
    )

    if not calls:
        raise HTTPException(
            status_code=400,
            detail="No call history available for this lead",
        )

    # ---------------------------------------------
    # ONLY CALLS WITH TRANSCRIPTS
    # ---------------------------------------------

    usable_calls = [
        call
        for call in calls
        if call.transcript
    ]

    if not usable_calls:
        raise HTTPException(
            status_code=400,
            detail="No transcribed calls available for this lead",
        )

    # ---------------------------------------------
    # GENERATE COACHING
    # ---------------------------------------------

    try:
        coaching = coach_sales_conversation(
            lead=lead,
            calls=usable_calls,
            max_rag_results=10,
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=(
                "Sales coaching generation failed: "
                f"{str(error)}"
            ),
        )

    latest_call = usable_calls[-1]

    return {
        "message": "AI Sales Coach generated successfully",
        "lead_id": lead.id,
        "calls_considered": len(usable_calls),
        "latest_call_number": latest_call.call_number,
        "sales_coach": coaching,
    }