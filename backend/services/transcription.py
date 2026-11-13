import os
import re
from typing import Any, Dict
from pathlib import Path
import requests

from config import (
    DEEPGRAM_API_KEY,
    DEEPGRAM_MODEL,
    MIN_CALL_DURATION_SECONDS,
    MIN_AUDIO_RMS,
)


# ============================================================
# TRANSCRIPTION CONFIGURATION
# ============================================================

DEEPGRAM_URL = "https://api.deepgram.com/v1/listen"
MIN_RMS = MIN_AUDIO_RMS


# ============================================================
# GENERAL HELPERS
# ============================================================

def _manual_guidance() -> str:
    return (
        "AI could not reliably understand enough of this call for safe CRM "
        "extraction and coaching, so please enter the important customer "
        "details manually.\n\n"
        "For better AI coaching on future calls:\n\n"
        "1. Speak clearly and slightly louder.\n"
        "2. Make sure the customer's voice is clearly audible.\n"
        "3. Avoid speaking over the customer.\n"
        "4. Keep your network connection stable.\n"
        "5. Move to a quieter location when possible.\n"
        "6. Ask the customer to repeat important details if the audio is unclear.\n"
        "7. Clearly confirm key details such as plot size, location, "
        "fencing requirement, budget and timeline.\n"
        "8. Avoid speaking too quickly.\n"
        "9. When important numbers, names or measurements are mentioned, "
        "repeat and confirm them clearly.\n"
        "10. If the customer is speaking very softly, politely ask them "
        "to speak a little louder."
    )


def _empty_result(
    status: str,
    message: str,
    audio: Dict[str, Any] | None = None,
    quality_flags: list[str] | None = None,
    error: str | None = None,
) -> Dict[str, Any]:

    result = {
        "status": status,
        "can_process": status != "manual_required",
        "transcript": "",
        "language": None,
        "language_confidence": None,
        "quality_score": 0,
        "quality_flags": quality_flags or [],
        "quality_statistics": {},
        "audio": audio or {},
        "message": message,
        "salesperson_guidance": _manual_guidance(),
    }

    if error:
        result["error"] = error

    return result


# ============================================================
# AUDIO INSPECTION
# ============================================================

def _inspect_audio(audio_path: str) -> Dict[str, Any]:
    """
    Inspect audio using Python's standard wave module where possible.

    Important:
    We only trust metadata from the WAV container when the file is WAV.

    MP3/MPEG files are not parsed as WAV.
    Their duration is obtained from ffprobe when available.
    """

    path = Path(audio_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Audio file not found: {audio_path}"
        )

    print("Running Layer 1 audio quality gate...")

    extension = path.suffix.lower()

    duration_seconds = None
    sample_rate = None
    channels = None
    rms = None
    flags = []

    # --------------------------------------------------------
    # WAV
    # --------------------------------------------------------

    if extension == ".wav":

        try:
            import wave

            with wave.open(str(path), "rb") as wav:

                channels = wav.getnchannels()
                sample_rate = wav.getframerate()
                frame_count = wav.getnframes()

                if sample_rate > 0:
                    duration_seconds = (
                        frame_count / sample_rate
                    )

                # Calculate RMS safely from PCM data.
                try:
                    import audioop

                    raw = wav.readframes(
                        min(frame_count, sample_rate * 10)
                    )

                    if raw:
                        rms = audioop.rms(
                            raw,
                            wav.getsampwidth()
                        )

                except Exception:
                    rms = None

        except Exception as exc:
            flags.append("wav_inspection_failed")
            print(
                f"Warning: WAV inspection failed: {exc}"
            )

    # --------------------------------------------------------
    # Non-WAV
    # --------------------------------------------------------

    else:

        # Try ffprobe for MP3/MPEG/M4A etc.
        try:

            import subprocess

            command = [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path),
            ]

            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:

                value = result.stdout.strip()

                if value:
                    duration_seconds = float(value)

        except Exception as exc:
            print(
                f"Warning: ffprobe duration detection failed: {exc}"
            )

        # We don't invent sample rate/channels for compressed files.
        sample_rate = None
        channels = None
        rms = None

    # --------------------------------------------------------
    # Duration gate
    # --------------------------------------------------------

    if (
        duration_seconds is not None
        and duration_seconds < MIN_CALL_DURATION_SECONDS
    ):
        flags.append("call_too_short")

    # --------------------------------------------------------
    # RMS gate
    # --------------------------------------------------------

    if (
        rms is not None
        and rms < MIN_RMS
    ):
        flags.append("very_low_audio_level")

    is_usable = (
        duration_seconds is not None
        and "call_too_short" not in flags
    )

    if duration_seconds is None:
        flags.append("duration_unavailable")
        is_usable = False

    audio = {
        "status": "ok" if is_usable else "warning",
        "is_usable": is_usable,
        "duration_seconds": duration_seconds,
        "sample_rate": sample_rate,
        "channels": channels,
        "rms": rms,
        "flags": flags,
    }

    print(f"Audio inspection: {audio}")

    return audio


