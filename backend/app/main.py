from fastapi import FastAPI
from api.lead import router as lead_router
from database.database import Base, engine
from models.lead import Lead
from models.call_record import CallRecord
from api.call_record import router as call_record_router
from fastapi.middleware.cors import CORSMiddleware


# Create database tables
Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="Sales AI Copilot",
    description="AI-powered CRM assistant for sales conversations",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(lead_router)
app.include_router(call_record_router)

@app.get("/")
def home():
    return {
        "message": "Sales AI Copilot is running!"
    }