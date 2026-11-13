from pathlib import Path
import json

import numpy as np
from sentence_transformers import SentenceTransformer


# ---------------------------------------------------------
# PATHS
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[1]
KB_DIR = BASE_DIR / "knowledge_base"

EMBEDDINGS_FILE = KB_DIR / "kb_embeddings.npy"
INDEX_FILE = KB_DIR / "kb_index.json"


# ---------------------------------------------------------
# EMBEDDING MODEL
# ---------------------------------------------------------

MODEL_NAME = "all-MiniLM-L6-v2"

_model = None
_embeddings = None
_index = None


# ---------------------------------------------------------
# LOAD MODEL
# ---------------------------------------------------------

def get_model():
    global _model

    if _model is None:
        print(f"Loading embedding model: {MODEL_NAME}")
        _model = SentenceTransformer(MODEL_NAME)

    return _model


# ---------------------------------------------------------
# LOAD KB INDEX
# ---------------------------------------------------------

def load_knowledge_base():
    global _embeddings
    global _index

    if _embeddings is None:
        if not EMBEDDINGS_FILE.exists():
            raise FileNotFoundError(
                f"Embeddings file not found:\n{EMBEDDINGS_FILE}\n\n"
                "Run ingest_kb.py first."
            )

        _embeddings = np.load(EMBEDDINGS_FILE)

    if _index is None:
        if not INDEX_FILE.exists():
            raise FileNotFoundError(
                f"KB index file not found:\n{INDEX_FILE}\n\n"
                "Run ingest_kb.py first."
            )

        with open(INDEX_FILE, "r", encoding="utf-8") as file:
            _index = json.load(file)

    return _embeddings, _index


# ---------------------------------------------------------
# RETRIEVE KNOWLEDGE
# ---------------------------------------------------------

def retrieve_knowledge(
    query: str,
    top_k: int = 5,
    knowledge_type: str | None = None,
    product_name: str | None = None,
    objection_type: str | None = None,
    sales_stage: str | None = None
):
    """
    Retrieve the most relevant KB chunks for a query.

    Optional filters:
    - knowledge_type
    - product_name
    - objection_type
    - sales_stage
    """

    if not query or not query.strip():
        return []

    embeddings, index = load_knowledge_base()

    model = get_model()

    # -----------------------------------------------------
    # CREATE QUERY EMBEDDING
    # -----------------------------------------------------

    query_embedding = model.encode(
        [query],
        normalize_embeddings=True
    )[0]

    query_embedding = np.asarray(
        query_embedding,
        dtype=np.float32
    )

    # -----------------------------------------------------
    # FIND CANDIDATES
    # -----------------------------------------------------

    candidate_indices = []

    for item in index:

        if knowledge_type:
            if item.get("knowledge_type") != knowledge_type:
                continue

        if product_name:
            if item.get("product_name") != product_name:
                continue

        if objection_type:
            if item.get("objection_type") != objection_type:
                continue

        if sales_stage:
            if item.get("sales_stage") != sales_stage:
                continue

        candidate_indices.append(
            item["index"]
        )

    if not candidate_indices:
        return []

    # -----------------------------------------------------
    # COSINE SIMILARITY
    # -----------------------------------------------------

    candidate_embeddings = embeddings[candidate_indices]

    scores = candidate_embeddings @ query_embedding

    # -----------------------------------------------------
    # SORT BY RELEVANCE
    # -----------------------------------------------------

    ranked_positions = np.argsort(
        scores
    )[::-1]

    ranked_positions = ranked_positions[:top_k]

    # -----------------------------------------------------
    # BUILD RESULTS
    # -----------------------------------------------------

    results = []

    for position in ranked_positions:

        actual_index = candidate_indices[position]

        item = index[actual_index]

        results.append({
            "score": round(
                float(scores[position]),
                4
            ),
            "chunk_id": item.get("chunk_id"),
            "source_file": item.get("source_file"),
            "knowledge_type": item.get("knowledge_type"),
            "topic": item.get("topic"),
            "product_name": item.get("product_name"),
            "objection_type": item.get("objection_type"),
            "sales_stage": item.get("sales_stage"),
            "text": item.get("text")
        })

    return results


# ---------------------------------------------------------
# SIMPLE TEST FUNCTION
# ---------------------------------------------------------

def search_sales_knowledge(
    query: str,
    top_k: int = 5
):
    """
    Convenience function for sales-related retrieval.
    """

    return retrieve_knowledge(
        query=query,
        top_k=top_k
    )


# ---------------------------------------------------------
# MAIN TEST
# ---------------------------------------------------------

if __name__ == "__main__":

    test_query = (
        "How should a salesperson communicate confidently and professionally with an executive customer?"
    )

    print("\n" + "=" * 60)
    print("JUSTFENCE RAG TEST")
    print("=" * 60)

    print(f"\nQuery:\n{test_query}")

    results = retrieve_knowledge(
        query=test_query,
        top_k=5
    )

    print(
        f"\nRetrieved {len(results)} results:\n"
    )

    for number, result in enumerate(
        results,
        start=1
    ):
        print("-" * 60)
        print(f"Result #{number}")
        print(f"Score: {result['score']}")
        print(f"Source: {result['source_file']}")
        print(f"Topic: {result['topic']}")
        print(
            f"Knowledge Type: "
            f"{result['knowledge_type']}"
        )
        print(
            f"Objection Type: "
            f"{result['objection_type']}"
        )
        print("\nText:")
        print(result["text"])

    print("\n" + "=" * 60)
    print("RAG TEST COMPLETE")
    print("=" * 60)