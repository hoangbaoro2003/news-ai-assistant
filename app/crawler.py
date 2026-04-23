"""
crawler.py – Thu thập bài báo từ RSS feeds của VnExpress, Thanh Niên, Tuổi Trẻ.

Workflow:
  1. Parse RSS feeds (feedparser)
  2. Lọc theo ngày (7 ngày gần nhất)
  3. Scrape nội dung bài (httpx + BeautifulSoup)
  4. Deduplicate theo URL
  5. Lưu raw data JSON để debug/backup
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Optional

import feedparser
import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# ── RSS Sources ───────────────────────────────────────────────────────────────
SOURCES: dict[str, list[str]] = {
    "VnExpress": [
        "https://vnexpress.net/rss/khoa-hoc-cong-nghe.rss",
        "https://vnexpress.net/rss/so-hoa.rss",
    ],
    "ThanhNien": [
        "https://thanhnien.vn/rss/cong-nghe.rss",
    ],
    "TuoiTre": [
        "https://tuoitre.vn/rss/nhip-song-so.rss",
    ],
}

# Technology keyword filter
TECH_KEYWORDS = [
    "ai", "trí tuệ nhân tạo", "công nghệ", "phần mềm", "phần cứng",
    "robot", "chatgpt", "openai", "google", "apple", "samsung", "chip",
    "điện thoại", "smartphone", "máy tính", "internet", "5g", "blockchain",
    "crypto", "xe điện", "ev", "tesla", "nvidia", "startup", "dữ liệu",
    "bảo mật", "hack", "deepseek", "gemini", "claude", "llm",
    "ứng dụng", "app", "vr", "ar", "metaverse", "deepfake",
]


@dataclass
class Article:
    title: str
    link: str
    source: str
    published_at: str        # "YYYY-MM-DD"
    content: str             # cleaned text
    article_id: str = ""

    def __post_init__(self):
        self.article_id = hashlib.md5(self.link.encode()).hexdigest()[:10]

    def to_dict(self) -> dict:
        return asdict(self)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _clean_html(raw: str) -> str:
    if not raw:
        return ""
    soup = BeautifulSoup(raw, "html.parser")
    text = soup.get_text(separator=" ", strip=True)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _parse_date(entry) -> Optional[datetime]:
    for attr in ("published_parsed", "updated_parsed"):
        t = getattr(entry, attr, None)
        if t:
            try:
                return datetime.fromtimestamp(time.mktime(t))
            except Exception:
                continue
    return None


def _is_recent(dt: Optional[datetime], days_back: int) -> bool:
    if dt is None:
        return False
    return dt >= datetime.now() - timedelta(days=days_back)


def _is_tech_relevant(text: str) -> bool:
    lowered = text.lower()
    return any(kw in lowered for kw in TECH_KEYWORDS)


def _scrape_body(url: str, timeout: int = 8) -> str:
    """Best-effort scrape article body (caps at 2000 chars)."""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; NewsBot/1.0)"}
        resp = httpx.get(url, headers=headers, timeout=timeout, follow_redirects=True)
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        for sel in [
            "article", ".article-body", ".fck_detail",
            ".detail-content", ".main-content", "#main-content",
        ]:
            el = soup.select_one(sel)
            if el:
                text = el.get_text(separator=" ", strip=True)
                if len(text) > 120:
                    return re.sub(r"\s+", " ", text)[:2000]
        return re.sub(r"\s+", " ", soup.get_text(separator=" ", strip=True))[:2000]
    except Exception as exc:
        logger.debug("Scrape failed %s: %s", url, exc)
        return ""


# ── Main fetch function ───────────────────────────────────────────────────────

def fetch_articles(
    days_back: int = 7,
    scrape_content: bool = True,
    max_per_source: int = 40,
    save_raw: bool = True,
) -> list[Article]:
    """
    Collect, filter, and return technology articles from the past `days_back` days.

    Parameters
    ----------
    days_back       : lookback window in days
    scrape_content  : whether to scrape article body (richer context, slower)
    max_per_source  : cap per RSS source to avoid overloading
    save_raw        : persist raw JSON to data/raw_articles.json

    Returns
    -------
    list[Article] – deduplicated, topic-filtered, date-filtered articles
    """
    seen: set[str] = set()
    articles: list[Article] = []

    for source_name, feeds in SOURCES.items():
        source_count = 0
        for feed_url in feeds:
            if source_count >= max_per_source:
                break
            try:
                feed = feedparser.parse(feed_url)
                logger.info("Feed %s → %d entries", feed_url, len(feed.entries))
            except Exception as exc:
                logger.warning("Feed error %s: %s", feed_url, exc)
                continue

            for entry in feed.entries:
                if source_count >= max_per_source:
                    break

                link = getattr(entry, "link", "") or getattr(entry, "id", "")
                if not link or link in seen:
                    continue

                pub_dt = _parse_date(entry)
                if not _is_recent(pub_dt, days_back):
                    continue

                title = getattr(entry, "title", "").strip()
                raw_summary = getattr(entry, "summary", "") or getattr(entry, "description", "")
                summary = _clean_html(raw_summary)

                if not _is_tech_relevant(f"{title} {summary}"):
                    continue

                # Scrape body or fall back to RSS summary
                body = _scrape_body(link) if scrape_content else ""
                content = body or summary

                articles.append(Article(
                    title=title,
                    link=link,
                    source=source_name,
                    published_at=pub_dt.strftime("%Y-%m-%d"),
                    content=content,
                ))
                seen.add(link)
                source_count += 1

    logger.info("Total articles collected: %d", len(articles))

    if save_raw:
        os.makedirs("data", exist_ok=True)
        with open("data/raw_articles.json", "w", encoding="utf-8") as f:
            json.dump([a.to_dict() for a in articles], f, ensure_ascii=False, indent=2)
        logger.info("Raw data saved → data/raw_articles.json")

    return articles
