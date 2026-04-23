"""
pipeline.py – Central orchestrator used by both CLI and Streamlit UI.

Exposes a single run() function so neither main_cli.py nor ui.py needs
to know about individual pipeline stages.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Callable, Optional

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    articles_total: int
    articles_used: int
    keywords: list[str]
    report: dict           # {executive_summary, highlights}
    markdown: str


def run(
    days_back: int = 7,
    top_k: int = 12,
    api_key: str = "",
    scrape_content: bool = True,
    progress_cb: Optional[Callable[[str], None]] = None,
) -> PipelineResult:
    """
    Run the full pipeline end-to-end.

    Parameters
    ----------
    days_back    : lookback window in days
    top_k        : articles passed to LLM for summarization
    api_key      : Gemini API key (empty → extractive fallback)
    scrape_content : fetch article body content (slower, richer)
    progress_cb  : optional callback(message: str) for UI progress updates

    Returns
    -------
    PipelineResult
    """

    def log(msg: str):
        logger.info(msg)
        if progress_cb:
            progress_cb(msg)

    # ── Build LLM ────────────────────────────────────────────────────────────
    llm = None
    if api_key:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            os.environ["GOOGLE_API_KEY"] = api_key
            llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.2)
            log("✅ Gemini API key hợp lệ – LLM đã sẵn sàng")
        except Exception as exc:
            log(f"⚠️ Không thể khởi tạo LLM ({exc}) – dùng extractive fallback")

    # ── Step 1: Fetch ─────────────────────────────────────────────────────────
    log("1️⃣  Đang thu thập bài báo từ RSS feeds (VnExpress, Thanh Niên, Tuổi Trẻ)…")
    from app.crawler import fetch_articles
    articles = fetch_articles(days_back=days_back, scrape_content=scrape_content)
    log(f"   → Thu thập được {len(articles)} bài phù hợp chủ đề Công nghệ")

    if not articles:
        return PipelineResult(
            articles_total=0, articles_used=0,
            keywords=[], report={"executive_summary": "Không thu thập được bài báo.", "highlights": []},
            markdown="# Lỗi\nKhông thu thập được bài báo. Kiểm tra kết nối mạng.",
        )

    # ── Step 2: Index + Retrieve ──────────────────────────────────────────────
    log("2️⃣  Đang embedding & xây dựng FAISS index…")
    from app.indexer import select_articles
    top_articles = select_articles(articles, k=top_k)
    log(f"   → Chọn {len(top_articles)} bài đa dạng nhất qua MMR retrieval")

    # ── Step 3: Keywords ──────────────────────────────────────────────────────
    log("3️⃣  Đang trích xuất Trending Keywords (TF-IDF → MMR → LLM refine)…")
    from app.keyword import extract_keywords
    keywords = extract_keywords(top_articles, llm=llm, top_n=10)
    log(f"   → Keywords: {', '.join(keywords[:5])}…")

    # ── Step 4: Summarize ─────────────────────────────────────────────────────
    log("4️⃣  LLM đang tổng hợp Executive Report…")
    from app.summarizer import generate_report, render_markdown
    report = generate_report(top_articles, keywords, llm=llm)
    markdown = render_markdown(report, keywords)
    log("   → Báo cáo hoàn tất!")

    return PipelineResult(
        articles_total=len(articles),
        articles_used=len(top_articles),
        keywords=keywords,
        report=report,
        markdown=markdown,
    )
