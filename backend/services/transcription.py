from pathlib import Path
import whisper


# Global variable so the model loads only once
model = None


def get_model():
    global model

    if model is None:
        print("Loading Whisper SMALL model...")

        model = whisper.load_model("small")

        print("Whisper SMALL model loaded successfully.")

    return model


def transcribe_audio(audio_path: str) -> str:
    """
    Convert a sales call recording into text using local OpenAI Whisper.
    """

    audio_file_path = Path(audio_path)

    if not audio_file_path.exists():
        raise FileNotFoundError(
            f"Audio file not found: {audio_file_path}"
        )

    print(f"Audio file found: {audio_file_path}")
    print("Getting Whisper model...")

    whisper_model = get_model()

    print("Starting transcription...")

    result = whisper_model.transcribe(
        str(audio_file_path),
        fp16=False,
        language="en",
        task="transcribe",
        temperature=0,
        verbose=True
    )

    print("Transcription completed!")
    print("========== TRANSCRIPT ==========")
    print(result["text"])
    print("================================")

    transcript = result["text"]

    return transcript.strip()