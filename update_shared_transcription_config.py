from pathlib import Path

p = Path("backend/config.py")
s = p.read_text(encoding="utf-8-sig")

additions = '''
DEEPGRAM_MODEL = os.getenv("DEEPGRAM_MODEL", "nova-3")
MIN_CALL_DURATION_SECONDS = float(os.getenv("MIN_CALL_DURATION_SECONDS", "60"))
MIN_AUDIO_RMS = float(os.getenv("MIN_AUDIO_RMS", "300"))
'''

if "DEEPGRAM_MODEL =" not in s:
    anchor = 'ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")'
    if anchor not in s:
        raise RuntimeError("Expected config anchor not found; no changes made.")
    s = s.replace(anchor, anchor + "\n" + additions.strip() + "\n", 1)

p.write_text(s, encoding="utf-8")
print("Shared transcription settings added (if not already present).")
