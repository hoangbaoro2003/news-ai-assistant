"""
main_cli.py – Command-line interface for the AI News Assistant.

Chạy pipeline hoàn chỉnh, xuất báo cáo ra file Markdown và JSON.
Phù hợp để dùng như cronjob, backend script, hoặc CI pipeline.

Usage:
  python app/main_cli.py                            # extractive fallback (no key needed)
  python app/main_cli.py --api-key AIza...          # dùng Gemini
  python app/main_cli.py --days 7 --top-k 12        # tuỳ chỉnh tham số
  GEMINI_API_KEY=AIza... python app/main_cli.py     # qua env var
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

# Add project root to path (so `python app/main_cli.py` works from root)
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)


def main():
    parser = argparse.ArgumentParser(
        description="AI News Assistant – Weekly Tech News Summarizer (CLI)"
    )
    parser.add_argument("--api-key", default=os.getenv("GEMINI_API_KEY", ""),
                        help="Gemini API key (or set GEMINI_API_KEY env var)")
    parser.add_argument("--days", type=int, default=7,
                        help="Lookback window in days (default: 7)")
    parser.add_argument("--top-k", type=int, default=12,
                        help="Articles to use for summarization (default: 12)")
    parser.add_argument("--no-scrape", action="store_true",
                        help="Skip body scraping (faster, less rich)")
    parser.add_argument("--output-md", default="reports/weekly_report.md",
                        help="Markdown report output path")
    parser.add_argument("--output-json", default="reports/weekly_report.json",
                        help="JSON report output path")
    args = parser.parse_args()

    sep = "=" * 65
    print(f"\n{sep}")
    print("  🤖  AI NEWS ASSISTANT  –  Weekly Technology Digest")
    print(sep)

    from app.pipeline import run

    def progress(msg: str):
        print(f"  {msg}")

    result = run(
        days_back=args.days,
        top_k=args.top_k,
        api_key=args.api_key,
        scrape_content=not args.no_scrape,
        progress_cb=progress,
    )

    # ── Save Markdown ─────────────────────────────────────────────────────────
    Path(args.output_md).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output_md, "w", encoding="utf-8") as f:
        f.write(result.markdown)

    # ── Save JSON ─────────────────────────────────────────────────────────────
    Path(args.output_json).parent.mkdir(parents=True, exist_ok=True)
    full_json = {
        "keywords": result.keywords,
        **result.report,
    }
    with open(args.output_json, "w", encoding="utf-8") as f:
        json.dump(full_json, f, ensure_ascii=False, indent=2)

    # ── Console summary ───────────────────────────────────────────────────────
    print(f"\n{sep}")
    print(f"  📊 Articles fetched : {result.articles_total}")
    print(f"  📄 Articles used    : {result.articles_used}")
    print(f"  🔑 Keywords         : {', '.join(result.keywords[:5])}…")
    print(f"\n  💾 Markdown report  → {args.output_md}")
    print(f"  💾 JSON report      → {args.output_json}")
    print(f"{sep}\n")

    # ── Print preview ─────────────────────────────────────────────────────────
    print("─── EXECUTIVE SUMMARY PREVIEW ────────────────────────────────")
    print(result.report.get("executive_summary", "")[:500])
    print("\n─── HIGHLIGHTED NEWS ──────────────────────────────────────────")
    for h in result.report.get("highlights", [])[:4]:
        print(f"[{h.get('rank')}] {h.get('title')}")
        print(f"    {h.get('summary', '')[:120]}…")
        print(f"    🔗 {h.get('source_url', '')}\n")


if __name__ == "__main__":
    main()
