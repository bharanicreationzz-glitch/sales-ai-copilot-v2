import os
import json
from pathlib import Path

import assemblyai as aai
from dotenv import load_dotenv


# --------------------------------------------------
# Load .env
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

API_KEY = os.getenv("ASSEMBLYAI_API_KEY")

if not API_KEY:
    raise RuntimeError("ASSEMBLYAI_API_KEY is missing from .env")


# --------------------------------------------------
# Audio file
# --------------------------------------------------

AUDIO_FILE = (
    Path(__file__).resolve().parent
    / "uploads"
    / "audio"
    / "lead_15_call_4.mp3"
)


if not AUDIO_FILE.exists():
    raise FileNotFoundError(
        f"Audio file not found: {AUDIO_FILE}"
    )


# --------------------------------------------------
# AssemblyAI configuration
# --------------------------------------------------

aai.settings.api_key = API_KEY

config = aai.TranscriptionConfig(
    speech_models=["universal-3-5-pro"],
    language_detection=True,
    speaker_labels=True,
)


# --------------------------------------------------
# Run transcription
# --------------------------------------------------

print("=" * 70)
print("ASSEMBLYAI TRANSCRIPTION TEST")
print("=" * 70)

print(f"Audio: {AUDIO_FILE.name}")
print(
    f"Size : "
    f"{AUDIO_FILE.stat().st_size / 1024 / 1024:.2f} MB"
)
print()

print("Submitting audio...")
print()


transcriber = aai.Transcriber(
    config=config
)

transcript = transcriber.transcribe(
    str(AUDIO_FILE)
)


# --------------------------------------------------
# Check status
# --------------------------------------------------

if transcript.status == aai.TranscriptStatus.error:
    print("TRANSCRIPTION ERROR")
    print("-" * 70)
    print(transcript.error)
    raise SystemExit(1)


# --------------------------------------------------
# Basic result
# --------------------------------------------------

print("STATUS")
print("-" * 70)
print(transcript.status)

print()

print("LANGUAGE")
print("-" * 70)
print(getattr(transcript, "language_code", None))

print()

print("CONFIDENCE")
print("-" * 70)
print(getattr(transcript, "confidence", None))

print()

print("TRANSCRIPT")
print("-" * 70)
print(transcript.text)

print()


# --------------------------------------------------
# Speaker-labelled transcript
# --------------------------------------------------

if transcript.utterances:

    print("SPEAKER UTTERANCES")
    print("-" * 70)

    for utterance in transcript.utterances:
        print(
            f"[{utterance.speaker}] "
            f"{utterance.text}"
        )

    print()


# --------------------------------------------------
# Save result
# --------------------------------------------------

output_file = (
    Path(__file__).resolve().parent
    / f"assemblyai_{AUDIO_FILE.stem}_result.json"
)


result = {
    "status": str(transcript.status),
    "language_code": getattr(
        transcript,
        "language_code",
        None,
    ),
    "confidence": getattr(
        transcript,
        "confidence",
        None,
    ),
    "text": transcript.text,
    "utterances": [
        {
            "speaker": u.speaker,
            "text": u.text,
            "start": u.start,
            "end": u.end,
            "confidence": getattr(
                u,
                "confidence",
                None,
            ),
        }
        for u in (transcript.utterances or [])
    ],
}


with open(
    output_file,
    "w",
    encoding="utf-8",
) as f:
    json.dump(
        result,
        f,
        ensure_ascii=False,
        indent=2,
    )


print("-" * 70)
print(f"Raw result saved to: {output_file}")
print("-" * 70)
