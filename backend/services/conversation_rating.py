import json
import re

from config import AI_MODEL, OPENAI_API_KEY, OPENAI_BASE_URL
from openai import OpenAI

from services.rag import search_sales_knowledge

ai_client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)


# ============================================================
# SCORING WEIGHTS
# ============================================================

SCORING_WEIGHTS = {
    "opening": 0.05,
    "discovery": 0.15,
    "requirement_qualification": 0.15,
    "product_recommendation": 0.10,
    "objection_handling": 0.20,
    "communication": 0.10,
    "closing": 0.10,
    "next_step": 0.15,
}


# ============================================================
# HELPERS
# ============================================================

def clean_json_response(content):
    """
    Remove Markdown code fences if the model returns JSON
    inside ```json ... ```.
    """

    content = content.strip()

    if content.startswith("```"):
        content = re.sub(
            r"^```(?:json)?\s*",
            "",
            content,
            flags=re.IGNORECASE
        )

        content = re.sub(
            r"\s*```$",
            "",
            content
        )

    return content.strip()


def clamp_score(value):
    """
    Keep every dimension between 0 and 100.
    """

    try:
        value = float(value)
    except (TypeError, ValueError):
        return 0

    return max(
        0,
        min(
            100,
            round(value)
        )
    )


def calculate_overall_score(dimensions):
    """
    Calculate the final score deterministically.

    The LLM does NOT control the final weighted score.
    """

    total = 0

    for dimension, weight in SCORING_WEIGHTS.items():

        score = dimensions.get(
            dimension,
            0
        )

        score = clamp_score(
            score
        )

        total += score * weight

    return round(total)


# ============================================================
# RAG CONTEXT
# ============================================================

def build_rag_context(
    transcript,
    max_results=10
):
    """
    Retrieve relevant JustFence sales knowledge.

    We intentionally search without metadata filters first,
    because the transcript can contain multiple issues:
    discovery + product + price + competitor + closing, etc.
    """

    results = search_sales_knowledge(
        transcript,
        top_k=max_results
    )

    if not results:
        return "", []

    context_parts = []

    for i, item in enumerate(
        results,
        start=1
    ):

        context_parts.append(
            f"""
KNOWLEDGE #{i}

Score: {item.get("score")}
Source: {item.get("source_file")}
Topic: {item.get("topic")}
Knowledge Type: {item.get("knowledge_type")}
Product: {item.get("product_name")}
Objection Type: {item.get("objection_type")}
Sales Stage: {item.get("sales_stage")}

Guidance:
{item.get("text")}
""".strip()
        )

    return (
        "\n\n---\n\n".join(
            context_parts
        ),
        results
    )


# ============================================================
# PROMPT
# ============================================================

