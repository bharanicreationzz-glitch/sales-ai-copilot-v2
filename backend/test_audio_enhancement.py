from pathlib import Path
import subprocess


INPUT_FILE = Path(__file__).resolve().parent / "test_clean.wav"
OUTPUT_FILE = Path(__file__).resolve().parent / "enhanced_test.wav"


if not INPUT_FILE.exists():
    raise FileNotFoundError(f"Input file not found: {INPUT_FILE}")


print("========================================")
print("Audio Enhancement Test")
print("========================================")
print(f"Input : {INPUT_FILE}")
print(f"Output: {OUTPUT_FILE}")
print()


command = [
    "ffmpeg",
    "-y",
    "-i",
    str(INPUT_FILE),

    # Speech-focused filtering
    "-af",
    "highpass=f=100,lowpass=f=7500,dynaudnorm=f=150:g=15",

    # Standard Whisper-friendly format
    "-ac", "1",
    "-ar", "16000",
    "-sample_fmt", "s16",
    "-c:a", "pcm_s16le",

    str(OUTPUT_FILE),
]


print("Enhancing audio...")
print()

subprocess.run(
    command,
    check=True,
)

print()
print("========================================")
print("ENHANCEMENT COMPLETE")
print("========================================")
print(f"Created: {OUTPUT_FILE}")
