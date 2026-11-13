from database.database import SessionLocal

# Import BOTH models so SQLAlchemy can resolve relationships
from models.lead import Lead
from models.call_record import CallRecord


db = SessionLocal()

try:
    calls = (
        db.query(CallRecord)
        .order_by(
            CallRecord.lead_id,
            CallRecord.created_at,
            CallRecord.id
        )
        .all()
    )

    current_lead_id = None
    call_number = 0

    for call in calls:

        if call.lead_id != current_lead_id:
            current_lead_id = call.lead_id
            call_number = 1
        else:
            call_number += 1

        call.call_number = call_number

        print(
            f"Lead {call.lead_id} | "
            f"Call Record {call.id} | "
            f"Assigned Call #{call_number}"
        )

    db.commit()

    print("\nSUCCESS: All call numbers updated.")

except Exception as e:
    db.rollback()
    print(f"\nERROR: {e}")

finally:
    db.close()