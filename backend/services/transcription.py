from pathlib import Path

from faster_whisper import WhisperModel


# Load Whisper model locally
# "base" gives a good balance between speed and accuracy.
model = WhisperModel(
    "base",
    device="cpu",
    compute_type="int8"
)


def transcribe_audio(audio_path: str) -> str:
    """
    Convert a sales call recording into text using local Whisper.
    """

    audio_file_path = Path(audio_path)

    if not audio_file_path.exists():
        raise FileNotFoundError(
            f"Audio file not found: {audio_file_path}"
        )

    segments, info = model.transcribe(
        str(audio_file_path),
        beam_size=5
    )

    transcript = " ".join(
        segment.text.strip()
        for segment in segments
    )

    return transcript.strip()