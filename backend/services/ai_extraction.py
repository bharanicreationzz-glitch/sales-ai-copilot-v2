import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


# Load environment variables
load_dotenv(
    Path(__file__).resolve().parents[2] / ".env"
)


# AI client for CRM extraction
ai_client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL")
)

AI_MODEL = os.getenv("AI_MODEL", "gpt-4o-mini")


def extract_crm_fields(transcript: str) -> dict:
    """
    Analyze a sales call transcript and extract CRM information.
    """

    prompt = f"""
You are an AI assistant for a fencing company's sales CRM.

Analyze the following sales call transcript and extract the CRM fields.

Transcript:
{transcript}

Return ONLY valid JSON.

Use exactly these fields:

{{
    "customer_name": "",
    "phone": "",
    "product": "",
    "customer_category": "",
    "language": "",
    "lead_potential": "",
    "quantity": "",
    "city": "",
    "next_follow_up_date": "",
    "notes": "",
    "ai_summary": ""
}}

Rules:
- Do not invent information.
- If a field is not mentioned, return "NA".
- Keep quantity exactly as understood from the conversation.
- lead_potential must be "Hot", "Warm", "Cold", or "NA".
- customer_category must be "B2B", "B2C", or "NA".
- language should identify the language spoken, or "NA".
- ai_summary should be a short summary of the customer's requirement and buying intent.
- Do not use Markdown.
- Do not wrap the JSON in ```json or ```.

Transcript:
{transcript}
"""

    response = ai_client.chat.completions.create(
        model=AI_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You extract structured CRM data from sales "
                    "conversations. Always return valid JSON only."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0
    )

    content = response.choices[0].message.content

    if not content:
        raise ValueError("AI returned an empty response")

    content = content.strip()

    # Remove Markdown JSON fences if the model adds them
    if content.startswith("```json"):
        content = content[7:]

    elif content.startswith("```"):
        content = content[3:]

    if content.endswith("```"):
        content = content[:-3]

    content = content.strip()

    try:
        return json.loads(content)

    except json.JSONDecodeError:
        print("AI RAW RESPONSE:")
        print(content)

        raise ValueError(
            "AI returned an invalid JSON response"
        )