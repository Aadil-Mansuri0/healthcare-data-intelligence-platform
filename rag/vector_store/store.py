"""
Vector Store — ChromaDB Wrapper
Persistent, local vector database for RAG. Stores embeddings for:
  1. Domain knowledge docs (drug formulary notes, CMS policy, ICD-10 context)
  2. Historical NL2SQL query→SQL pairs (few-shot retrieval for better SQL generation)
  3. Schema documentation chunks

Why ChromaDB: open-source, embeddable (no separate server needed for dev),
production-swappable for Pinecone/Weaviate/pgvector without changing the
retriever interface below.
"""

import os
import logging
import chromadb
from chromadb.utils import embedding_functions

logger = logging.getLogger("VectorStore")

CHROMA_PERSIST_DIR = os.environ.get("CHROMA_PERSIST_DIR", "./rag/vector_store/chroma_data")

_openai_ef = embedding_functions.OpenAIEmbeddingFunction(
    api_key=os.environ.get("OPENAI_API_KEY", ""),
    model_name="text-embedding-3-small",  # 1536-dim, cheap, strong retrieval quality
)


class VectorStore:
    """Thin wrapper around a persistent Chroma collection with a stable interface."""

    def __init__(self, collection_name: str, persist_dir: str = CHROMA_PERSIST_DIR):
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=_openai_ef,
            metadata={"hnsw:space": "cosine"},
        )
        self.collection_name = collection_name
        logger.info(f"VectorStore ready: collection='{collection_name}' @ {persist_dir}")

    def upsert(self, ids: list[str], documents: list[str], metadatas: list[dict] | None = None):
        """Add or update documents. Embeddings are computed automatically via embedding_function."""
        self.collection.upsert(ids=ids, documents=documents, metadatas=metadatas or [{}] * len(ids))
        logger.info(f"Upserted {len(ids)} docs into '{self.collection_name}'")

    def query(self, query_text: str, top_k: int = 5, where: dict | None = None) -> list[dict]:
        """Semantic search — returns top_k most similar documents with distance scores."""
        results = self.collection.query(
            query_texts=[query_text],
            n_results=top_k,
            where=where,
        )
        hits = []
        if results["ids"] and results["ids"][0]:
            for i in range(len(results["ids"][0])):
                hits.append({
                    "id": results["ids"][0][i],
                    "document": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i],
                    "similarity": round(1 - results["distances"][0][i], 4),  # cosine sim
                })
        return hits

    def delete(self, ids: list[str]):
        self.collection.delete(ids=ids)

    def count(self) -> int:
        return self.collection.count()

    def reset_collection(self):
        """Dangerous — wipes the collection. Used only in ingestion re-runs."""
        self.client.delete_collection(self.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name, embedding_function=_openai_ef,
            metadata={"hnsw:space": "cosine"},
        )


# ─── Named store singletons (one collection per knowledge domain) ─────────────
def get_knowledge_store() -> VectorStore:
    """Domain knowledge: drug formulary notes, CMS policy excerpts, ICD-10 context."""
    return VectorStore("healthcare_knowledge_base")


def get_query_history_store() -> VectorStore:
    """Historical NL question → generated SQL pairs, for few-shot retrieval."""
    return VectorStore("nl2sql_query_history")


def get_schema_store() -> VectorStore:
    """Chunked schema documentation (table/column descriptions) for grounding."""
    return VectorStore("schema_documentation")
