# JustFence Sales AI Knowledge Base — V1

Purpose:
- Product knowledge
- Sales guidance
- Objection handling
- Decision-delay handling
- Follow-up guidance
- Executive communication coaching
- Qualification rules

Design:
- Product knowledge is separated from sales guidance.
- Each Markdown file is a source document.
- `kb_chunks.jsonl` contains retrieval-ready chunks with metadata.
- Pricing is explicitly marked as reference pricing and should not be treated as a final/current quote without verification.

Recommended retrieval metadata:
- knowledge_type
- topic
- product_name
- objection_type
- sales_stage
- priority