# ============================================================
# TRANSCRIPT QUALITY
# ============================================================

def _calculate_transcript_quality(
    transcript: str,
    duration_seconds: float | None,
) -> Dict[str, Any]:

    text = transcript.strip()

    if not text:
        return {
            "status": "manual_required",
            "can_process": False,
            "quality_score": 0,
            "quality_flags": ["empty_transcript"],
            "message": (
                "No usable speech was detected. "
                "Manual entry is required."
            ),
            "statistics": {},
        }

    words = re.findall(
        r"\b[\wÀ-ÿ]+\b",
        text.lower(),
        flags=re.UNICODE,
    )

    word_count = len(words)

    if word_count == 0:
        return {
            "status": "manual_required",
            "can_process": False,
            "quality_score": 0,
            "quality_flags": ["no_words_detected"],
            "message": (
                "No meaningful words were detected. "
                "Manual entry is required."
            ),
            "statistics": {},
        }

    unique_words = set(words)

    unique_word_count = len(unique_words)

    frequencies = {}

    for word in words:
        frequencies[word] = frequencies.get(word, 0) + 1

    max_word_frequency = (
        max(frequencies.values())
        if frequencies
        else 0
    )

    repeated_word_ratio = 1 - (
        unique_word_count / word_count
    )

    flags = []

    # --------------------------------------------------------
    # Repetition
    # --------------------------------------------------------

    if repeated_word_ratio >= 0.65:
        flags.append("excessive_word_repetition")
        quality_score = 70

    elif repeated_word_ratio >= 0.50:
        flags.append("excessive_word_repetition")
        quality_score = 90

    else:
        quality_score = 100

    # --------------------------------------------------------
    # Very short transcript
    # --------------------------------------------------------

    if word_count < 15:
        flags.append("very_short_transcript")
        quality_score = min(
            quality_score,
            50
        )

    # --------------------------------------------------------
    # Character checks
    # --------------------------------------------------------

    character_count = len(text)

    replacement_character_ratio = (
        text.count("�") / max(character_count, 1)
    )

    if replacement_character_ratio > 0.01:
        flags.append("replacement_characters")
        quality_score = min(
            quality_score,
            50
        )

    # --------------------------------------------------------
    # Script distribution
    # --------------------------------------------------------

    script_distribution = {
        "latin": 0.0,
        "devanagari": 0.0,
        "kannada": 0.0,
        "tamil": 0.0,
        "telugu": 0.0,
        "malayalam": 0.0,
        "other": 0.0,
    }

    script_count = {
        key: 0
        for key in script_distribution
    }

    total_letters = 0

    for char in text:

        if not char.isalpha():
            continue

        total_letters += 1

        code = ord(char)

        if (
            0x0000 <= code <= 0x024F
        ):
            script_count["latin"] += 1

        elif (
            0x0900 <= code <= 0x097F
        ):
            script_count["devanagari"] += 1

        elif (
            0x0C80 <= code <= 0x0CFF
        ):
            script_count["kannada"] += 1

        elif (
            0x0B80 <= code <= 0x0BFF
        ):
            script_count["tamil"] += 1

        elif (
            0x0C00 <= code <= 0x0C7F
        ):
            script_count["telugu"] += 1

        elif (
            0x0D00 <= code <= 0x0D7F
        ):
            script_count["malayalam"] += 1

        else:
            script_count["other"] += 1

    if total_letters > 0:

        for key in script_distribution:
            script_distribution[key] = round(
                script_count[key] / total_letters,
                3,
            )

    statistics = {
        "word_count": word_count,
        "unique_word_count": unique_word_count,
        "repeated_word_ratio": round(
            repeated_word_ratio,
            3,
        ),
        "unique_word_ratio": round(
            unique_word_count / word_count,
            3,
        ),
        "max_word_frequency": max_word_frequency,
        "character_count": character_count,
        "replacement_character_ratio": round(
            replacement_character_ratio,
            3,
        ),
        "script_distribution": script_distribution,
        "duration_seconds": duration_seconds,
    }

    # --------------------------------------------------------
    # Final status
    # --------------------------------------------------------

    if quality_score < 80:

        status = "manual_required"
        can_process = False

        message = (
            "Transcript quality is insufficient for reliable "
            "CRM extraction and coaching. Manual entry is required."
        )

    elif quality_score < 95:

        status = "warning"
        can_process = True

        message = (
            "Transcript is usable but contains some quality "
            "warnings. CRM extraction and coaching can proceed "
            "with caution."
        )

    else:

        status = "trusted"
        can_process = True

        message = (
            "Transcript passed the Layer 1 quality gate."
        )

    return {
        "status": status,
        "can_process": can_process,
        "quality_score": quality_score,
        "quality_flags": flags,
        "message": message,
        "statistics": statistics,
    }


