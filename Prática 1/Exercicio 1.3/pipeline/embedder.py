"""
Módulo de geração de embeddings com sentence-transformers.

Modelo escolhido: paraphrase-multilingual-MiniLM-L12-v2
- Gratuito e open-source (licença Apache 2.0)
- 384 dimensões — mesmo tamanho do all-MiniLM-L6-v2
- Treinado explicitamente em 50+ idiomas incluindo português — essencial para este projeto
- Substituiu all-MiniLM-L6-v2 que é primariamente inglês e gerava recall ~0% em PT-BR
- Roda localmente sem necessidade de API key
"""

from functools import lru_cache
from typing import List

from sentence_transformers import SentenceTransformer

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"


@lru_cache(maxsize=1)
def _get_model() -> SentenceTransformer:
    """Carrega o modelo uma única vez e mantém em cache. Força CPU para evitar
    incompatibilidade de compute capability com GPUs antigas (CC < 7.5)."""
    return SentenceTransformer(MODEL_NAME, device="cpu")


def embed_texts(texts: List[str]) -> List[List[float]]:
    """Gera embeddings para uma lista de textos."""
    model = _get_model()
    embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
    return embeddings.tolist()


def embed_query(query: str) -> List[float]:
    """Gera o embedding para uma pergunta de busca."""
    return embed_texts([query])[0]
