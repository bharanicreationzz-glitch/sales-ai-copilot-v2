import json
import re
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer


# ============================================================
# CONFIG
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
KB_DIR = BASE_DIR / "knowledge_base"

CHUNKS_FILE = KB_DIR / "kb_chunks.jsonl"
EMBEDDINGS_FILE = KB_DIR / "kb_embeddings.npy"
INDEX_FILE = KB_DIR / "kb_index.json"

EMBEDDING_MODEL = "all-MiniLM-L6-v2"


# ============================================================
# SOURCE / SECTION MAPPING
# ============================================================

# The current KB has 59 chunks.
# These mappings are intentionally based on the actual KB
# structure rather than loose keyword matching.

TOPIC_TYPE_MAP = {

    # --------------------------------------------------------
    # Company
    # --------------------------------------------------------

    "Company & Trust Guidance": "company_usp",

    # --------------------------------------------------------
    # Decision Delay
    # --------------------------------------------------------

    "Decision Delay Handling": "decision_delay",
    "Principle": "decision_delay",
    "Common delay signals": "decision_delay",
    "Identify the barrier": "decision_delay",
    "Reduce decision friction": "decision_delay",
    "Ethical urgency": "decision_delay",
    "Decision-maker": "decision_delay",
    "Multi-call decision delay": "decision_delay",
    "Repeated objection": "decision_delay",

    # --------------------------------------------------------
    # Executive Communication
    # --------------------------------------------------------

    "Executive Communication Coaching": "executive_communication",
    "Strong speech": "executive_communication",
    "Weak patterns": "executive_communication",
    "Better alternatives": "executive_communication",
    "Confidence rule": "executive_communication",
    "Response structure": "executive_communication",
    "Executive communication": "executive_communication",

    # --------------------------------------------------------
    # Follow-up
    # --------------------------------------------------------

    "Follow-Up Guidance": "follow_up",
    "Rule": "follow_up",
    "After price discussion": "follow_up",
    "After product comparison": "follow_up",
    "After decision delay": "follow_up",
    "Follow-up objective": "follow_up",
    "Next-step rule": "follow_up",
    "Lead potential": "follow_up",
    "Closing": "follow_up",
    "Avoid": "follow_up",

    # --------------------------------------------------------
    # Objection Handling
    # --------------------------------------------------------

    "Objection Handling": "objection_handling",
    "Master framework": "objection_handling",
    "\"I'm not interested\"": "objection_handling",
    "\"Price is high\"": "objection_handling",
    "\"I'll think about it\"": "objection_handling",
    "\"I'll call you later\"": "objection_handling",
    "\"Not now\"": "objection_handling",
    "\"I need more time\"": "objection_handling",
    "\"I need to discuss with my husband/wife\"": "objection_handling",
    "\"I need to ask my contractor\"": "objection_handling",
    "\"I'm comparing with another supplier\"": "objection_handling",
    "\"Competitor is cheaper\"": "objection_handling",
    "Quality concern": "objection_handling",
    "Installation concern": "objection_handling",
    "Trust concern": "objection_handling",
    "Objection classification": "objection_handling",

    # --------------------------------------------------------
    # Pricing
    # --------------------------------------------------------

    "Pricing Reference": "pricing_reference",

    # --------------------------------------------------------
    # Qualification
    # --------------------------------------------------------

    "Customer Qualification": "qualification",
    "Required discovery": "qualification",
    "Customer category": "qualification",

    # --------------------------------------------------------
    # Sales Guidance
    # --------------------------------------------------------

    "Sales Guidance": "sales_guidance",
    "Core sales flow": "sales_guidance",
    "Discovery": "sales_guidance",
    "Discovery before pitching": "sales_guidance",
    "Value-based selling": "sales_guidance",
    "Recommendation": "sales_guidance",

    # --------------------------------------------------------
    # Products
    # --------------------------------------------------------

    "Product: Antiqo Fence": "product",
    "Product: JF Checks Mesh": "product",
    "Product: JF Lato Fence": "product",
    "Product: JF PolyHex Mesh": "product",
    "Product: JF Privezy Grass Wall": "product",
    "Product: JF Trinity Poles": "product",
}


