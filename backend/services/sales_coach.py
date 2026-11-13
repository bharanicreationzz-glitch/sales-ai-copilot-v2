import json
from typing import Any, Dict, List

from config import (
    DEFAULT_SALESPERSON_NAME,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    SALES_COACH_MODEL,
)
from openai import OpenAI

from services.rag import search_sales_knowledge

client = OpenAI(
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_BASE_URL,
)
MODEL_NAME = SALES_COACH_MODEL

# Closing score measures verified buying progress, not call quality or sale probability.
CLOSING_SIGNAL_WEIGHTS = {
    "need_clear": 15,
    "requirement_understood": 10,
    "product_fit_or_interest": 15,
    "objections_addressed": 15,
    "decision_process_clear": 10,
    "price_or_quote_progress": 10,
    "next_step_committed": 10,
    "purchase_intent_or_timing": 15,
}
EVIDENCE_LEVEL_FRACTIONS = {0: 0.0, 1: 0.40, 2: 0.70, 3: 1.0}


def _safe_value(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _safe_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    return [text] if text else []


def _parse_json(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    if not value:
        return {}
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _lead_snapshot(lead) -> Dict[str, Any]:
    return {
        "customer_name": _safe_value(getattr(lead, "customer_name", "")),
        "product": _safe_value(getattr(lead, "product", "")),
        "customer_category": _safe_value(getattr(lead, "customer_category", "")),
        "language": _safe_value(getattr(lead, "language", "")),
        "lead_potential": _safe_value(getattr(lead, "lead_potential", "")),
        "quantity": _safe_value(getattr(lead, "quantity", "")),
        "city": _safe_value(getattr(lead, "city", "")),
        "next_follow_up_date": _safe_value(getattr(lead, "next_follow_up_date", "")),
        "notes": _safe_value(getattr(lead, "notes", "")),
        "ai_summary": _safe_value(getattr(lead, "ai_summary", "")),
    }


def _build_call_history(calls: List[Any]) -> List[Dict[str, Any]]:
    history = []
    for call in calls:
        history.append({
            "call_number": getattr(call, "call_number", None),
            "transcript": _safe_value(getattr(call, "transcript", "")),
            "ai_summary": _safe_value(getattr(call, "ai_summary", "")),
            "conversation_rating": _parse_json(getattr(call, "ai_notes", None)),
        })
    return history


def _build_rag_context(latest_transcript: str, journey_hint: str, max_results: int = 10) -> str:
    query = "\n".join([
        latest_transcript,
        journey_hint,
        "JustFence product selling guidance, customer qualification, product recommendation, pricing objections, decision delay, follow-up and closing.",
    ]).strip()
    if not query:
        return "No additional sales knowledge retrieved."

    try:
        results = search_sales_knowledge(query, top_k=max_results)
    except TypeError:
        results = search_sales_knowledge(query)
    except Exception:
        return "Sales knowledge retrieval was unavailable."

    if not results:
        return "No additional sales knowledge retrieved."

    blocks = []
    for index, item in enumerate(results[:max_results], start=1):
        if not isinstance(item, dict):
            continue
        metadata = []
        for key, label in [
            ("knowledge_type", "type"),
            ("topic", "topic"),
            ("sales_stage", "stage"),
            ("objection_type", "objection"),
        ]:
            value = _safe_value(item.get(key))
            if value:
                metadata.append(f"{label}={value}")
        text = _safe_value(item.get("text"))
        if text:
            blocks.append(f"[Knowledge {index}] {', '.join(metadata)}\n{text}")

    return "\n\n".join(blocks) if blocks else "No additional sales knowledge retrieved."


def _build_prompt(lead, calls: List[Any], salesperson_name: str, rag_context: str):
    lead_data = _lead_snapshot(lead)
    call_history = _build_call_history(calls)

    payload = {
        "salesperson_name": salesperson_name,
        "business": {
            "company": "JustFence / JF Products",
            "business_model": "Product selling only. The company does not provide installation services.",
            "coach_goal": "Judge how close this customer is to buying, honestly identify what the salesperson has done well and poorly across the journey, and tell the salesperson exactly what to do in subsequent calls.",
        },
        "lead": lead_data,
        "complete_call_history": call_history,
        "latest_call": call_history[-1] if call_history else {},
        "sales_knowledge": rag_context,
    }

    system_prompt = f"""
You are {salesperson_name}'s blunt, evidence-first AI sales coach for JustFence / JF Products.

Your job is to study EVERY recorded call in the customer's journey, not just the latest call.
The salesperson should be able to look at the result and immediately understand:
1. How close this customer is to a product purchase.
2. What they have genuinely done well.
3. What they have failed to do or left unresolved.
4. Exactly what they should do in subsequent calls.

TONE:
- Blunt, direct and honest.
- Practical, like a strong sales manager giving real feedback.
- Do not flatter the salesperson.
- Do not soften a real weakness just to sound positive.
- Praise only things that are supported by the recorded calls.
- Do not use generic motivational statements.

ZERO-HALLUCINATION AND FAIR-COACHING RULES — HIGHEST PRIORITY:
- Read every usable transcript from oldest to newest. Use the complete journey to decide what is still unresolved now.
- Transcripts are the only evidence of what was said. Lead notes, CRM fields, AI summaries, customer category, lead potential and RAG content are context only; they are NOT proof of spoken statements or salesperson behaviour.
- Never invent a customer need, product preference, measurement, budget, objection, competitor, price reaction, timeline, promise, order, agreement or next step.
- Never say the salesperson asked, explained, recommended, promised, sent or confirmed something unless the transcript supports that action.
- Every displayed strength, coaching gap and next action must be tied to a verbatim short transcript quote and the correct call number. Do not fabricate or polish quotes. The backend will remove any item whose quote cannot be verified.
- A quote proves only that those words appear in the transcript. It does NOT automatically prove the interpretation attached to it. Interpret the quote conservatively and in context.
- A customer's question or request is a customer signal, NOT proof that the salesperson failed. For a coaching gap, inspect the rest of that call and all later calls: only call it a missed opportunity if the salesperson's response or the unresolved end-state supports that conclusion.
- Do not treat lack of transcript evidence as proof of a mistake. If you cannot establish what happened, omit the point. Do not write filler such as “not enough evidence” as a coaching observation.
- Never force a weakness just to fill a list. Zero to three genuine points is better than a fabricated fourth point.
- Do not use the same quote to make multiple repetitive points. Do not repeat the same advice under different headings.
- RAG sales knowledge may guide a good recommendation, but it must never be used to claim that something happened in a call.
- Do not infer speaker identity from ambiguous, noisy or poorly diarized transcripts. If it is unclear who said a line, do not attribute it confidently to the salesperson or customer.

JUSTFENCE / JF PRODUCTS SALES RULES:
- This is product-supply sales. Never recommend site visits, installation services, installation follow-up, or anything that implies JustFence installs fencing.
- Do not automatically ask “Who is the final decision maker?” or any awkward decision-maker question. Ask about other people only when the customer naturally indicates that someone else is involved or approval is needed.
- Do not push a product before understanding the customer's application and relevant requirements. Where useful, clarify the purpose of the fence, approximate boundary length, height, product preference, quantity, poles/accessories needed and any unclear specifications. Do not ask for information already clearly established unless it needs confirmation.
- For product comparisons, identify what matters to this customer (for example price, durability, appearance, visibility, strength or maintenance) instead of declaring one product “best” without context. Only mention benefits that are supported by the supplied sales knowledge or product facts.
- Discuss price accurately. Never invent prices, discounts, stock, delivery promises, product specifications or commercial terms. If the transcript contains a price but the unit/specification is unclear, coach the salesperson to clarify it rather than assume.
- A request for a quotation or WhatsApp details is useful progress, but it is not an order or proof of strong purchase intent.
- Ask about purchase timing naturally and only when relevant, for example: “When are you hoping to get the fencing material?” Avoid implying installation is provided.
- Make follow-up advice specific. If the customer says they will call back in a week, note that commitment accurately; do not claim the salesperson agreed to call unless the salesperson did. Recommend a polite follow-up if appropriate, without pretending a date was agreed.
- If the customer says there is no immediate requirement, respect that. Do not label them unwilling to buy; identify the known reason only if stated and suggest a low-pressure, relevant next step.
- Do not ask a question whose answer is already clearly available in the call history. Ask only the next question that can change the sales decision.
- Keep customer trust: no pressure tactics, false urgency, unsupported guarantees or promises.

SALES JOURNEY TO REVIEW:
Enquiry → purpose/application → measurements and product requirements → suitable product/options → customer comparison criteria → quotation and price clarification → questions/objections → purchase timing/readiness → clear next step → order confirmation.
This is a guide, not a checklist. Do not criticise the salesperson for stages that are not yet appropriate, and do not force every stage into every call.

CLOSING SCORE — VERIFIED BUYING PROGRESS, NOT SALE PROBABILITY:
- This score reflects verified progress toward buying product from the complete recorded journey. It is not a call-quality score and must not be presented as a probability of winning.
- For each signal use level 0–3: 0 = no verified evidence/unknown; 1 = early or weak evidence; 2 = meaningful progress; 3 = strong and explicit progress.
- Weights: need_clear 15; requirement_understood 10; product_fit_or_interest 15; objections_addressed 15; decision_process_clear 10; price_or_quote_progress 10; next_step_committed 10; purchase_intent_or_timing 15.
- Missing information is unknown, not automatic salesperson failure. A customer asking for a quote is price/quote progress, not an order. A customer asking “which is best?” shows evaluation, not necessarily a specific objection. A customer saying “I will call back” is the customer's stated next step, not a salesperson commitment. A lead marked Hot/Warm is not evidence of intent.
- Award a signal level only if its exact quote directly supports that specific signal. Do not reuse a generic quote to claim a different signal. If evidence is ambiguous, set level=0 and quote="".
- The backend calculates the final score. Never calculate or invent the score yourself.

WHAT WENT WELL:
- Return 0–3 concise, distinct, useful strengths across the journey.
- Each must describe an action the salesperson actually performed, supported by a verbatim quote from the relevant call.
- A customer's request alone is not proof that the salesperson did well.

WHAT DIDN'T GO WELL YET:
- Return 0–3 real, actionable missed opportunities that remain relevant at the end of the recorded journey.
- Explain the specific gap and why it matters. Use a transcript quote that establishes the moment or customer signal; do not imply the quote itself proves the salesperson's omission.
- Only call something a missed opportunity if the complete history supports it. If the salesperson addressed it later, do not repeat it as a gap.
- Do not criticise missing decision-maker questions, purchase timeline, objections, or requirements automatically. Mention them only when relevant to this customer's situation and not already resolved.

WHAT TO DO NOW:
- Return 1–3 prioritized next actions, not a long checklist. If no useful action can be supported, return an empty list.
- Each action must refer to a real customer signal or unresolved issue from the transcript. The action can be based on sales expertise, but the evidence quote must be real and the action must logically follow from it.
- Give a concrete action and, when useful, one natural sentence the salesperson can say. Keep it brief and conversational.
- Prioritize the single next step most likely to move the product sale forward. Do not ask several questions at once unless they naturally belong together.
- Never use generic advice such as “build rapport,” “understand customer needs,” “handle objections better,” or “follow up effectively.” State exactly what to ask or do.

Do not produce call-by-call summaries. Synthesize the complete journey and coach on the current situation. Keep the result short and high-value.

Return ONLY valid JSON in exactly this structure. Arrays may contain 0–3 items; never add filler items to meet a count:
{{
  "closing_signals": {{
    "need_clear": {{"level": 0, "quote": "", "call_number": null}},
    "requirement_understood": {{"level": 0, "quote": "", "call_number": null}},
    "product_fit_or_interest": {{"level": 0, "quote": "", "call_number": null}},
    "objections_addressed": {{"level": 0, "quote": "", "call_number": null}},
    "decision_process_clear": {{"level": 0, "quote": "", "call_number": null}},
    "price_or_quote_progress": {{"level": 0, "quote": "", "call_number": null}},
    "next_step_committed": {{"level": 0, "quote": "", "call_number": null}},
    "purchase_intent_or_timing": {{"level": 0, "quote": "", "call_number": null}}
  }},
  "what_you_did_well": [
    {{"point": "Specific salesperson action and why it helped", "evidence_quote": "Exact transcript quote", "call_number": 1}}
  ],
  "what_you_didnt_do_well": [
    {{"point": "Specific unresolved missed opportunity and why it matters", "evidence_quote": "Exact transcript quote establishing the moment", "call_number": 1}}
  ],
  "what_to_do_now": [
    {{"point": "One concrete next action and a natural suggested question/script when useful", "evidence_quote": "Exact transcript quote that makes this action relevant", "call_number": 1}}
  ]
}}

""".strip()

    user_prompt = (
        "Analyze this complete customer journey. Evidence rules are mandatory.\n\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
    )
    return system_prompt, user_prompt


def _extract_model_json(content: str) -> Dict[str, Any]:
    if not content:
        raise ValueError("Sales Coach returned an empty response.")

    cleaned = content.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start == -1 or end <= start:
            raise ValueError("Sales Coach did not return valid JSON.")
        result = json.loads(cleaned[start:end + 1])

    if not isinstance(result, dict):
        raise ValueError("Sales Coach response must be a JSON object.")
    return result


def _normalise_call_number(value: Any):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _quote_exists(quote: str, transcripts_by_call: Dict[int, str]) -> bool:
    quote = _safe_value(quote)
    if not quote:
        return False
    normalized_quote = " ".join(quote.split()).casefold()
    if not normalized_quote:
        return False

    for transcript in transcripts_by_call.values():
        normalized_transcript = " ".join(transcript.split()).casefold()
        if normalized_quote in normalized_transcript:
            return True
    return False


def _verified_evidence(item: Any, transcripts_by_call: Dict[int, str]) -> Dict[str, Any]:
    if not isinstance(item, dict):
        return {"verified": False, "quote": "", "call_number": None}
    quote = _safe_value(item.get("quote") or item.get("evidence_quote"))
    call_number = _normalise_call_number(item.get("call_number"))
    if not quote or not _quote_exists(quote, transcripts_by_call):
        return {"verified": False, "quote": "", "call_number": None}
    if call_number is not None:
        if not _quote_exists(quote, {call_number: transcripts_by_call.get(call_number, "")}):
            return {"verified": False, "quote": "", "call_number": None}
    else:
        for number, transcript in transcripts_by_call.items():
            if _quote_exists(quote, {number: transcript}):
                call_number = number
                break
    return {"verified": call_number is not None, "quote": quote if call_number is not None else "", "call_number": call_number}


def _normalise_pointer_list(value: Any, transcripts_by_call: Dict[int, str]) -> List[Dict[str, Any]]:
    """Keep only concise coaching points with a verifiable quote; never pad with filler."""
    raw_items = value if isinstance(value, list) else []
    output = []
    seen = set()
    for raw in raw_items:
        if not isinstance(raw, dict):
            continue
        point = _safe_value(raw.get("point"))
        evidence = _verified_evidence(raw, transcripts_by_call)
        if not point or not evidence["verified"]:
            continue
        # Remove generic filler or explicit no-evidence statements even if a quote was attached.
        lowered = point.casefold()
        if any(term in lowered for term in (
            "not enough recorded evidence", "no evidence available", "insufficient evidence",
            "build rapport", "understand customer needs", "follow up effectively",
        )):
            continue
        # Avoid repeating the same advice in slightly different wording.
        dedupe_key = " ".join(point.casefold().split())
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        output.append({
            "point": point,
            "evidence_quote": evidence["quote"],
            "call_number": evidence["call_number"],
            "evidence_verified": True,
        })
        if len(output) == 3:
            break
    return output


def _normalise_level(value: Any) -> int:
    try:
        return max(0, min(3, int(value)))
    except (TypeError, ValueError):
        return 0


def _calculate_closing_score(signals: Dict[str, Any], transcripts_by_call: Dict[int, str]) -> Dict[str, Any]:
    normalized = {}
    score = 0.0
    for key, weight in CLOSING_SIGNAL_WEIGHTS.items():
        raw = signals.get(key) or {}
        level = _normalise_level(raw.get("level", 0)) if isinstance(raw, dict) else 0
        evidence = _verified_evidence(raw, transcripts_by_call)
        if not evidence["verified"]:
            level = 0
        points = weight * EVIDENCE_LEVEL_FRACTIONS[level]
        score += points
        normalized[key] = {**evidence, "level": level, "max_points": weight, "points": round(points, 1)}
    return {"score": int(round(score)), "signals": normalized}


def _normalise_output(result: Dict[str, Any], calls: List[Any]) -> Dict[str, Any]:
    transcripts_by_call = {}
    for call in calls:
        number = _normalise_call_number(getattr(call, "call_number", None))
        if number is not None:
            transcripts_by_call[number] = _safe_value(getattr(call, "transcript", ""))

    calculated = _calculate_closing_score(result.get("closing_signals") or {}, transcripts_by_call)

    return {
        "closing_score": calculated,
        "what_you_did_well": _normalise_pointer_list(
            result.get("what_you_did_well"), transcripts_by_call
        ),
        "what_you_didnt_do_well": _normalise_pointer_list(
            result.get("what_you_didnt_do_well"), transcripts_by_call
        ),
        "what_to_do_now": _normalise_pointer_list(
            result.get("what_to_do_now"), transcripts_by_call
        ),
    }


def coach_sales_conversation(
    lead,
    calls: List[Any],
    max_rag_results: int = 10,
    salesperson_name: str = DEFAULT_SALESPERSON_NAME,
) -> Dict[str, Any]:
    if not calls:
        raise ValueError("No calls were provided for sales coaching.")

    usable_calls = [
        c for c in calls if _safe_value(getattr(c, "transcript", ""))
    ]
    if not usable_calls:
        raise ValueError("No transcribed calls are available for sales coaching.")

    usable_calls.sort(
        key=lambda c: getattr(c, "call_number", None)
        if getattr(c, "call_number", None) is not None
        else 0
    )

    history = _build_call_history(usable_calls)
    journey_hint = "\n".join([
        _safe_value(getattr(lead, "notes", "")),
        _safe_value(getattr(lead, "ai_summary", "")),
        _safe_value(getattr(lead, "product", "")),
        _safe_value(getattr(lead, "quantity", "")),
    ]).strip()

    rag_context = _build_rag_context(
        history[-1].get("transcript", ""),
        journey_hint,
        max_rag_results,
    )

    system_prompt, user_prompt = _build_prompt(
        lead,
        usable_calls,
        salesperson_name,
        rag_context,
    )

    response = client.chat.completions.create(
        model=MODEL_NAME,
        temperature=0.0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    content = response.choices[0].message.content
    result = _extract_model_json(content)
    normalized = _normalise_output(result, usable_calls)

    normalized["_meta"] = {
        "salesperson": salesperson_name,
        "calls_considered": len(usable_calls),
        "latest_call_number": getattr(usable_calls[-1], "call_number", None),
        "rag_results_used": max_rag_results,
        "model": MODEL_NAME,
        "evidence_policy": "display only points with a transcript-verifiable quote; unsupported points are dropped; transcript evidence does not automatically prove an interpretation",
    }

    return normalized
