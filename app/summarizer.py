"""
summarizer.py – Tạo báo cáo tuần từ danh sách bài báo đã chọn.

Sử dụng Google Gemini (qua LangChain) để viết:
  - Executive Summary  (tổng quan xu hướng tuần)
  - Highlighted News   (5-8 sự kiện quan trọng + link nguồn)

Khi không có API key, tự động dùng extractive fallback để vẫn cho ra
output hợp lệ (dùng được để test pipeline).
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime

logger = logging.getLogger(__name__)

# ── Extractive fallback (no LLM) ─────────────────────────────────────────────

def _extractive_report(articles: list, keywords: list[str]) -> dict:
    """Build a basic report from raw metadata when no LLM is available."""
    today = datetime.now().strftime("%d/%m/%Y")
    oldest = articles[-1].published_at if articles else "N/A"

    exec_summary = (
        f"Tuần từ {oldest} đến {today}, công nghệ Việt Nam và thế giới ghi nhận "
        f"{len(articles)} sự kiện đáng chú ý từ các nguồn VnExpress, Thanh Niên, Tuổi Trẻ. "
        f"Các chủ đề nổi bật bao gồm: {', '.join(keywords[:5])}. "
        "Hệ thống đang chạy ở chế độ không có LLM – vui lòng cung cấp GEMINI_API_KEY "
        "để nhận tóm tắt chất lượng cao hơn."
    )

    highlights = []
    for i, a in enumerate(articles[:8], 1):
        highlights.append({
            "rank": i,
            "title": a.title,
            "summary": a.content[:250].strip() + "…" if len(a.content) > 250 else a.content,
            "source": a.source,
            "source_url": a.link,
            "published_at": a.published_at,
        })

    return {
        "executive_summary": exec_summary,
        "highlights": highlights,
    }


# ── LLM report generation ─────────────────────────────────────────────────────

def _build_prompt(articles: list, keywords: list[str]) -> str:
    context = "\n".join(
        f"[{i}] [{a.source}] {a.title} ({a.published_at})\n"
        f"    Nội dung: {a.content[:400]}\n"
        f"    Link: {a.link}"
        for i, a in enumerate(articles[:15], 1)
    )
    kw_str = ", ".join(keywords)

    return f"""Bạn là AI News Assistant chuyên nghiệp. Hãy viết BÁO CÁO CÔNG NGHỆ TUẦN QUA bằng Tiếng Việt chuẩn mực, súc tích và có chiều sâu phân tích.

DỮ LIỆU BÀI VIẾT:
{context}

TỪ KHÓA XU HƯỚNG: {kw_str}

YÊU CẦU: Trả về một JSON hợp lệ (không có markdown, không có giải thích), với cấu trúc sau:
{{
  "executive_summary": "Đoạn văn 4-6 câu tổng quan bức tranh công nghệ tuần qua, nêu xu hướng nổi bật và các diễn biến đáng chú ý nhất.",
  "highlights": [
    {{
      "rank": 1,
      "title": "Tiêu đề sự kiện",
      "summary": "Tóm tắt 2-3 câu về sự kiện",
      "source": "Tên nguồn",
      "source_url": "URL gốc từ dữ liệu",
      "published_at": "YYYY-MM-DD"
    }}
  ]
}}

Chọn 6-8 sự kiện quan trọng nhất. Giữ nguyên URL từ dữ liệu, không tự tạo URL.
"""


def generate_report(
    articles: list,
    keywords: list[str],
    llm=None,
) -> dict:
    """
    Generate the full weekly report dict.

    Parameters
    ----------
    articles  : top-K selected Article objects
    keywords  : trending keywords list
    llm       : LangChain LLM instance (None → extractive fallback)

    Returns
    -------
    dict with keys: executive_summary, highlights
    """
    if not articles:
        return {
            "executive_summary": "Không có bài báo nào được thu thập.",
            "highlights": [],
        }

    if llm is None:
        logger.info("No LLM – using extractive fallback")
        return _extractive_report(articles, keywords)

    prompt = _build_prompt(articles, keywords)
    try:
        logger.info("Calling Gemini for report generation…")
        response = llm.invoke(prompt)
        raw = response.content.strip()

        # Strip markdown fences if present
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
        raw = re.sub(r"\s*```$", "", raw, flags=re.MULTILINE)

        report = json.loads(raw)
        return report

    except json.JSONDecodeError:
        logger.warning("LLM returned non-JSON – trying Markdown extraction fallback")
        # Return raw content as executive summary for UI display
        return {
            "executive_summary": response.content,
            "highlights": _extractive_report(articles, keywords)["highlights"],
        }
    except Exception as exc:
        logger.warning("LLM report generation failed: %s – using extractive fallback", exc)
        return _extractive_report(articles, keywords)


# ── Markdown renderer ─────────────────────────────────────────────────────────

def render_markdown(report: dict, keywords: list[str]) -> str:
    """Convert report dict to formatted Markdown string for CLI/file output."""
    today = datetime.now().strftime("%d/%m/%Y")
    lines = [
        f"# 📰 Weekly Technology News Report",
        f"**Ngày tạo:** {today}  |  **Nguồn:** VnExpress, Thanh Niên, Tuổi Trẻ\n",
        "---\n",
        "## 🔥 Trending Keywords\n",
        " ".join(f"`{k}`" for k in keywords) + "\n",
        "---\n",
        "## 📋 Executive Summary\n",
        report.get("executive_summary", "") + "\n",
        "---\n",
        "## 📰 Highlighted News\n",
    ]

    for item in report.get("highlights", []):
        rank = item.get("rank", "")
        title = item.get("title", "")
        summary = item.get("summary", "")
        source = item.get("source", "")
        url = item.get("source_url", "#")
        date = item.get("published_at", "")

        lines += [
            f"### {rank}. {title}",
            f"- **Tóm tắt:** {summary}",
            f"- **Nguồn:** [{source}]({url})  |  📅 {date}\n",
        ]

    return "\n".join(lines)
