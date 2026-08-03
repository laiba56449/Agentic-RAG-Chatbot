from abc import ABC, abstractmethod
from typing import List

EMBEDDING_DIMENSIONS = 384  # must match app/models/chunk.py exactly


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Embed a batch of texts; return one vector (list of floats) per input text,
        in the same order. Each vector must have length EMBEDDING_DIMENSIONS."""
        raise NotImplementedError


class SentenceTransformerEmbeddingProvider(EmbeddingProvider):
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        # Imported here, not at module level, so importing this file doesn't force-load
        # the (large) model until a provider is actually instantiated.
        from sentence_transformers import SentenceTransformer
        self._model = SentenceTransformer(model_name)

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        embeddings = self._model.encode(
            texts,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return embeddings.tolist()


_provider_instance: EmbeddingProvider | None = None


def get_embedding_provider() -> EmbeddingProvider:
    """Singleton accessor."""
    global _provider_instance
    if _provider_instance is None:
        _provider_instance = SentenceTransformerEmbeddingProvider()
    return _provider_instance