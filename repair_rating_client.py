from pathlib import Path

p = Path("backend/services/conversation_rating.py")
s = p.read_text(encoding="utf-8-sig")

if "ai_client = OpenAI(" in s:
    print("OpenAI client initialization already exists; no change made.")
else:
    anchor = "from services.rag import search_sales_knowledge"
    if anchor not in s:
        raise RuntimeError("Expected import not found. File was not changed.")

    s = s.replace(
        anchor,
        anchor + "\n\nai_client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)",
        1,
    )
    p.write_text(s, encoding="utf-8")
    print("OpenAI client initialization restored.")
