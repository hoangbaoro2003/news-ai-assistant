"""
keyword.py – Hybrid keyword extraction pipeline.

Stage 1 – TF-IDF (scikit-learn): identifies statistically important terms
           from the article corpus without any API calls.
Stage 2 – FAISS + MMR: embeds keyword candidates and selects diverse,
           non-redundant top terms using Maximal Marginal Relevance.
Stage 3 – LLM Refine (Gemini, optional): passes candidates to the LLM
           for a final editorial pass, turning raw tokens into readable
           trend labels.

This layered approach works even without an API key (Stages 1+2 only).
"""

from __future__ import annotations

import logging
import re
from collections import Counter
from typing import Optional

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

logger = logging.getLogger(__name__)

# Vietnamese stopwords (extended)
STOPWORDS_VN = {
    "và", "của", "là", "có", "được", "với", "trong", "cho", "từ", "về",
    "đã", "sẽ", "này", "các", "một", "những", "không", "để", "khi", "như",
    "theo", "tại", "trên", "sau", "vào", "hay", "hoặc", "nên", "cũng",
    "bởi", "vì", "đến", "lên", "ra", "đó", "mà", "thì", "còn", "đây",
    "thế", "rất", "lại", "nhiều", "cần", "người", "năm", "ngày", "tuần",
    "tháng", "qua", "đầu", "mới", "hơn", "nhất", "chỉ", "cũng", "được",
    "bị", "làm", "đang", "tiếp", "tục", "phải", "nếu", "nhưng", "vẫn",
}


# ── Stage 1: TF-IDF ──────────────────────────────────────────────────────────

def _tfidf_candidates(articles: list, top_n: int = 40) -> list[str]:
    """Extract top-N terms by TF-IDF score."""
    texts = [f"{a.title} {a.content}" for a in articles]
    try:
        vec = TfidfVectorizer(
            max_features=top_n,
            ngram_range=(1, 2),          # unigrams + bigrams
            stop_words=list(STOPWORDS_VN),
            token_pattern=r"(?u)\b[\wÀ-ỹ]{3,}\b",
            sublinear_tf=True,
        )
        vec.fit_transform(texts)
        return vec.get_feature_names_out().tolist()
    except Exception as exc:
        logger.warning("TF-IDF failed: %s", exc)
        # Frequency fallback
        freq: Counter = Counter()
        for a in articles:
            words = re.findall(r"\b[\wÀ-ỹ]{3,}\b", f"{a.title} {a.content}".lower())
            for w in words:
                if w not in STOPWORDS_VN:
                    freq[w] += 1
        return [w for w, _ in freq.most_common(top_n)]


# ── Stage 2: FAISS + MMR diversity ranking ────────────────────────────────────

def _mmr_rank(candidates: list[str], query: str, k: int = 15, lambda_: float = 0.6) -> list[str]:
    """
    Rank keyword candidates using MMR:
    score = lambda * relevance(w, query) - (1-lambda) * max_sim(w, selected)

    Falls back to plain candidates[:k] if sentence-transformers / FAISS unavailable.
    """
    try:
        from sentence_transformers import SentenceTransformer
        import faiss

        model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
        all_texts = [query] + candidates
        embs = model.encode(all_texts, normalize_embeddings=True).astype("float32")

        q_vec = embs[0:1]
        c_embs = embs[1:]

        # Build FAISS index for candidates
        dim = c_embs.shape[1]
        index = faiss.IndexFlatIP(dim)
        index.add(c_embs)

        selected: list[int] = []
        remaining = list(range(len(candidates)))

        for _ in range(min(k, len(candidates))):
            if not remaining:
                break
            rel = (c_embs[remaining] @ q_vec.T).flatten()
            if not selected:
                best = remaining[int(np.argmax(rel))]
            else:
                sel_embs = c_embs[selected]
                sim_to_sel = (c_embs[remaining] @ sel_embs.T).max(axis=1)
                scores = lambda_ * rel - (1 - lambda_) * sim_to_sel
                best = remaining[int(np.argmax(scores))]
            selected.append(best)
            remaining.remove(best)

        return [candidates[i] for i in selected]

    except ImportError:
        logger.info("sentence-transformers/faiss not available – skipping MMR step")
        return candidates[:k]


# ── Stage 3: LLM Refine ───────────────────────────────────────────────────────

def _llm_refine(candidates: list[str], llm) -> list[str]:
    """
    Ask the LLM to pick the 10 most meaningful trend labels from candidates.
    Returns original candidates[:10] on any failure.
    """
    prompt = (
        f"Đây là danh sách các từ/cụm từ xuất hiện nhiều trong tin tức công nghệ tuần qua:\n"
        f"{candidates}\n\n"
        "Hãy chọn ra đúng 10 từ khóa/xu hướng quan trọng và có ý nghĩa nhất cho độc giả. "
        "Ưu tiên cụm từ (2-3 chữ) hơn từ đơn. "
        "Chỉ trả về 10 từ khóa, ngăn cách bởi dấu phẩy. Không giải thích."
    )
    try:
        response = llm.invoke(prompt)
        refined = [k.strip() for k in response.content.split(",") if k.strip()]
        return refined[:10] if refined else candidates[:10]
    except Exception as exc:
        logger.warning("LLM keyword refine failed: %s", exc)
        return candidates[:10]


# ── Public API ────────────────────────────────────────────────────────────────

def extract_keywords(
    articles: list,
    llm=None,
    top_n: int = 10,
) -> list[str]:
    """
    Full hybrid keyword extraction.

    Parameters
    ----------
    articles : list[Article]
    llm      : LangChain LLM instance (optional – skip Stage 3 if None)
    top_n    : final number of keywords to return

    Returns
    -------
    list[str] – top trending keywords/phrases
    """
    if not articles:
        return ["Công nghệ", "AI", "Smartphone", "Bảo mật", "Chuyển đổi số"]

    logger.info("[Keyword] Stage 1: TF-IDF extraction…")
    candidates = _tfidf_candidates(articles, top_n=40)
    logger.info("[Keyword] %d candidates from TF-IDF: %s", len(candidates), candidates[:8])

    logger.info("[Keyword] Stage 2: MMR diversity ranking…")
    query = "xu hướng công nghệ AI trí tuệ nhân tạo tuần này Việt Nam"
    ranked = _mmr_rank(candidates, query, k=top_n * 2)
    logger.info("[Keyword] MMR top: %s", ranked[:8])

    if llm is not None:
        logger.info("[Keyword] Stage 3: LLM refinement…")
        final = _llm_refine(ranked, llm)
    else:
        final = ranked[:top_n]

    logger.info("[Keyword] Final keywords: %s", final)
    return final
