# 📰 AI News Assistant – Weekly Technology Intelligence System

> **Candidate:** Trần Lê Hoàng Bảo &nbsp;|&nbsp; **Role:** AI Engineer Intern – Technical Assessment &nbsp;|&nbsp; **PCA Company Services**

An end-to-end **AI-powered news intelligence system** that automatically collects, filters, ranks, and summarizes Vietnamese technology news into a structured weekly digest — available via both a **CLI backend** and an **interactive Streamlit web UI**.

---

## ✨ Live Demo Preview

| Web UI (Streamlit) | CLI Output |
|---|---|
| Nhập API key → Click → Xem báo cáo ngay trên browser | Chạy ngầm → Xuất file `.md` + `.json` |

```
🔥 Trending Keywords
#trí tuệ nhân tạo  #Gemini 2.5 Pro  #smartphone AI  #deepfake  #startup Việt Nam

📋 Executive Summary
Tuần từ 15/04 đến 22/04/2026, lĩnh vực công nghệ ghi nhận làn sóng
đột phá từ các mô hình AI thế hệ mới. Google ra mắt Gemini 2.5 Pro...

📰 Highlighted News
[1] Google ra mắt Gemini 2.5 Pro – mô hình AI mạnh nhất từ trước đến nay
    Google chính thức phát hành Gemini 2.5 Pro với 1M token context...
    🔗 https://vnexpress.net/...
```

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│               AI NEWS ASSISTANT  –  PIPELINE                    │
│                                                                  │
│  ┌──────────┐   ┌──────────────┐   ┌──────────────────────┐    │
│  │ CRAWLER  │──▶│   INDEXER    │──▶│      KEYWORD         │    │
│  │          │   │              │   │                      │    │
│  │ feedparser│   │sentence-    │   │ Stage 1: TF-IDF      │    │
│  │ httpx    │   │transformers  │   │ Stage 2: FAISS MMR   │    │
│  │ bs4      │   │ + FAISS      │   │ Stage 3: LLM Refine  │    │
│  │          │   │ IndexFlatIP  │   │                      │    │
│  │VnExpress │   │              │   └──────────┬───────────┘    │
│  │ThanhNien │   │  MMR select  │              │                 │
│  │TuoiTre   │   │  top-K       │              ▼                 │
│  └──────────┘   └──────────────┘   ┌──────────────────────┐    │
│        │                           │     SUMMARIZER       │    │
│        ▼                           │                      │    │
│  data/raw_articles.json            │  Gemini 1.5 Flash    │    │
│                                    │  (LangChain)         │    │
│                                    │  + extractive fallback│   │
│                                    └──────────┬───────────┘    │
│                                               │                 │
│                              ┌────────────────┴──────────┐     │
│                              │         OUTPUT             │     │
│                              │  CLI: .md + .json files   │     │
│                              │  UI : Streamlit browser   │     │
│                              └───────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
```

**Pipeline stages:**

| # | Module | Technology | What it does |
|---|--------|-----------|-------------|
| 1 | `crawler.py` | feedparser + httpx + BeautifulSoup | Parse RSS, filter 7 days, scrape body, deduplicate |
| 2 | `indexer.py` | sentence-transformers + FAISS | Embed articles → MMR retrieval for top-K diverse articles |
| 3 | `keyword.py` | scikit-learn + FAISS + Gemini | TF-IDF → MMR ranking → LLM editorial refine |
| 4 | `summarizer.py` | LangChain + Gemini 1.5 Flash | Executive summary + highlighted news (structured JSON) |
| 5 | `pipeline.py` | Python orchestrator | Ties all stages; used by both CLI and UI |

---

## 🚀 Quick Start

### 1. Clone & install

```bash
git clone https://github.com/<your-username>/news-ai-assistant.git
cd news-ai-assistant
pip install -r requirements.txt
```

### 2. Configure API key (optional but recommended)

```bash
cp .env.example .env
# Mở .env và điền GEMINI_API_KEY
# Lấy key miễn phí tại: https://aistudio.google.com/apikey
```

> **Không có API key?** Hệ thống vẫn chạy được với Extractive Mode — pipeline đầy đủ, chỉ phần tóm tắt cuối dùng thuật toán thay vì LLM.

### 3. Run

**Mode A – Interactive Web UI (recommended for demo)**
```bash
streamlit run app/ui.py
# → Mở trình duyệt tại http://localhost:8501
```

**Mode B – CLI (for backend / automation)**
```bash
# Extractive mode (không cần API key)
python app/main_cli.py

# Với Gemini API
python app/main_cli.py --api-key AIza...

# Qua environment variable
GEMINI_API_KEY=AIza... python app/main_cli.py

# Tuỳ chỉnh
python app/main_cli.py --days 7 --top-k 12 --output-md reports/report.md
```

**Run tests**
```bash
pytest tests/ -v
```

---

## 📁 Project Structure

```
news-ai-assistant/
├── app/
│   ├── __init__.py
│   ├── crawler.py       # RSS collection + scraping + topic filter
│   ├── indexer.py       # FAISS vector index + MMR article retrieval
│   ├── keyword.py       # TF-IDF → MMR → LLM keyword extraction
│   ├── summarizer.py    # Gemini report generation + extractive fallback
│   ├── pipeline.py      # Central orchestrator (used by CLI + UI)
│   ├── main_cli.py      # CLI entry point → exports .md + .json
│   └── ui.py            # Streamlit web interface
│
├── data/
│   └── raw_articles.json    # Auto-saved raw crawl output (for debug)
│
├── reports/
│   └── sample_report.json   # Pre-generated demo output
│
├── tests/
│   └── test_pipeline.py     # 18 unit + integration tests
│
├── .env.example
├── requirements.txt
└── README.md
```

---

## 🧪 Tests

```bash
pytest tests/ -v
```

18 tests covering: crawler date filtering, topic relevance, HTML cleaning, TF-IDF extraction, MMR ranking, report structure validation, Markdown rendering, pipeline smoke test with mocked network.

---

## 🌐 CLI Options

```
python app/main_cli.py [OPTIONS]

  --api-key     Gemini API key (or GEMINI_API_KEY env var)
  --days        Lookback window in days (default: 7)
  --top-k       Articles used for summarization (default: 12)
  --no-scrape   Skip body scraping for faster runs
  --output-md   Markdown report path (default: reports/weekly_report.md)
  --output-json JSON report path (default: reports/weekly_report.json)
```

---

## 🔑 API Key

| Provider | Free Tier | How to get |
|----------|-----------|-----------|
| **Google Gemini** ✅ | Yes (Gemini 1.5 Flash – free) | [aistudio.google.com](https://aistudio.google.com/apikey) |
| **None** ✅ | Always | Extractive fallback, no signup needed |

---

## 🛠️ Tech Stack

| Layer | Technology | Role |
|-------|-----------|------|
| Language | Python 3.10+ | Core |
| RSS Parsing | `feedparser` | Structured news ingestion |
| Scraping | `httpx` + `beautifulsoup4` | Article body extraction |
| Classic ML | `scikit-learn` TF-IDF | Statistical keyword extraction |
| Embeddings | `sentence-transformers` (multilingual) | Semantic article representation |
| Vector Search | `FAISS` (CPU, cosine) | Fast similarity retrieval |
| Diversity | MMR algorithm | Avoids near-duplicate articles/keywords |
| LLM | Google Gemini 1.5 Flash via `LangChain` | Executive summary generation |
| Web UI | `Streamlit` | Interactive browser interface |
| Testing | `pytest` | Unit + integration coverage |
