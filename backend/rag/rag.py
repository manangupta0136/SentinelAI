"""
RAG — Retrieval Augmented Generation
--------------------------------------
Ingests runbooks, SOPs, and incident history into Qdrant (in-memory).
Retrieves relevant documents given a failure type.

Uses sentence-transformers for embeddings.
Qdrant runs in-memory — no separate server needed.
"""

import os
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer

DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data"
)

RUNBOOKS_DIR  = os.path.join(DATA_DIR, "runbooks")
SOPS_DIR      = os.path.join(DATA_DIR, "sops")
INCIDENTS_DIR = os.path.join(DATA_DIR, "incidents")

COLLECTION_NAME = "knowledge_base"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"


class RAGEngine:

    def __init__(self):
        self.client = QdrantClient(":memory:")
        self.model = SentenceTransformer(EMBEDDING_MODEL)
        self._ingested = False

    def _read_files(self, directory: str, doc_type: str) -> list:
        docs = []
        if not os.path.exists(directory):
            return docs
        for fname in os.listdir(directory):
            if fname.endswith(".txt"):
                fpath = os.path.join(directory, fname)
                with open(fpath, "r") as f:
                    content = f.read().strip()
                docs.append({
                    "text": content,
                    "type": doc_type,
                    "filename": fname,
                })
        return docs

    def ingest(self):
        """Load all documents and store embeddings in Qdrant."""
        if self._ingested:
            return

        documents = []
        documents += self._read_files(RUNBOOKS_DIR,  "runbook")
        documents += self._read_files(SOPS_DIR,      "sop")
        documents += self._read_files(INCIDENTS_DIR, "incident")

        if not documents:
            print("[RAG] Warning: No documents found to ingest.")
            return

        texts = [d["text"] for d in documents]
        vectors = self.model.encode(texts).tolist()

        self.client.recreate_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=len(vectors[0]), distance=Distance.COSINE),
        )

        points = [
            PointStruct(id=i, vector=vectors[i], payload=documents[i])
            for i in range(len(documents))
        ]
        self.client.upsert(collection_name=COLLECTION_NAME, points=points)

        self._ingested = True
        print(f"[RAG] Ingested {len(documents)} documents.")

    def retrieve(self, failure: str, top_k: int = 3) -> dict:
        """
        Given a failure type string, retrieve the most relevant documents.
        Returns RAG_OUTPUT dict.
        """
        if not self._ingested:
            self.ingest()

        query_vector = self.model.encode(failure).tolist()

        results = self.client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            limit=top_k,
        )

        runbook = ""
        sop = ""
        incident = ""

        for r in results.points:
            doc_type = r.payload.get("type", "")
            text = r.payload.get("text", "")
            if doc_type == "runbook" and not runbook:
                runbook = text
            elif doc_type == "sop" and not sop:
                sop = text
            elif doc_type == "incident" and not incident:
                incident = text

        return {
            "runbook": runbook,
            "sop": sop,
            "incident": incident,
        }


# Singleton
_rag_engine = None

def get_rag_engine() -> RAGEngine:
    global _rag_engine
    if _rag_engine is None:
        _rag_engine = RAGEngine()
        _rag_engine.ingest()
    return _rag_engine


if __name__ == "__main__":
    rag = get_rag_engine()
    result = rag.retrieve("MPLS Congestion")
    print("Runbook:", result["runbook"][:200])
    print("SOP:", result["sop"][:200])
    print("Incident:", result["incident"][:200])