def build_rating_prompt(
    transcript,
    rag_context
):

    return f"""
You are a senior AI Sales Coach for JustFence.

Your job is to evaluate the SALESPERSON'S performance
in the conversation using the provided JustFence sales
knowledge as the evaluation standard.

IMPORTANT:

1. Evaluate the salesperson, not the customer.
2. Do not reward the salesperson merely for mentioning
   a product.
3. A recommendation should be based on customer needs.
4. Do not assume missing information was discussed.
5. Do not invent facts that are not in the transcript.
6. Distinguish customer statements from salesperson
   statements.
7. Do not punish the salesperson for not giving information
   that was genuinely unavailable.
8. Confidence does NOT mean pretending to know something.
9. "I'll verify that and confirm" can be strong professional
   communication.
10. Do not recommend fake urgency, pressure, manipulation,
    competitor attacks, unsupported claims or unnecessary
    discounting.
11. If the customer gives a genuine final rejection, respecting
    the rejection is correct.
12. Evaluate the conversation according to the retrieved
    JustFence guidance, not generic sales theory.

============================================================
JUSTFENCE KNOWLEDGE
============================================================

{rag_context}

============================================================
SALES CALL TRANSCRIPT
============================================================

{transcript}

============================================================
EVALUATION FRAMEWORK
============================================================

Score each dimension from 0 to 100.

OPENING
Evaluate:
- Professional opening
- Clear introduction
- Appropriate tone
- Whether the salesperson established the purpose naturally

DISCOVERY
Evaluate:
- Whether the salesperson understood the customer's situation
- Location/site context
- Property/site type
- Purpose
- Relevant customer priorities
- Whether discovery happened before pitching

REQUIREMENT QUALIFICATION
Evaluate:
- Boundary length
- Required height
- Quantity
- Application
- Purpose
- Important missing specifications
- Whether the salesperson separated actual requirement
  from assumptions

PRODUCT RECOMMENDATION
Evaluate:
- Whether the recommended product fits the customer's needs
- Whether the recommendation was based on customer purpose
- Whether benefits were explained in customer terms
- Whether the salesperson avoided unnecessary product dumping
- Whether technical claims were supported

OBJECTION HANDLING
Evaluate:
- Whether objections were identified
- Whether the salesperson diagnosed the real concern
- Whether they clarified before responding
- Whether they handled price/competitor/timing/product/
  quality/trust/installation concerns appropriately
- Whether they avoided immediate discounting
- Whether they avoided criticizing competitors

COMMUNICATION
Evaluate:
- Clarity
- Calmness
- Professionalism
- Directness
- Executive-level communication
- Confidence in known facts
- Honesty about unknown information
- Excessive use of weak language such as:
  "maybe", "I think", "probably", "basically", "I guess"

CLOSING
Evaluate:
- Whether the salesperson confirmed customer understanding
- Whether they checked readiness
- Whether they avoided forcing a decision
- Whether the conversation moved toward a clear decision

NEXT STEP
Evaluate:
- Whether a specific next action was agreed
- Whether responsibility was clear
- Whether timing was clear when appropriate
- Whether follow-up was tailored to the actual conversation
- Whether the salesperson avoided generic repeated follow-ups

============================================================
IMPORTANT SCORING RULE
============================================================

Do not simply give a high score because the salesperson
was polite.

A strong sales conversation should:

UNDERSTAND
→ QUALIFY
→ RECOMMEND
→ EXPLAIN VALUE
→ HANDLE CONCERNS
→ REDUCE DECISION FRICTION
→ CONFIRM NEXT STEP

A conversation with weak discovery, weak objection handling
or no next step should score accordingly.

============================================================
OUTPUT
============================================================

Return ONLY valid JSON.

Use exactly this structure:

{{
  "dimensions": {{
    "opening": 0,
    "discovery": 0,
    "requirement_qualification": 0,
    "product_recommendation": 0,
    "objection_handling": 0,
    "communication": 0,
    "closing": 0,
    "next_step": 0
  }},

  "dimension_reasons": {{
    "opening": "",
    "discovery": "",
    "requirement_qualification": "",
    "product_recommendation": "",
    "objection_handling": "",
    "communication": "",
    "closing": "",
    "next_step": ""
  }},

  "strengths": [],

  "missed_opportunities": [],

  "what_should_have_been_said": [],

  "speech_confidence": {{
    "level": "Low",
    "reason": "",
    "examples": []
  }},

  "customer_objections": [],

  "decision_stage": "",

  "next_best_action": "",

  "overall_assessment": ""
}}

For speech_confidence.level use exactly one of:

"Low"
"Medium"
"High"

For decision_stage use the most appropriate value:

"Initial Contact"
"Requirement Discovery"
"Product Evaluation"
"Price Evaluation"
"Comparison"
"Decision Pending"
"Follow-up Pending"
"Closed - Won"
"Closed - Lost"
"Unknown"

Keep recommendations practical and specific.

Do not invent customer objections.

Do not claim the salesperson missed something if the
transcript does not provide enough evidence to determine it.
"""


# ============================================================
# MAIN RATING FUNCTION
# ============================================================

