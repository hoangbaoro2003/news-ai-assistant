"""
indexer.py – Vector indexing + MMR retrieval for article selection.

Encodes articles with a multilingual sentence transformer, builds a FAISS
cosine-similarity index, then retrieves the top-K most relevant AND diverse
articles using Maximal Marginal Relevance (MMR).

Falls back gracefully to recency-based selection if dependencies are missing.
"""

from __future__ import annotations

import logging

import numpy as np

logger = logging.getLogger(__name__)

TOPIC_QUERY = (
    "công nghệ AI trí tuệ nhân tạo điện thoại phần mềm "
    "internet bảo mật startup chip Việt Nam tuần này"
)


class ArticleIndexer:
    """
    Build FAISS index over articles and retrieve top-K via MMR.

    Usage:
        idx = ArticleIndexer()
        idx.build(articles)
        top = idx.retrieve_mmr(k=12)
    """

    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"):
        self._model_name = model_name
        self._model = None
        self._index = None
        self._articles: list = []
        self._embeddings = None

    def _load_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            logger.info("Loading embedding model: %s", self._model_name)
            self._model = SentenceTransformer(self._model_name)
        return self._model

    def build(self, articles: list) -> None:
        import faiss
        self._articles = articles
        docs = [f"{a.title} {a.content[:500]}" for a in articles]

        model = self._load_model()
        logger.info("Encoding %d articles…", len(docs))
        embs = model.encode(
            docs, normalize_embeddings=True,
            show_progress_bar=False, batch_size=32
        ).astype("float32")
        self._embeddings = embs

        dim = embs.shape[1]
        self._index = faiss.IndexFlatIP(dim)
        self._index.add(embs)
        logger.info("FAISS index built (dim=%d, n=%d)", dim, len(articles))

    def retrieve_mmr(
        self,
        query: str = TOPIC_QUERY,
        k: int = 12,
        lambda_: float = 0.6,
        pool_factor: int = 4,
    ) -> list:
        """
        MMR retrieval: balances relevance to `query` vs. diversity among selected.
        lambda_=1.0 → pure relevance; lambda_=0.0 → pure diversity.
        """
        if self._index is None or self._embeddings is None:
            raise RuntimeError("Call build() first.")

        pool_size = min(len(self._articles), k * pool_factor)
        model = self._load_model()
        q_vec = model.encode([query], normalize_embeddings=True).astype("float32")

        _, pool_idx = self._index.search(q_vec, pool_size)
        pool_idx = [i for i in pool_idx[0] if i >= 0]
        if not pool_idx:
            return self._articles[:k]

        pool_embs = self._embeddings[pool_idx]
        selected: list[int] = []
        remaining = list(range(len(pool_idx)))

        for _ in range(min(k, len(pool_idx))):
            if not remaining:
                break
            rel = (pool_embs[remaining] @ q_vec.T).flatten()
            if not selected:
                best = remaining[int(np.argmax(rel))]
            else:
                sel_embs = pool_embs[selected]
                sim_max = (pool_embs[remaining] @ sel_embs.T).max(axis=1)
                scores = lambda_ * rel - (1 - lambda_) * sim_max
                best = remaining[int(np.argmax(scores))]
            selected.append(best)
            remaining.remove(best)

        results = [self._articles[pool_idx[i]] for i in selected]
        results.sort(key=lambda a: a.published_at, reverse=True)
        return results


def select_articles(articles: list, k: int = 12) -> list:
    """
    Public helper: try FAISS+MMR, fall back to recency sort on ImportError.
    """
    if not articles:
        return []
    try:
        idx = ArticleIndexer()
        idx.build(articles)
        return idx.retrieve_mmr(k=k)
    except ImportError:
        logger.warning("faiss/sentence-transformers unavailable – using recency sort")
        return sorted(articles, key=lambda a: a.published_at, reverse=True)[:k]
