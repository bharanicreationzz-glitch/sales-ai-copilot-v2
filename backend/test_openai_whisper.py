from pathlib import Path
import whisper


# ============================================================
# CONFIGURATION
# ============================================================

AUDIO_FILE = Path(__file__).resolve().parent / "test_clean.wav"

MODEL_NAME = "large-v3"
LANGUAGE = "ml"


# ============================================================
# CHECK AUDIO
# ============================================================

if not AUDIO_FILE.exists():
    raise FileNotFoundError(
        f"Audio file not found: {AUDIO_FILE}"
    )

print("========================================")
print("OpenAI Whisper Local A/B Test")
print("========================================")
print(f"Audio file : {AUDIO_FILE}")
print(f"Model      : {MODEL_NAME}")
print(f"Language   : {LANGUAGE}")
print()


# ============================================================
# LOAD MODEL
# ============================================================

print("Loading Whisper model...")

model = whisper.load_model(MODEL_NAME)

print("Whisper model loaded successfully!")
print()


# ============================================================
# TRANSCRIBE
# ============================================================

print("Starting transcription...")
print("Please wait...")
print()

result = model.transcribe(
    str(AUDIO_FILE),
    language=LANGUAGE,
    temperature=0,
    condition_on_previous_text=False,
    fp16=False,
)


# ============================================================
# RESULT
# ============================================================

print()
print("========================================")
print("TRANSCRIPTION RESULT")
print("========================================")

print(result["text"].strip())

print()
print("========================================")
print("TEST COMPLETE")
print("========================================")