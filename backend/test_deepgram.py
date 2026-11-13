import os
from pathlib import Path

import requests
from dotenv import load_dotenv


# Load project .env
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

API_KEY = os.getenv("DEEPGRAM_API_KEY")

if not API_KEY:
    raise RuntimeError("DEEPGRAM_API_KEY is missing from .env")


AUDIO_FILE = (
    Path(__file__).resolve().parent
    / "uploads"
    / "audio"
    / "lead_17_call_1_enhanced.wav"
)


if not AUDIO_FILE.exists():
    raise FileNotFoundError(f"Audio file not found: {AUDIO_FILE}")


url = (
    "https://api.deepgram.com/v1/listen"
    "?model=nova-3"
    "&smart_format=true"
    "&detect_language=true"
    "&utterances=true"
)


headers = {
    "Authorization": f"Token {API_KEY}",
    "Content-Type": "audio/wav",
}


print("=" * 70)
print("DEEPGRAM TRANSCRIPTION TEST")
print("=" * 70)
print(f"Audio: {AUDIO_FILE.name}")
print(f"Size : {AUDIO_FILE.stat().st_size / 1024 / 1024:.2f} MB")
print()


with open(AUDIO_FILE, "rb") as audio:
    response = requests.post(
        url,
        headers=headers,
        data=audio,
        timeout=300,
    )


print(f"HTTP status: {response.status_code}")
print()


if not response.ok:
    print("ERROR:")
    print(response.text)
    raise SystemExit(1)


data = response.json()


# Save raw response for inspection
output_file = (
    Path(__file__).resolve().parent
    / f"deepgram_{AUDIO_FILE.stem}_result.json"
)

import json

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)


channel = data["results"]["channels"][0]
alternative = channel["alternatives"][0]

transcript = alternative.get("transcript", "")
confidence = alternative.get("confidence")

print("LANGUAGE / TRANSCRIPT")
print("-" * 70)

languages = alternative.get("languages", [])
print("Languages:", languages)

print("Confidence:", confidence)

print()
print("TRANSCRIPT")
print("-" * 70)
print(transcript)

print()
print("-" * 70)
print(f"Raw response saved to: {output_file}")
print("-" * 70)