# ============================================================
# DEEPGRAM TRANSCRIPTION
# ============================================================

def _transcribe_with_deepgram(
    audio_path: str,
) -> Dict[str, Any]:

    api_key = DEEPGRAM_API_KEY

    if not api_key:
        raise RuntimeError(
            "DEEPGRAM_API_KEY is missing from the shared project configuration."
        )

    params = {
        "model": DEEPGRAM_MODEL,
        "smart_format": "true",
        "detect_language": "true",
        "utterances": "true",
    }

    headers = {
        "Authorization": f"Token {api_key}",
        "Content-Type": "application/octet-stream",
    }

    print("Starting Deepgram transcription...")
    print(
        f"Deepgram model: {DEEPGRAM_MODEL}"
    )

    with open(
        audio_path,
        "rb",
    ) as audio_file:

        response = requests.post(
            DEEPGRAM_URL,
            params=params,
            headers=headers,
            data=audio_file,
            timeout=300,
        )

    if not response.ok:

        raise RuntimeError(
            f"Deepgram API error "
            f"{response.status_code}: "
            f"{response.text}"
        )

    data = response.json()

    channel = (
        data
        .get("results", {})
        .get("channels", [{}])[0]
    )

    alternative = (
        channel
        .get("alternatives", [{}])[0]
    )

    transcript = (
        alternative
        .get("transcript", "")
        .strip()
    )

    confidence = alternative.get(
        "confidence"
    )

    # Deepgram's detect_language may return
    # language at different locations depending
    # on response/version.
    detected_language = (
        alternative.get("language")
        or channel.get("detected_language")
        or None
    )

    languages = alternative.get(
        "languages",
        []
    )

    if not detected_language and languages:
        detected_language = languages[0]

    print(
        f"Deepgram detected language: "
        f"{detected_language}"
    )

    print(
        f"Deepgram confidence: "
        f"{confidence}"
    )

    print(
        "========== TRANSCRIPT =========="
    )

    print(transcript)

    print(
        "================================"
    )

    return {
        "transcript": transcript,
        "language": detected_language,
        "confidence": confidence,
        "raw": data,
    }


