from pathlib import Path

p = Path("backend/services/ai_extraction.py")
s = p.read_text(encoding="utf-8-sig")

marker = "# ============================================================\n# ENVIRONMENT"
start = s.index(marker)
client_line = "ai_client = OpenAI(api_key=OPENAI_API_KEY)"
end = s.index(client_line, start) + len(client_line)

header = '''import json
from datetime import datetime, timedelta, timezone

from config import AI_EXTRACTION_MODEL, OPENAI_API_KEY, OPENAI_BASE_URL
from openai import OpenAI


# ============================================================
# ENVIRONMENT
# ============================================================

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is missing from the project .env configuration.")

AI_MODEL = AI_EXTRACTION_MODEL
ai_client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)'''

p.write_text(header + s[end:], encoding="utf-8")
print("Extraction configuration updated; remaining code preserved.")
