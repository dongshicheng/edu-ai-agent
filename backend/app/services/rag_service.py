from __future__ import annotations

import os
import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from app.config import settings

_embedding_model: SentenceTransformer | None = None
_chroma_client: chromadb.PersistentClient | None = None


def get_embedding_model() -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer(
            settings.embedding_model, device=settings.embedding_device
        )
    return _embedding_model


def get_chroma_client() -> chromadb.PersistentClient:
    global _chroma_client
    if _chroma_client is None:
        os.makedirs(settings.chroma_persist_dir, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir
        )
    return _chroma_client


def get_or_create_collection(name: str = "default") -> chromadb.Collection:
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
    )


def embed_texts(texts: list[str]) -> list[list[float]]:
    model = get_embedding_model()
    embeddings = model.encode(texts, normalize_embeddings=True)
    return embeddings.tolist()


def ingest_document(
    text: str,
    metadata: dict | None = None,
    collection_name: str = "default",
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> int:
    """Split text into chunks, embed, and store in ChromaDB. Returns chunk count."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?", " ", ""],
    )
    chunks = splitter.split_text(text)
    if not chunks:
        return 0

    collection = get_or_create_collection(collection_name)
    embeddings = embed_texts(chunks)

    ids = [f"{collection_name}_{collection.count() + i}" for i in range(len(chunks))]
    metadatas = [metadata or {} for _ in chunks]

    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=chunks,
        metadatas=metadatas,
    )
    return len(chunks)


def search(
    query: str,
    top_k: int = 5,
    collection_name: str = "default",
    where: dict | None = None,
) -> list[dict]:
    """Semantic search. Returns list of {content, score, metadata}."""
    collection = get_or_create_collection(collection_name)
    if collection.count() == 0:
        return []

    query_embedding = embed_texts([query])[0]

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, collection.count()),
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    output = []
    if results["documents"] and results["documents"][0]:
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            score = 1 - dist  # cosine distance to similarity
            output.append({
                "content": doc,
                "score": round(score, 4),
                "metadata": meta or {},
            })
    return output


def list_collections() -> list[dict]:
    client = get_chroma_client()
    collections = client.list_collections()
    return [
        {"name": c.name, "count": c.count()}
        for c in collections
    ]


def delete_collection(name: str) -> bool:
    client = get_chroma_client()
    try:
        client.delete_collection(name)
        return True
    except Exception:
        return False
