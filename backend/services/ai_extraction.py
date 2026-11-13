import json
from datetime import datetime, timedelta, timezone
from typing import Any

from config import AI_EXTRACTION_MODEL, OPENAI_API_KEY, OPENAI_BASE_URL
from openai import OpenAI


# ============================================================
# ENVIRONMENT
# ============================================================

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is missing from the project .env configuration.")

AI_MODEL = AI_EXTRACTION_MODEL
ai_client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)


# ============================================================
# FOLLOW-UP CONFIGURATION
# ============================================================

HOT_FOLLOWUP_DAYS = 1
WARM_FOLLOWUP_DAYS = 10
COLD_FOLLOWUP_DAYS = 18


# ============================================================
# CURRENT DATE
# ============================================================

INDIA_OFFSET = timezone(timedelta(hours=5, minutes=30))


def get_india_today():
    return datetime.now(INDIA_OFFSET).date()


def get_followup_date(lead_potential):
    """Map lead potential to its next follow-up date."""
    lead = str(lead_potential or "").strip().lower()

    if lead == "hot":
        days = HOT_FOLLOWUP_DAYS
    elif lead == "warm":
        days = WARM_FOLLOWUP_DAYS
    else:
        days = COLD_FOLLOWUP_DAYS

    return (get_india_today() + timedelta(days=days)).isoformat()


# ============================================================
# PRODUCT NORMALIZATION
# ============================================================

# Canonical product names align with the current JustFence CRM catalog.
# Aliases are intentionally conservative; do not map an uncertain product.
PRODUCT_ALIASES = {
    # Agriculture
    "polyhex": "Polyhex Mesh",
    "polyhex mesh": "Polyhex Mesh",
    "fiber mesh": "Polyhex Mesh",
    "fibre mesh": "Polyhex Mesh",
    "fiber fencing": "Polyhex Mesh",
    "fibre fencing": "Polyhex Mesh",
    "hex mesh": "Polyhex Mesh",

    "checks mesh": "Checks Mesh",
    "check mesh": "Checks Mesh",
    "checker mesh": "Checks Mesh",

    "trinity pole": "Trinity Pole",
    "trinity poles": "Trinity Pole",
    "trinity fence pole": "Trinity Pole",
    "trinity fencing pole": "Trinity Pole",

    "frp rod": "FRP Rod",
    "frp rods": "FRP Rod",
    "fiberglass rod": "FRP Rod",
    "fiber glass rod": "FRP Rod",
    "fibre glass rod": "FRP Rod",

    "pet wire": "PET Wire",
    "pet fencing wire": "PET Wire",
    "plant wire": "PET Wire",

    "shade net": "Shade Net",
    "shadenet": "Shade Net",
    "shade cloth": "Shade Net",

    # Decor
    "lato fence": "Lato Fence",
    "lato fencing": "Lato Fence",

    "indian trellis": "Indian Trellis",
    "indian style trellis": "Indian Trellis",

    "american trellis": "American Trellis",
    "american style trellis": "American Trellis",

    "australian trellis": "Australian Trellis",
    "australian style trellis": "Australian Trellis",

    "semi trellis": "Semi Trellis",
    "semi-trellis": "Semi Trellis",

    "privezy": "Privezy Wall",
    "privezy wall": "Privezy Wall",
    "privezy grass wall": "Privezy Wall",
    "grass wall": "Privezy Wall",
    "artificial grass wall": "Privezy Wall",

    "antiqo": "Antiqo Fence",
    "antiqo fence": "Antiqo Fence",
    "antiqo fencing": "Antiqo Fence",

    # Security
    "razor wire": "Razor Wire",
    "razor wires": "Razor Wire",
    "razor coil": "Razor Wire",
    "razor coil fence": "Razor Wire",

    "concertina coil": "Concertina Coil",
    "concertina wire": "Concertina Coil",
    "concertina": "Concertina Coil",

    # Legacy / broader terms retained for compatibility
    "chain mesh": "Chain Link Mesh",
    "chainlink": "Chain Link Mesh",
    "chain link": "Chain Link Mesh",
    "chain link mesh": "Chain Link Mesh",
    "welded mesh": "Welded Mesh",
    "weld mesh": "Welded Mesh",
    "precast": "Modular Wall",
    "precast wall": "Modular Wall",
    "modular wall": "Modular Wall",
    "modular walls": "Modular Wall",
    "plot fence": "Plot Fencing",
    "plot fencing": "Plot Fencing",
}

