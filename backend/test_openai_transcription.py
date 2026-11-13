from pathlib import Path
import os

from dotenv import load_dotenv
from openai import OpenAI


# ---------------------------------------------------------
# Load project .env from the project root
# ---------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"

load_dotenv(ENV_FILE)


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------
AUDIO_FILE = Path(__file__).resolve().parent / "test_clean.wav"

API_KEY = os.getenv("OPENAI_TRANSCRIPTION_API_KEY")
BASE_URL = os.getenv("OPENAI_BASE_URL")


print("========================================")
print("OpenAI / Vocareum Transcription Test")
print("========================================")

print(f"Audio file : {AUDIO_FILE}")
print(f"Audio exists: {AUDIO_FILE.exists()}")
print(f"Base URL loaded: {bool(BASE_URL)}")
print(f"Transcription key loaded: {bool(API_KEY)}")

if not API_KEY:
    raise RuntimeError(
        "OPENAI_TRANSCRIPTION_API_KEY was not found in the project .env"
    )

if not BASE_URL:
    raise RuntimeError(
        "OPENAI_BASE_URL was not found in the project .env"
    )

if not AUDIO_FILE.exists():
    raise FileNotFoundError(
        f"Audio file not found: {AUDIO_FILE}"
    )


# ---------------------------------------------------------
# Create client using the EXISTING project configuration
# ---------------------------------------------------------
client = OpenAI(
    api_key=API_KEY,
    base_url=BASE_URL,
)


# ---------------------------------------------------------
# Transcribe
# ---------------------------------------------------------
print("\nSending audio for transcription...\n")

with open(AUDIO_FILE, "rb") as audio_file:

    transcript = client.audio.transcriptions.create(
        model="gpt-4o-transcribe",
        file=audio_file,
        language="ml",
    )


# ---------------------------------------------------------
# Result
# ---------------------------------------------------------
print("========================================")
print("TRANSCRIPTION RESULT")
print("========================================")

print(transcript.text)

print("\n========================================")
print("TEST COMPLETE")
print("========================================")