# ============================================================
# PRODUCT MAP
# ============================================================

PRODUCT_TOPIC_MAP = {

    "Product: Antiqo Fence": "Antiqo Fence",
    "Product: JF Checks Mesh": "Checks Mesh",
    "Product: JF Lato Fence": "Lato Fence",
    "Product: JF PolyHex Mesh": "Polyhex Mesh",
    "Product: JF Privezy Grass Wall": "Privezy Grass Wall",
    "Product: JF Trinity Poles": "Trinity Pole",
}


# ============================================================
# SOURCE FILE MAP
# ============================================================

TYPE_SOURCE_MAP = {

    "company_usp": "company_usp.md",
    "decision_delay": "decision_delay.md",
    "executive_communication": "executive_communication.md",
    "follow_up": "follow_up.md",
    "objection_handling": "objection_handling.md",
    "pricing_reference": "pricing_reference.md",
    "qualification": "qualification.md",
    "sales_guidance": "sales_guidance.md",
}


PRODUCT_SOURCE_MAP = {

    "Antiqo Fence": "product_antiqo_fence.md",
    "Checks Mesh": "product_checks_mesh.md",
    "Lato Fence": "product_lato_fence.md",
    "Polyhex Mesh": "product_polyhex_mesh.md",
    "Privezy Grass Wall": "product_privezy_grass_wall.md",
    "Trinity Pole": "product_trinity_poles.md",
}


# ============================================================
# HELPERS
# ============================================================

def clean_topic(topic):
    if not topic:
        return None

    topic = topic.strip()

    topic = re.sub(
        r"[*_`]",
        "",
        topic
    )

    return topic


def detect_topic(text):
    """
    Extract the last Markdown heading from the chunk.
    """

    headings = re.findall(
        r"(?m)^#{1,3}\s+(.+?)\s*$",
        text
    )

    if not headings:
        return None

    return clean_topic(
        headings[-1]
    )


def detect_knowledge_type(topic):
    """
    Determine knowledge type from the actual KB topic.
    """

    if not topic:
        return None

    if topic in TOPIC_TYPE_MAP:
        return TOPIC_TYPE_MAP[topic]

    return None


def detect_product(topic, knowledge_type):
    """
    Only product-specific chunks get product_name.

    Sales guidance chunks mentioning a product do NOT
    automatically become product knowledge.
    """

    if knowledge_type != "product":
        return None

    return PRODUCT_TOPIC_MAP.get(topic)


def detect_source_file(
    knowledge_type,
    product_name
):
    """
    Assign the source file deterministically.
    """

    if knowledge_type == "product":
        if product_name:
            return PRODUCT_SOURCE_MAP.get(
                product_name
            )

        return None

    return TYPE_SOURCE_MAP.get(
        knowledge_type
    )


# ============================================================
# OBJECTION TYPE
# ============================================================

OBJECTION_TOPIC_MAP = {

    "\"I'm not interested\"": "NOT_INTERESTED",
    "\"Price is high\"": "PRICE",
    "\"I'll think about it\"": "TIMING",
    "\"I'll call you later\"": "TIMING",
    "\"Not now\"": "TIMING",
    "\"I need more time\"": "TIMING",

    "\"I need to discuss with my husband/wife\"":
        "DECISION_MAKER",

    "\"I need to ask my contractor\"":
        "INSTALLATION",

    "\"I'm comparing with another supplier\"":
        "COMPETITOR",

    "\"Competitor is cheaper\"":
        "COMPETITOR",

    "Quality concern":
        "QUALITY",

    "Installation concern":
        "INSTALLATION",

    "Trust concern":
        "TRUST",
}


def detect_objection_type(
    topic,
    knowledge_type
):
    """
    Objection type comes ONLY from explicit objection
    topics.

    This prevents words like 'competitor', 'price',
    or 'installation' inside unrelated chunks from
    creating false classifications.
    """

    if knowledge_type != "objection_handling":
        return None

    return OBJECTION_TOPIC_MAP.get(
        topic
    )