PRODUCT_CATEGORIES = {
    "Polyhex Mesh": "Agriculture",
    "Checks Mesh": "Agriculture",
    "Trinity Pole": "Agriculture",
    "FRP Rod": "Agriculture",
    "PET Wire": "Agriculture",
    "Shade Net": "Agriculture",
    "Lato Fence": "Decor",
    "Indian Trellis": "Decor",
    "American Trellis": "Decor",
    "Australian Trellis": "Decor",
    "Semi Trellis": "Decor",
    "Privezy Wall": "Decor",
    "Antiqo Fence": "Decor",
    "Razor Wire": "Security",
    "Concertina Coil": "Security",
    "Chain Link Mesh": "Other",
    "Welded Mesh": "Other",
    "Modular Wall": "Other",
    "Plot Fencing": "Other",
}


def normalize_product(product):
    """Normalize known product aliases while preserving unknown values."""
    if not product:
        return "NA"

    value = str(product).strip()
    if not value or value.lower() in {"na", "n/a", "none", "null", "unknown"}:
        return "NA"

    lower_value = " ".join(value.lower().replace("-", " ").split())

    # Exact alias match first, avoiding accidental substring matches.
    if lower_value in PRODUCT_ALIASES:
        return PRODUCT_ALIASES[lower_value]

    # Longest alias first for phrases such as "Privezy grass wall".
    for alias in sorted(PRODUCT_ALIASES, key=len, reverse=True):
        if alias in lower_value:
            return PRODUCT_ALIASES[alias]

    return value


def infer_product_category(product, supplied_category=None):
    """Use the known catalog mapping; otherwise preserve a valid supplied value."""
    normalized_product = normalize_product(product)
    if normalized_product in PRODUCT_CATEGORIES:
        return PRODUCT_CATEGORIES[normalized_product]

    category = normalize_na(supplied_category)
    if category.lower() in {"agriculture", "decor", "security", "other"}:
        return category.title()
    return "NA"


# ============================================================
# TEXT NORMALIZATION
# ============================================================


