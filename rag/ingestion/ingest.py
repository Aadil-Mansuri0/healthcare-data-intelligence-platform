"""
RAG Ingestion Pipeline
Loads knowledge base documents + Snowflake schema metadata, chunks them,
and upserts embeddings into the appropriate ChromaDB collection.

Run standalone: python rag/ingestion/ingest.py --target knowledge
Run standalone: python rag/ingestion/ingest.py --target schema
Can also be triggered from Airflow as a periodic refresh task.
"""

import argparse
import logging
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
from rag.vector_store.store import get_knowledge_store, get_schema_store
from rag.knowledge_base.documents import KNOWLEDGE_DOCUMENTS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RAGIngestion")


def chunk_text(text: str, max_words: int = 200, overlap: int = 30) -> list[str]:
    """
    Simple sliding-window word-based chunker with overlap, so context isn't
    severed mid-thought at chunk boundaries. Good enough for our short KB docs;
    for large PDFs swap in a recursive character/sentence-aware splitter.
    """
    words = text.split()
    if len(words) <= max_words:
        return [text]

    chunks = []
    start = 0
    while start < len(words):
        end = min(start + max_words, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start = end - overlap
    return chunks


def ingest_knowledge_base():
    """Ingest domain-knowledge documents into the knowledge vector store."""
    store = get_knowledge_store()
    store.reset_collection()  # clean re-ingest for reproducibility
    store = get_knowledge_store()

    ids, docs, metas = [], [], []
    for entry in KNOWLEDGE_DOCUMENTS:
        chunks = chunk_text(entry["text"])
        for i, chunk in enumerate(chunks):
            ids.append(f"{entry['id']}_chunk{i}")
            docs.append(chunk)
            metas.append({"category": entry["category"], "source_id": entry["id"]})

    store.upsert(ids=ids, documents=docs, metadatas=metas)
    logger.info(f"✅ Knowledge base ingested: {len(ids)} chunks from {len(KNOWLEDGE_DOCUMENTS)} source docs")
    logger.info(f"   Collection size: {store.count()}")


SCHEMA_DOCS = [
    {
        "table": "GOLD_SCHEMA.DRUG_SUMMARY",
        "text": (
            "DRUG_SUMMARY contains yearly aggregated metrics per drug (gnrc_name, brnd_name). "
            "Columns: total_claims (sum of prescription claims), total_cost_usd (total dollar "
            "spend), total_beneficiaries, avg_cost_per_claim, unique_prescribers, is_generic "
            "(boolean), cost_rank (1 = most expensive drug that year). Use this table for "
            "questions about specific drugs, drug costs, generic vs brand comparisons, and "
            "top/most expensive drug rankings."
        ),
    },
    {
        "table": "GOLD_SCHEMA.PRESCRIBER_SUMMARY",
        "text": (
            "PRESCRIBER_SUMMARY contains yearly aggregated metrics per prescriber (identified "
            "by prscrbr_npi). Columns include prscrbr_last_org_name, prscrbr_state_abrvtn, "
            "prscrbr_type (specialty), total_claims, total_cost_usd, unique_drugs_prescribed, "
            "generic_rate (percentage), state_rank. Use this table for questions about "
            "individual prescribers, specialties, or prescriber-level rankings within a state."
        ),
    },
    {
        "table": "GOLD_SCHEMA.STATE_KPI",
        "text": (
            "STATE_KPI contains yearly aggregated metrics per US state (state_abrvtn). "
            "Columns include total_claims, total_cost_usd, total_beneficiaries, "
            "total_prescribers, cost_per_beneficiary, pain_specialty_claims (opioid proxy), "
            "national_rank. Use this table for questions comparing states, regional spend "
            "patterns, or geographic opioid/pain-management prescribing trends."
        ),
    },
]


def ingest_schema_docs():
    """Ingest table/column descriptions to ground NL2SQL retrieval."""
    store = get_schema_store()
    store.reset_collection()
    store = get_schema_store()

    ids = [f"schema_{i}" for i in range(len(SCHEMA_DOCS))]
    docs = [d["text"] for d in SCHEMA_DOCS]
    metas = [{"table": d["table"]} for d in SCHEMA_DOCS]

    store.upsert(ids=ids, documents=docs, metadatas=metas)
    logger.info(f"✅ Schema docs ingested: {len(ids)} table descriptions")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", choices=["knowledge", "schema", "all"], default="all")
    args = parser.parse_args()

    if args.target in ("knowledge", "all"):
        ingest_knowledge_base()
    if args.target in ("schema", "all"):
        ingest_schema_docs()


if __name__ == "__main__":
    main()
