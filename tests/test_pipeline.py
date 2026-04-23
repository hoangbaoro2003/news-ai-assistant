"""
tests/test_pipeline.py – Unit & integration tests for core modules.

Run: pytest tests/ -v
"""

from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
import pytest

# ── Helpers ───────────────────────────────────────────────────────────────────

def make_article(
    title="OpenAI phát hành GPT-5 mới nhất",
    link="https://vnexpress.net/openai-gpt5-123.html",
    source="VnExpress",
    days_ago=1,
    content="OpenAI vừa công bố mô hình ngôn ngữ lớn GPT-5 với khả năng lý luận vượt trội.",
):
    from app.crawler import Article
    pub = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
    return Article(title=title, link=link, source=source, published_at=pub, content=content)

def make_articles(n=8):
    topics = [
        ("AI vượt mốc 1 tỷ người dùng", "VnExpress", "Trí tuệ nhân tạo đạt mốc quan trọng toàn cầu."),
        ("Apple ra mắt iPhone 17", "ThanhNien", "Apple công bố dòng iPhone mới với chip A19."),
        ("Samsung Galaxy S25 Ultra", "TuoiTre", "Samsung ra mắt flagship với camera 200MP AI."),
        ("Blockchain tại Việt Nam", "VnExpress", "Chính phủ thúc đẩy ứng dụng blockchain."),
        ("Google Gemini 2.5 Pro", "ThanhNien", "Google phát hành Gemini 2.5 với 1M token context."),
        ("Deepfake lừa đảo doanh nghiệp", "TuoiTre", "Cảnh báo deepfake tấn công doanh nghiệp Việt."),
        ("Startup AI Việt Nam gọi vốn", "VnExpress", "KAI Technology huy động 30 triệu USD Series B."),
        ("5G phủ sóng toàn quốc", "ThanhNien", "Viettel hoàn thành phủ sóng 5G 63 tỉnh thành."),
    ]
    return [
        make_article(
            title=topics[i % len(topics)][0],
            link=f"https://example.com/art-{i}",
            source=topics[i % len(topics)][1],
            days_ago=i + 1,
            content=topics[i % len(topics)][2],
        )
        for i in range(n)
    ]


# ── crawler tests ─────────────────────────────────────────────────────────────

class TestCrawler:
    def test_article_id_deterministic(self):
        a1 = make_article(link="https://example.com/foo")
        a2 = make_article(link="https://example.com/foo")
        assert a1.article_id == a2.article_id

    def test_article_id_unique(self):
        a1 = make_article(link="https://example.com/foo")
        a2 = make_article(link="https://example.com/bar")
        assert a1.article_id != a2.article_id

    def test_article_to_dict(self):
        a = make_article()
        d = a.to_dict()
        assert "title" in d and "link" in d and "source" in d

    def test_is_recent_within(self):
        from app.crawler import _is_recent
        dt = datetime.now() - timedelta(days=3)
        assert _is_recent(dt, 7) is True

    def test_is_recent_outside(self):
        from app.crawler import _is_recent
        dt = datetime.now() - timedelta(days=10)
        assert _is_recent(dt, 7) is False

    def test_is_recent_none(self):
        from app.crawler import _is_recent
        assert _is_recent(None, 7) is False

    def test_is_tech_relevant_true(self):
        from app.crawler import _is_tech_relevant
        assert _is_tech_relevant("Google ra mắt mô hình AI mới nhất") is True

    def test_is_tech_relevant_false(self):
        from app.crawler import _is_tech_relevant
        assert _is_tech_relevant("Thời tiết hôm nay đẹp và nắng nhẹ") is False

    def test_clean_html(self):
        from app.crawler import _clean_html
        result = _clean_html("<p>Hello <b>World</b></p>")
        assert "Hello" in result and "<" not in result


# ── keyword tests ─────────────────────────────────────────────────────────────