# ============================================================
# SALES STAGE
# ============================================================

def detect_sales_stage(
    topic,
    knowledge_type,
    objection_type
):
    """
    Conservative stage classification.
    """

    # --------------------------------------------------------
    # Objections
    # --------------------------------------------------------

    if objection_type == "COMPETITOR":
        return "Comparison"

    if objection_type == "PRICE":
        return "Price Evaluation"

    if objection_type == "TIMING":
        if topic == "\"I'll call you later\"":
            return "Follow-up Pending"

        if topic in {
            "\"Not now\"",
            "\"I need more time\"",
        }:
            return "Decision Pending"

        if topic == "\"I'll think about it\"":
            return "Decision Pending"

    if objection_type == "DECISION_MAKER":
        return "Decision Pending"

    if objection_type == "INSTALLATION":
        return None

    # --------------------------------------------------------
    # Decision delay
    # --------------------------------------------------------

    if knowledge_type == "decision_delay":
        if topic in {
            "Common delay signals",
            "Multi-call decision delay",
            "Repeated objection",
        }:
            return "Decision Pending"

        if topic == "Decision-maker":
            return "Decision Pending"

    # --------------------------------------------------------
    # Qualification
    # --------------------------------------------------------

    if knowledge_type == "qualification":
        return "Requirement Discovery"

    # --------------------------------------------------------
    # Pricing
    # --------------------------------------------------------

    if knowledge_type == "pricing_reference":
        return "Price Evaluation"

    # --------------------------------------------------------
    # Follow-up
    # --------------------------------------------------------

    if knowledge_type == "follow_up":

        if topic in {
            "Follow-Up Guidance",
            "Rule",
            "Next-step rule",
            "Follow-up objective",
            "Lead potential",
            "Closing",
            "Avoid",
        }:
            return "Follow-up Pending"

        if topic == "After price discussion":
            return "Price Evaluation"

        if topic == "After product comparison":
            return "Comparison"

        if topic == "After decision delay":
            return "Decision Pending"

    # --------------------------------------------------------
    # Sales guidance
    # --------------------------------------------------------

    if knowledge_type == "sales_guidance":

        if topic in {
            "Discovery",
            "Discovery before pitching",
        }:
            return "Requirement Discovery"

        if topic == "Recommendation":
            return "Requirement Discovery"

    return None


# ============================================================
# CHUNK ID
# ============================================================

def create_chunk_id(
    topic,
    source_file,
    index
):

    if topic:
        base = topic

    elif source_file:
        base = Path(
            source_file
        ).stem

    else:
        base = f"chunk_{index}"

    base = base.lower()

    base = re.sub(
        r"[^a-z0-9]+",
        "_",
        base
    )

    base = re.sub(
        r"_+",
        "_",
        base
    )

    base = base.strip("_")

    return f"{base}_{index}"


# ============================================================
# METADATA
# ============================================================

def extract_metadata(
    chunk,
    index
):

    text = chunk.get(
        "text",
        ""
    ).strip()

    topic = detect_topic(
        text
    )

    knowledge_type = detect_knowledge_type(
        topic
    )

    product_name = detect_product(
        topic,
        knowledge_type
    )

    source_file = detect_source_file(
        knowledge_type,
        product_name
    )

    objection_type = detect_objection_type(
        topic,
        knowledge_type
    )

    sales_stage = detect_sales_stage(
        topic,
        knowledge_type,
        objection_type
    )

    chunk_id = create_chunk_id(
        topic,
        source_file,
        index
    )

    return {
        "index": index,
        "chunk_id": chunk_id,
        "source_file": source_file,
        "knowledge_type": knowledge_type,
        "topic": topic,
        "product_name": product_name,
        "objection_type": objection_type,
        "sales_stage": sales_stage,
        "text": text,
    }


# ============================================================
# LOAD CHUNKS
# ============================================================

