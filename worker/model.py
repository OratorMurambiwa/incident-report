"""Pinned local embeddings; never uses hosted inference or downloads at runtime."""
import os
from functools import lru_cache

from langchain_core.embeddings import Embeddings

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_REVISION = "c9745ed1d9f207416be6d2e6f8de32d1f16199bf"
MODEL_PATH = os.getenv("EMBEDDING_MODEL_PATH", "/opt/models/all-MiniLM-L6-v2")
DIMENSIONS = 384


@lru_cache(maxsize=1)
def get_model():
    import torch
    from sentence_transformers import SentenceTransformer
    torch.set_num_threads(2)
    model = SentenceTransformer(MODEL_PATH, device="cpu", local_files_only=True,
                                trust_remote_code=False)
    if model.get_sentence_embedding_dimension() != DIMENSIONS:
        raise RuntimeError("Embedding dimension mismatch")
    return model


class LocalEmbeddings(Embeddings):
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return get_model().encode(texts, normalize_embeddings=True, batch_size=32,
                                  show_progress_bar=False).tolist()

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]
