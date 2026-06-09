"""
Módulo de armazenamento e busca no ChromaDB.

ChromaDB roda localmente (sem servidor externo) e persiste os dados em disco.
A coleção usa embeddings pré-computados (não delega ao ChromaDB a geração),
o que mantém controle total sobre o modelo de embedding utilizado.
"""

from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings

from pipeline.chunker import Chunk

COLLECTION_NAME = "novatech_docs"
DB_PATH = "./chroma_db"


def _get_client() -> chromadb.ClientAPI:
    return chromadb.PersistentClient(path=DB_PATH)


def get_or_create_collection() -> chromadb.Collection:
    client = _get_client()
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},  # distância cosseno para embeddings de texto
    )


def store_chunks(chunks: List[Chunk], embeddings: List[List[float]]) -> None:
    """Armazena chunks com seus embeddings na coleção do ChromaDB."""
    collection = get_or_create_collection()

    ids = [c.chunk_id for c in chunks]
    documents = [c.content for c in chunks]
    metadatas = [
        {
            "source_doc": c.source_doc,
            "section_title": c.section_title,
            **c.metadata,
        }
        for c in chunks
    ]

    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
    )


def search(
    query_embedding: List[float],
    n_results: int = 5,
    where: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Busca os N chunks mais similares à query no ChromaDB.

    Retorna lista de dicts com:
      - chunk_id
      - content
      - source_doc
      - section_title
      - score (similaridade cosseno, 0-1; maior = mais similar)
    """
    collection = get_or_create_collection()

    kwargs: Dict[str, Any] = {
        "query_embeddings": [query_embedding],
        "n_results": n_results,
        "include": ["documents", "metadatas", "distances"],
    }
    if where:
        kwargs["where"] = where

    results = collection.query(**kwargs)

    output = []
    for i, doc_id in enumerate(results["ids"][0]):
        # ChromaDB retorna distância (0 = idêntico), convertemos para score de similaridade
        distance = results["distances"][0][i]
        similarity = 1.0 - distance

        meta = results["metadatas"][0][i]
        output.append({
            "chunk_id": doc_id,
            "content": results["documents"][0][i],
            "source_doc": meta.get("source_doc", ""),
            "section_title": meta.get("section_title", ""),
            "score": round(similarity, 4),
        })

    return output


def reset_collection() -> None:
    """Remove e recria a coleção (útil para re-ingestão completa)."""
    client = _get_client()
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
