from faster_whisper import WhisperModel
import sys
from pathlib import Path

print("Starting Whisper transcription test...")

if len(sys.argv) < 2:
    print("Usage: python test_whisper.py <audio_file>")
    sys.exit(1)

audio_path = Path(sys.argv[1])

if not audio_path.exists():
    print(f"ERROR: File not found: {audio_path}")
    sys.exit(1)

print(f"Audio file: {audio_path}")
print("Loading model...")

model = WhisperModel(
    "large-v3",
    device="cpu",
    compute_type="int8",
)

print("Model loaded.")
print("Starting transcription...")

segments, info = model.transcribe(
    str(audio_path),
    language="ml",
    beam_size=5,
    best_of=5,
    temperature=(0.0, 0.2, 0.4, 0.6, 0.8),
    vad_filter=True,
    vad_parameters={"min_silence_duration_ms": 700},
    condition_on_previous_text=False,
    no_repeat_ngram_size=3,
    compression_ratio_threshold=2.4,
    log_prob_threshold=-1.0,
    no_speech_threshold=0.6,
    word_timestamps=False,
)

print()
print(f"Detected language: {info.language}")
print(f"Language probability: {info.language_probability:.2f}")
print()
print("========== TRANSCRIPT ==========")

texts = []

for segment in segments:
    text = segment.text.strip()

    if not text:
        continue

    texts.append(text)

    print(
        f"[{segment.start:06.2f} --> "
        f"{segment.end:06.2f}] {text}"
    )

print("================================")

print()
print("Final transcript:")
print(" ".join(texts))