def load_chunks():

    chunks = []

    with open(
        CHUNKS_FILE,
        "r",
        encoding="utf-8"
    ) as f:

        for line in f:

            line = line.strip()

            if not line:
                continue

            chunks.append(
                json.loads(line)
            )

    return chunks


# ============================================================
# DISTRIBUTION
# ============================================================

def print_distribution(
    index,
    field,
    title
):

    print(
        f"\n{title}:"
    )

    counts = {}

    for item in index:

        value = (
            item.get(field)
            or "None"
        )

        counts[value] = (
            counts.get(value, 0)
            + 1
        )

    for key, count in sorted(
        counts.items()
    ):

        print(
            f"  {key}: {count}"
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print(
        "JUSTFENCE KNOWLEDGE BASE INGESTION V4"
    )
    print("=" * 60)

    print(
        "\nKB directory:"
    )

    print(KB_DIR)

    # --------------------------------------------------------
    # Load
    # --------------------------------------------------------

    chunks = load_chunks()

    print(
        f"\nLoaded {len(chunks)} KB chunks."
    )

    if not chunks:

        print(
            "\nERROR: No KB chunks found."
        )

        return

    # --------------------------------------------------------
    # Metadata
    # --------------------------------------------------------

    print(
        "\nBuilding KB metadata..."
    )

    index = []

    for i, chunk in enumerate(
        chunks
    ):

        metadata = extract_metadata(
            chunk,
            i
        )

        index.append(
            metadata
        )

    # --------------------------------------------------------
    # Example
    # --------------------------------------------------------

    print(
        "\nExample metadata:"
    )

    print(
        json.dumps(
            index[0],
            indent=2,
            ensure_ascii=False
        )
    )

    # --------------------------------------------------------
    # Model
    # --------------------------------------------------------

    print(
        f"\nLoading embedding model: "
        f"{EMBEDDING_MODEL}"
    )

    model = SentenceTransformer(
        EMBEDDING_MODEL
    )

    # --------------------------------------------------------
    # Embeddings
    # --------------------------------------------------------

    texts = [
        item["text"]
        for item in index
    ]

    print(
        f"\nCreating embeddings for "
        f"{len(texts)} KB chunks..."
    )

    embeddings = model.encode(
        texts,
        batch_size=32,
        show_progress_bar=True,
        normalize_embeddings=True
    )

    embeddings = np.asarray(
        embeddings,
        dtype=np.float32
    )

    print(
        f"\nEmbedding shape: "
        f"{embeddings.shape}"
    )

    # --------------------------------------------------------
    # Save embeddings
    # --------------------------------------------------------

    np.save(
        EMBEDDINGS_FILE,
        embeddings
    )

    # --------------------------------------------------------
    # Save index
    # --------------------------------------------------------

    with open(
        INDEX_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            index,
            f,
            indent=2,
            ensure_ascii=False
        )

    # --------------------------------------------------------
    # Results
    # --------------------------------------------------------

    print(
        "\nSUCCESS!"
    )

    print(
        "\nEmbeddings saved to:"
    )

    print(
        EMBEDDINGS_FILE
    )

    print(
        "\nIndex saved to:"
    )

    print(
        INDEX_FILE
    )

    # --------------------------------------------------------
    # Distribution
    # --------------------------------------------------------

    print_distribution(
        index,
        "knowledge_type",
        "Knowledge type distribution"
    )

    print_distribution(
        index,
        "objection_type",
        "Objection type distribution"
    )

    print_distribution(
        index,
        "sales_stage",
        "Sales stage distribution"
    )

    # --------------------------------------------------------
    # Product check
    # --------------------------------------------------------

    print(
        "\nProduct chunks:"
    )

    for item in index:

        if item["knowledge_type"] == "product":

            print(
                f"  {item['index']} | "
                f"{item['topic']} | "
                f"{item['product_name']} | "
                f"{item['source_file']}"
            )

    print(
        "\nKnowledge base is ready "
        "for RAG retrieval."
    )

    print("=" * 60)


if __name__ == "__main__":
    main()