def rate_conversation(
    transcript,
    max_rag_results=10
):

    if not transcript or not transcript.strip():

        raise ValueError(
            "Transcript cannot be empty."
        )

    transcript = transcript.strip()

    # --------------------------------------------------------
    # RAG
    # --------------------------------------------------------

    rag_context, rag_results = build_rag_context(
        transcript,
        max_results=max_rag_results
    )

    if not rag_context:

        rag_context = (
            "No relevant JustFence knowledge was retrieved."
        )

    # --------------------------------------------------------
    # AI evaluation
    # --------------------------------------------------------

    prompt = build_rating_prompt(
        transcript,
        rag_context
    )

    response = ai_client.chat.completions.create(
        model=AI_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a precise JustFence sales "
                    "conversation evaluator. "
                    "Return only valid JSON."
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

        raise ValueError(
            "AI returned an empty response."
        )

    content = clean_json_response(
        content
    )

    try:

        evaluation = json.loads(
            content
        )

    except json.JSONDecodeError as exc:

        raise ValueError(
            f"AI returned invalid JSON: {exc}\n\n"
            f"Raw response:\n{content}"
        )

    # --------------------------------------------------------
    # Normalize dimensions
    # --------------------------------------------------------

    dimensions = evaluation.get(
        "dimensions",
        {}
    )

    normalized_dimensions = {}

    for dimension in SCORING_WEIGHTS:

        normalized_dimensions[
            dimension
        ] = clamp_score(
            dimensions.get(
                dimension,
                0
            )
        )

    evaluation["dimensions"] = (
        normalized_dimensions
    )

    # --------------------------------------------------------
    # Deterministic overall score
    # --------------------------------------------------------

    evaluation["overall_score"] = (
        calculate_overall_score(
            normalized_dimensions
        )
    )

    # --------------------------------------------------------
    # Ensure expected fields exist
    # --------------------------------------------------------

    evaluation.setdefault(
        "dimension_reasons",
        {}
    )

    evaluation.setdefault(
        "strengths",
        []
    )

    evaluation.setdefault(
        "missed_opportunities",
        []
    )

    evaluation.setdefault(
        "what_should_have_been_said",
        []
    )

    evaluation.setdefault(
        "speech_confidence",
        {
            "level": "Medium",
            "reason": "",
            "examples": []
        }
    )

    evaluation.setdefault(
        "customer_objections",
        []
    )

    evaluation.setdefault(
        "decision_stage",
        "Unknown"
    )

    evaluation.setdefault(
        "next_best_action",
        ""
    )

    evaluation.setdefault(
        "overall_assessment",
        ""
    )

    # --------------------------------------------------------
    # Attach RAG context for debugging
    # --------------------------------------------------------

    evaluation["_rag_context"] = rag_results

    return evaluation


# ============================================================
# TEST TRANSCRIPT
# ============================================================

TEST_TRANSCRIPT = """
Salesperson:
Hello sir, this is from JustFence. We have many fencing
products. We can provide good quality fencing.

Customer:
I need fencing for my farm.

Salesperson:
We have Checks Mesh. It is good for farms.

Customer:
How much is it?

Salesperson:
It depends on the requirement. It may be around this range.

Customer:
I am also checking with another supplier.

Salesperson:
Okay sir. Our product is good quality.

Customer:
I will think about it.

Salesperson:
Okay sir, you can call me later.
"""


# ============================================================
# COMMAND LINE TEST
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print(
        "JUSTFENCE CONVERSATION RATING V3"
    )
    print("=" * 60)

    print(
        "\nRunning conversation rating test..."
    )

    try:

        result = rate_conversation(
            TEST_TRANSCRIPT,
            max_rag_results=10
        )

        print(
            "\n"
            + "=" * 60
        )

        print(
            "CONVERSATION RATING RESULT"
        )

        print(
            "=" * 60
        )

        print(
            json.dumps(
                result,
                indent=2,
                ensure_ascii=False
            )
        )

    except Exception as exc:

        print(
            "\nERROR:"
        )

        print(
            str(exc)
        )

    print(
        "\n"
        + "=" * 60
    )
    