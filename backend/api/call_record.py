from pathlib import Path
from services.ai_extraction import extract_crm_fields
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from sqlalchemy.orm import Session

from database.database import SessionLocal
from models.lead import Lead
from models.call_record import CallRecord
from services.transcription import transcribe_audio


router = APIRouter(
    prefix="/leads",
    tags=["Call Records"]
)


UPLOAD_DIR = Path("uploads/audio")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


@router.post("/{lead_id}/calls")
async def upload_call_recording(
    lead_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()

    if not lead:
        raise HTTPException(
            status_code=404,
            detail="Lead not found"
        )

    file_extension = Path(file.filename).suffix
    file_name = f"lead_{lead_id}_call_{file.filename}"

    file_path = UPLOAD_DIR / file_name

    file_content = await file.read()

    with open(file_path, "wb") as buffer:
        buffer.write(file_content)

    call_record = CallRecord(
        lead_id=lead_id,
        recording_path=str(file_path)
    )

    db.add(call_record)
    db.commit()
    db.refresh(call_record)

    return {
        "message": "Call recording uploaded successfully",
        "call_record_id": call_record.id,
        "lead_id": lead_id,
        "recording_path": str(file_path)
    }
@router.post("/calls/{call_id}/transcribe")
def transcribe_call(
    call_id: int,
    db: Session = Depends(get_db)
):
    call_record = (
        db.query(CallRecord)
        .filter(CallRecord.id == call_id)
        .first()
    )

    if not call_record:
        raise HTTPException(
            status_code=404,
            detail="Call record not found"
        )

    if not call_record.recording_path:
        raise HTTPException(
            status_code=400,
            detail="No recording found for this call"
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
        "transcript": transcript
    }
@router.post("/calls/{call_id}/analyze")
def analyze_call(
    call_id: int,
    db: Session = Depends(get_db)
):
    # Find the call record
    call_record = (
        db.query(CallRecord)
        .filter(CallRecord.id == call_id)
        .first()
    )

    if not call_record:
        raise HTTPException(
            status_code=404,
            detail="Call record not found"
        )

    # Make sure a transcript exists
    if not call_record.transcript:
        raise HTTPException(
            status_code=400,
            detail="No transcript found for this call"
        )

    # Find the lead connected to this call
    lead = (
        db.query(Lead)
        .filter(Lead.id == call_record.lead_id)
        .first()
    )

    if not lead:
        raise HTTPException(
            status_code=404,
            detail="Lead not found"
        )

    # Send transcript to AI
    ai_data = extract_crm_fields(
        call_record.transcript
    )

    # Update Lead fields
    lead.customer_name = ai_data.get(
        "customer_name", lead.customer_name
    )

    lead.phone = ai_data.get(
        "phone", lead.phone
    )

    lead.product = ai_data.get(
        "product", "NA"
    )

    lead.customer_category = ai_data.get(
        "customer_category", "NA"
    )

    lead.language = ai_data.get(
        "language", "NA"
    )

    lead.lead_potential = ai_data.get(
        "lead_potential", "NA"
    )

    lead.quantity = ai_data.get(
        "quantity", "NA"
    )

    lead.city = ai_data.get(
        "city", "NA"
    )

    lead.notes = ai_data.get(
        "notes", "NA"
    )

    lead.ai_summary = ai_data.get(
        "ai_summary", "NA"
    )

    # Save AI summary to the individual call as well
    call_record.ai_summary = ai_data.get(
        "ai_summary", "NA"
    )

    db.commit()
    db.refresh(lead)
    db.refresh(call_record)

    return {
        "message": "Call analyzed successfully",
        "call_record_id": call_record.id,
        "lead_id": lead.id,
        "ai_data": ai_data
    }