def clean_text(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def normalize_na(value):
    value = clean_text(value)
    if not value:
        return "NA"

    if value.lower() in {
        "null", "none", "unknown", "not available", "not mentioned",
        "n/a", "na", "n.a.",
    }:
        return "NA"

    return value


def normalize_boolean(value):
    """Return True, False, or the string 'NA' for uncertain values."""
    if isinstance(value, bool):
        return value
    if value is None:
        return "NA"

    normalized = str(value).strip().lower()
    if normalized in {"true", "yes", "y", "required", "needed"}:
        return True
    if normalized in {"false", "no", "n", "not required", "not needed"}:
        return False
    return "NA"


# ============================================================
# LEAD INTENT RULES
# ============================================================


def calculate_lead_potential(data, transcript):
    """Apply business rules after LLM extraction to classify lead intent."""
    text = transcript.lower()
    timeline = clean_text(data.get("timeline", "")).lower()
    notes = clean_text(data.get("notes", "")).lower()
    summary = clean_text(data.get("ai_summary", "")).lower()
    combined = f"{text} {timeline} {notes} {summary}"

    hot_phrases = [
        "need a quotation", "send the quotation", "send me the quotation",
        "share the quotation", "quotation on whatsapp", "send quotation on whatsapp",
        "quote on whatsapp", "send details on whatsapp", "share details on whatsapp",
        "please send quotation", "please arrange a site visit", "arrange a site visit",
        "book a site visit", "site visit", "start this week", "start immediately",
        "start now", "install this week", "need it immediately", "want it immediately",
        "ready to proceed", "ready to buy", "ready to order",
    ]
    if any(phrase in combined for phrase in hot_phrases):
        return "Hot"

    exact_requirement_signals = 0
    quantity = clean_text(data.get("quantity", "")).lower()
    product = clean_text(data.get("product", "")).lower()
    city = clean_text(data.get("city", "")).lower()

    if quantity and quantity != "na":
        exact_requirement_signals += 1
    if product and product != "na":
        exact_requirement_signals += 1
    if city and city != "na":
        exact_requirement_signals += 1

    pricing_signals = [
        "what is the price", "what's the price", "how much", "rate",
        "costing", "price", "quotation", "quote",
    ]
    pricing_interest = any(phrase in combined for phrase in pricing_signals)

    if exact_requirement_signals >= 2 and pricing_interest:
        return "Hot"

    warm_phrases = [
        "next month", "within a month", "planning to", "planning", "will do",
        "looking to", "considering", "need fencing", "require fencing",
        "send quotation", "send details", "interested", "checking options",
        "comparing options",
    ]
    if any(phrase in combined for phrase in warm_phrases):
        return "Warm"

    cold_phrases = [
        "just checking", "just enquiring", "only checking", "not sure",
        "no idea when", "maybe later", "just wanted to know",
        "just wanted to check", "no immediate plan", "not decided",
        "not decided yet",
    ]
    if any(phrase in combined for phrase in cold_phrases):
        return "Cold"

    if exact_requirement_signals >= 1:
        return "Warm"

    return "Cold"


# ============================================================
# MAIN EXTRACTION FUNCTION
# ============================================================


def extract_crm_fields(transcript):
    """Extract transcript details into CRM-ready fields."""
    transcript = clean_text(transcript)

    if not transcript:
        return {
            "customer_name": "NA",
            "phone": "NA",
            "product": "NA",
            "product_category": "NA",
            "product_variant": "NA",
            "product_specification": "NA",
            "application": "NA",
            "customer_category": "NA",
            "language": "NA",
            "lead_potential": "Cold",
            "quantity": "NA",
            "unit": "NA",
            "required_length": "NA",
            "required_height": "NA",
            "required_thickness": "NA",
            "budget": "NA",
            "installation_required": "NA",
            "city": "NA",
            "next_follow_up_date": get_followup_date("Cold"),
            "notes": "No usable transcript was provided.",
            "ai_summary": "No usable transcript was available for CRM extraction.",
        }

    system_prompt = """
You are an AI CRM extraction assistant for JustFence.
Convert a sales-call transcript into structured CRM information.

BUSINESS CONTEXT
JustFence sells fencing, agriculture, decorative fencing, and boundary-security products.
Do not invent information. If a field is not explicitly present or cannot be confidently
identified, return the string "NA". Do not treat the examples below as facts about this call.

PRODUCT CATALOG AND NORMALIZATION
Agriculture:
- Polyhex Mesh (also called fiber mesh, fibre mesh, fiber fencing, fibre fencing, hex mesh)
- Checks Mesh
- Trinity Pole / Trinity Fence Pole
- FRP Rod (also called fiberglass/fibre-glass rod)
- PET Wire (legacy term Plant Wire may refer to this product; normalize only when context supports it)
- Shade Net

Decor:
- Lato Fence
- Indian Trellis
- American Trellis
- Australian Trellis
- Semi Trellis
- Privezy Wall (also called Privezy Grass Wall or grass wall)
- Antiqo Fence

Security:
- Razor Wire / Razor Coil
- Concertina Coil / Concertina Wire

Legacy or other terms:
- Chain Link Mesh
- Welded Mesh
- Modular Wall / Precast Wall
- Plot Fencing

Use the canonical product names listed above when the match is clear. If the product is
ambiguous or outside this catalog, preserve the customer's wording rather than guessing.

PRODUCT CATEGORY
Use one of: Agriculture, Decor, Security, Other, or "NA".

CUSTOMER CATEGORY
Use one of: B2C, B2B, Dealer, Contractor, Builder, Architect, Unknown, or "NA".
Use "NA" when there is insufficient evidence.

LEAD CLASSIFICATION GUIDANCE
Hot:
- Customer requests a quotation, pricing for a specific requirement, a site visit, or asks
  for details/quotation on WhatsApp.
- Customer wants to start soon or shows clear immediate buying intent.
- Customer gives specific quantity/dimensions and is actively evaluating.
Warm:
- Genuine requirement exists but the project is planned for later.
- Customer is comparing options or requests a quotation without immediate timeline.
Cold:
- Customer is only checking price, has no clear requirement, is unsure whether/when to
  proceed, or is having a purely exploratory conversation.
A customer comparing products is NOT automatically Cold.
The application will apply additional business scoring rules after extraction; extract facts
faithfully and do not fabricate urgency.

EXTRACTION FIELDS
Extract exactly these fields:
customer_name, phone, product, product_category, product_variant,
product_specification, application, customer_category, language, lead_potential,
quantity, unit, required_length, required_height, required_thickness, budget,
installation_required, city, timeline, notes, ai_summary.

PRODUCT DETAILS
- product_variant: specific variant/type stated by the customer.
- product_specification: technical specifications explicitly stated.
- application: intended use or site/project context.
- quantity: actual required quantity, preserving meaningful units/details.
- unit: unit associated with the quantity, such as roll, panel, pole, rod, sheet, feet, meter.
- required_length, required_height, required_thickness: capture stated dimensions.
- budget: stated budget or range only.
- installation_required: true if explicitly requested; false if explicitly declined; otherwise "NA".
Do not infer specifications, dimensions, budget, or installation requirement.
If multiple measurements are mentioned, preserve useful details in the appropriate fields and notes.

NOTES
Write concise CRM notes covering requirements, product comparison, pricing interest,
dimensions, timeline, WhatsApp request, site visit request, and other useful sales details.

AI SUMMARY
Write a concise 1–3 sentence sales summary based only on the transcript.
Return ONLY valid JSON. Use JSON booleans true/false for installation_required when known,
and the string "NA" when unknown.
"""

    user_prompt = f"""
Extract CRM information from this sales call transcript.

--- TRANSCRIPT START ---
{transcript}
--- TRANSCRIPT END ---

Return a JSON object with exactly these fields and value types:
{{
  "customer_name": "NA",
  "phone": "NA",
  "product": "NA",
  "product_category": "NA",
  "product_variant": "NA",
  "product_specification": "NA",
  "application": "NA",
  "customer_category": "NA",
  "language": "NA",
  "lead_potential": "NA",
  "quantity": "NA",
  "unit": "NA",
  "required_length": "NA",
  "required_height": "NA",
  "required_thickness": "NA",
  "budget": "NA",
  "installation_required": "NA",
  "city": "NA",
  "timeline": "NA",
  "notes": "NA",
  "ai_summary": "NA"
}}
"""

    response = ai_client.chat.completions.create(
        model=AI_MODEL,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("OpenAI returned an empty response.")

    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"AI returned invalid JSON:\n{content}") from exc

    # Normalize extracted values.
    customer_name = normalize_na(data.get("customer_name"))
    phone = normalize_na(data.get("phone"))
    product = normalize_product(data.get("product"))
    product_category = infer_product_category(product, data.get("product_category"))
    product_variant = normalize_na(data.get("product_variant"))
    product_specification = normalize_na(data.get("product_specification"))
    application = normalize_na(data.get("application"))
    customer_category = normalize_na(data.get("customer_category"))
    language = normalize_na(data.get("language"))
    quantity = normalize_na(data.get("quantity"))
    unit = normalize_na(data.get("unit"))
    required_length = normalize_na(data.get("required_length"))
    required_height = normalize_na(data.get("required_height"))
    required_thickness = normalize_na(data.get("required_thickness"))
    budget = normalize_na(data.get("budget"))
    installation_required = normalize_boolean(data.get("installation_required"))
    city = normalize_na(data.get("city"))
    timeline = normalize_na(data.get("timeline"))
    notes = normalize_na(data.get("notes"))
    ai_summary = normalize_na(data.get("ai_summary"))

    normalized_data = {
        "customer_name": customer_name,
        "phone": phone,
        "product": product,
        "product_category": product_category,
        "product_variant": product_variant,
        "product_specification": product_specification,
        "application": application,
        "customer_category": customer_category,
        "language": language,
        "quantity": quantity,
        "unit": unit,
        "required_length": required_length,
        "required_height": required_height,
        "required_thickness": required_thickness,
        "budget": budget,
        "installation_required": installation_required,
        "city": city,
        "timeline": timeline,
        "notes": notes,
        "ai_summary": ai_summary,
    }

    lead_potential = calculate_lead_potential(normalized_data, transcript)
    next_follow_up_date = get_followup_date(lead_potential)

    return {
        "customer_name": customer_name,
        "phone": phone,
        "product": product,
        "product_category": product_category,
        "product_variant": product_variant,
        "product_specification": product_specification,
        "application": application,
        "customer_category": customer_category,
        "language": language,
        "lead_potential": lead_potential,
        "quantity": quantity,
        "unit": unit,
        "required_length": required_length,
        "required_height": required_height,
        "required_thickness": required_thickness,
        "budget": budget,
        "installation_required": installation_required,
        "city": city,
        "next_follow_up_date": next_follow_up_date,
        "notes": notes,
        "ai_summary": ai_summary,
    }


def extract_lead_data(transcript):
    """Backward-compatible alias."""
    return extract_crm_fields(transcript)


# ============================================================
# LOCAL TEST
# ============================================================

if __name__ == "__main__":
    test_transcript = """
    Hello. I need a quotation for two acres of land.
    I am looking for fiber mesh.
    Five feet height and around 100 feet length.
    What is the price?
    Please send the quotation on WhatsApp.
    """

    result = extract_crm_fields(test_transcript)
    print(json.dumps(result, indent=2, ensure_ascii=False))