# ============================================================
# PUBLIC FUNCTION
# ============================================================

def transcribe_audio_result(
    audio_path: str,
) -> Dict[str, Any]:

    path = Path(audio_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Audio file not found: {audio_path}"
        )

    print(
        f"Audio file found: {audio_path}"
    )

    # --------------------------------------------------------
    # Layer 1A — Audio quality
    # --------------------------------------------------------

    try:
        audio = _inspect_audio(
            audio_path
        )

    except Exception as exc:

        print(
            f"Audio inspection error: {exc}"
        )

        return _empty_result(
            status="manual_required",
            message=(
                "Audio quality could not be verified. "
                "Please enter the call details manually."
            ),
            quality_flags=[
                "audio_inspection_error"
            ],
            error=str(exc),
        )

    if not audio["is_usable"]:

        print(
            "Audio failed Layer 1 quality gate."
        )

        return _empty_result(
            status="manual_required",
            message=(
                "This call is too short or the audio could "
                "not be reliably inspected. Please enter "
                "the call details manually."
            ),
            audio=audio,
            quality_flags=audio["flags"],
        )

    # --------------------------------------------------------
    # Layer 1B — Deepgram transcription
    # --------------------------------------------------------

    try:

        transcription = _transcribe_with_deepgram(
            audio_path
        )

    except Exception as exc:

        print(
            f"Deepgram transcription error: {exc}"
        )

        return _empty_result(
            status="manual_required",
            message=(
                "Automatic transcription failed. "
                "Please enter the call details manually."
            ),
            audio=audio,
            quality_flags=[
                "transcription_api_error"
            ],
            error=str(exc),
        )

    transcript = transcription[
        "transcript"
    ]

    language = transcription[
        "language"
    ]

    confidence = transcription[
        "confidence"
    ]

    # --------------------------------------------------------
    # Layer 1C — Transcript quality
    # --------------------------------------------------------

    quality = _calculate_transcript_quality(
        transcript,
        audio.get("duration_seconds"),
    )

    print(
        f"Transcript quality: {quality}"
    )

    # --------------------------------------------------------
    # Final gate
    # --------------------------------------------------------

    if not quality["can_process"]:

        print(
            "Transcript rejected by quality gate."
        )

        return {
            "status": "manual_required",
            "can_process": False,
            "transcript": transcript,
            "language": language,
            "language_confidence": confidence,
            "quality_score": quality[
                "quality_score"
            ],
            "quality_flags": quality[
                "quality_flags"
            ],
            "quality_statistics": quality[
                "statistics"
            ],
            "audio": audio,
            "message": quality[
                "message"
            ],
            "salesperson_guidance": _manual_guidance(),
        }

    if quality["status"] == "warning":

        print(
            "Transcript accepted: WARNING — "
            "processing can continue."
        )

    else:

        print(
            "Transcript accepted: TRUSTED."
        )

    return {
        "status": quality["status"],
        "can_process": True,
        "transcript": transcript,
        "language": language,
        "language_confidence": confidence,
        "quality_score": quality[
            "quality_score"
        ],
        "quality_flags": quality[
            "quality_flags"
        ],
        "quality_statistics": quality[
            "statistics"
        ],
        "audio": audio,
        "message": quality[
            "message"
        ],
        "salesperson_guidance": _manual_guidance(),
    }


# ============================================================
# BACKWARD COMPATIBILITY
# ============================================================

def transcribe_audio(
    audio_path: str,
) -> str:

    result = transcribe_audio_result(
        audio_path
    )

    return result.get(
        "transcript",
        ""
    )