class TestKeyword:
    def test_extract_keywords_returns_list(self):
        from app.keyword import extract_keywords
        arts = make_articles(5)
        kws = extract_keywords(arts, llm=None)
        assert isinstance(kws, list) and len(kws) > 0

    def test_extract_keywords_respects_top_n(self):
        from app.keyword import extract_keywords
        arts = make_articles(8)
        kws = extract_keywords(arts, llm=None, top_n=5)
        assert len(kws) <= 5

    def test_extract_keywords_empty_articles(self):
        from app.keyword import extract_keywords
        kws = extract_keywords([], llm=None)
        assert isinstance(kws, list) and len(kws) > 0  # returns defaults

    def test_tfidf_candidates(self):
        from app.keyword import _tfidf_candidates
        arts = make_articles(5)
        cands = _tfidf_candidates(arts, top_n=20)
        assert isinstance(cands, list) and len(cands) > 0


# ── summarizer tests ──────────────────────────────────────────────────────────

class TestSummarizer:
    def test_extractive_fallback_structure(self):
        from app.summarizer import _extractive_report
        arts = make_articles(5)
        report = _extractive_report(arts, ["AI", "smartphone"])
        assert "executive_summary" in report
        assert "highlights" in report
        assert isinstance(report["highlights"], list)

    def test_extractive_highlights_have_url(self):
        from app.summarizer import _extractive_report
        arts = make_articles(5)
        report = _extractive_report(arts, ["AI"])
        for h in report["highlights"]:
            assert "source_url" in h and h["source_url"].startswith("https://")

    def test_render_markdown(self):
        from app.summarizer import render_markdown
        report = {
            "executive_summary": "Tuần công nghệ sôi động.",
            "highlights": [
                {"rank": 1, "title": "Test", "summary": "Tóm tắt.", "source": "VnExpress",
                 "source_url": "https://vnexpress.net/test", "published_at": "2025-04-20"},
            ],
        }
        md = render_markdown(report, ["AI", "chip"])
        assert "Executive Summary" in md
        assert "Highlighted News" in md
        assert "vnexpress.net" in md

    def test_generate_report_no_llm(self):
        from app.summarizer import generate_report
        arts = make_articles(5)
        report = generate_report(arts, ["AI", "công nghệ"], llm=None)
        assert "executive_summary" in report
        assert len(report.get("highlights", [])) > 0

    def test_generate_report_empty_articles(self):
        from app.summarizer import generate_report
        report = generate_report([], [], llm=None)
        assert "executive_summary" in report


# ── indexer tests ─────────────────────────────────────────────────────────────

class TestIndexer:
    def test_select_articles_fallback(self):
        """select_articles should work even if faiss is not installed (recency sort)."""
        from app.indexer import select_articles
        arts = make_articles(8)
        selected = select_articles(arts, k=5)
        assert len(selected) <= 5
        assert all(hasattr(a, "title") for a in selected)

    def test_select_articles_respects_k(self):
        from app.indexer import select_articles
        arts = make_articles(8)
        selected = select_articles(arts, k=3)
        assert len(selected) <= 3


# ── pipeline smoke test ───────────────────────────────────────────────────────

class TestPipeline:
    def test_smoke_no_network_no_llm(self, monkeypatch):
        """End-to-end smoke test: mock crawler, run full pipeline, check output shape."""
        from app import pipeline as pl

        dummy = make_articles(8)
        monkeypatch.setattr("app.crawler.fetch_articles", lambda **kw: dummy)

        result = pl.run(days_back=7, top_k=6, api_key="", scrape_content=False)

        assert result.articles_total == 8
        assert result.articles_used <= 6
        assert isinstance(result.keywords, list) and len(result.keywords) > 0
        assert "executive_summary" in result.report
        assert isinstance(result.report.get("highlights"), list)
        assert "Executive Summary" in result.markdown

    def test_pipeline_no_articles(self, monkeypatch):
        from app import pipeline as pl
        monkeypatch.setattr("app.crawler.fetch_articles", lambda **kw: [])
        result = pl.run(days_back=7, api_key="", scrape_content=False)
        assert result.articles_total == 0
        assert result.keywords == []
