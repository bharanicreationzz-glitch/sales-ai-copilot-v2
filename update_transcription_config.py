from pathlib import Path

p = Path("backend/services/transcription.py")
s = p.read_text(encoding="utf-8-sig")

old_imports = '''import os
import re
from pathlib import Path
from typing import Any, Dict

import requests
from dotenv import load_dotenv
'''

new_imports = '''import os
import re
from typing import Any, Dict

import requests

from config import (
    DEEPGRAM_API_KEY,
    DEEPGRAM_MODEL,
    MIN_CALL_DURATION_SECONDS,
    MIN_AUDIO_RMS,
)
'''

old_config = '''# ============================================================
# PATHS / ENVIRONMENT
# ============================================================

# transcription.py
#   backend/
#       services/
#           transcription.py
#
# Project root:
#   sales-ai-copilot/
#
# .env is located at:
#   sales-ai-copilot/.env

SERVICE_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SERVICE_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent

ENV_FILE = PROJECT_ROOT / ".env"

load_dotenv(ENV_FILE, override=True)


# ============================================================
# DEEPGRAM CONFIGURATION
# ============================================================

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")

DEEPGRAM_MODEL = os.getenv(
    "DEEPGRAM_MODEL",
    "nova-3"
)

DEEPGRAM_URL = (
    "https://api.deepgram.com/v1/listen"
)


# ============================================================
# AUDIO QUALITY CONFIGURATION
# ============================================================

MIN_CALL_DURATION_SECONDS = float(
    os.getenv("MIN_CALL_DURATION_SECONDS", "60")
)

MIN_RMS = float(
    os.getenv("MIN_AUDIO_RMS", "300")
)
'''

new_config = '''# ============================================================
# TRANSCRIPTION CONFIGURATION
# ============================================================

DEEPGRAM_URL = "https://api.deepgram.com/v1/listen"
MIN_RMS = MIN_AUDIO_RMS
'''

if old_imports not in s:
    raise RuntimeError("Import block did not match; file was not changed.")

if old_config not in s:
    raise RuntimeError("Configuration block did not match; file was not changed.")

s = s.replace(old_imports, new_imports, 1)
s = s.replace(old_config, new_config, 1)

old_reload = '''    # Reload explicitly from project root.
    load_dotenv(
        ENV_FILE,
        override=True
    )

    api_key = os.getenv(
        "DEEPGRAM_API_KEY"
    )
'''

new_reload = '''    api_key = DEEPGRAM_API_KEY
'''

if old_reload not in s:
    raise RuntimeError(
        "Deepgram environment reload block did not match; "
        "only earlier in-memory changes were made."
    )

s = s.replace(old_reload, new_reload, 1)
s = s.replace(
    '''        raise RuntimeError(
            f"DEEPGRAM_API_KEY is missing. "
            f"Expected .env at: {ENV_FILE}"
        )''',
    '''        raise RuntimeError(
            "DEEPGRAM_API_KEY is missing from the shared project configuration."
        )''',
    1,
)

p.write_text(s, encoding="utf-8")
print("Transcription configuration updated; remaining logic preserved.")
