# 📰 AI News Assistant – Weekly Technology Intelligence System

> **Candidate:** Trần Lê Hoàng Bảo &nbsp;|&nbsp; **Role:** AI Engineer Intern – Technical Assessment &nbsp;|&nbsp; **PCA Company Services**

An end-to-end **AI-powered news intelligence system** that automatically collects, filters, ranks, and summarizes Vietnamese technology news into a structured weekly digest — available via both a **CLI backend** and an **interactive Streamlit web UI**.

---

## ✨ Live Demo Preview & Results

Hệ thống cung cấp trải nghiệm liền mạch giữa giao diện Web và dòng lệnh:

| Web UI (Streamlit) | CLI Output |
|---|---|
| Nhập API key → Click → Xem báo cáo ngay trên browser | Chạy ngầm → Xuất file `.md` + `.json` |

### 📊 Actual Run Metrics (April 25, 2026)

| Metric | Result |
|--------|--------|
| 📰 Articles fetched | **74 bài** từ VnExpress, Thanh Niên, Tuổi Trẻ |
| 📄 Articles used for summary | **12 bài** (MMR selected) |
| 🔑 Keywords extracted | **10 từ khóa** trending |
| ⏱️ Processing time | **~40 giây** end-to-end |

---

### Trending Keywords (actual output)
`#công nghệ` `#google` `#iphone` `#trung tâm` `#camera` `#ultra` `#khả năng` `#chip` `#hiện` `#máy`

### Highlighted News (actual output)
```
[1] TP HCM hút 1,23 tỷ USD đầu tư vào AI, y sinh, pin thông minh
    → https://vnexpress.net/tp-hcm-hut-1-23-ty-usd-dau-tu-vao-ai...

[2] Vingroup phát triển ngôn ngữ LLM trong chiến lược AI
    → https://vnexpress.net/vingroup-phat-trien-ngon-ngu-llm...

[3] Mô hình iPhone gập so dáng cùng thiết bị Apple
    → https://vnexpress.net/...

[4] Claude Mythos - 'siêu hacker' khiến Anthropic chưa dám thương mại hóa
    → https://vnexpress.net/claude-mythos-sieu-hacker...

[5] 'Năng lực bảo vệ chưa theo kịp nhận thức an toàn dữ liệu'
[6] Trí tuệ nhân tạo 'vận hành ngược' tại các nhà máy AI
```

---

## 🏗️ System Architecture

```text
┌─────────────────────────────────────────────────────────────────┐
│               AI NEWS ASSISTANT  –  PIPELINE                                       │
│                                                                                    │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────────────┐       │
│  │   CRAWLER   │──▶│      INDEXER     │──▶│      KEYWORD               │       │
│  │             │    │                  │    │                            │       │
│  │  feedparser │    │    sentence-     │    │   Stage 1: TF-IDF          │       │
│  │    httpx    │    │   transformers   │    │   Stage 2: FAISS MMR       │       │
│  │     bs4     │    │    + FAISS       │    │   Stage 3: LLM Refine      │       │
│  │             │    │    IndexFlatIP   │    │                            │       │
│  │  VnExpress  │    │                  │    └──────────┬───────────┘       │
│  │  ThanhNien  │    │    MMR select    │                  │                       │
│  │   TuoiTre   │    │      top-K       │                  ▼                      │
│  └──────────┘    └──────────────┘    ┌──────────────────────┐       │
│         │                                    │         SUMMARIZER         │       │
│         ▼                                   │                            │       │
│  data/raw_articles.json                      │       Gemini 2.0 Flash     │       │
│                                              │         (LangChain)        │       │
│                                              │     + extractive fallback  │       │
│                                              └──────────┬───────────┘       │
│                                                    │                               │
│                              ┌────────────────┴──────────┐                 │
│                              │              OUTPUT               │                 │
│                              │       CLI → .md + .json files    │                 │
│                              │       UI  → Streamlit browser    │                 │
│                              └───────────────────────────┘                 │
└─────────────────────────────────────────────────────────────────┘
```

**Pipeline stages:**

| # | Module | Technology | What it does |
|---|--------|-----------|-------------|
| 1 | `crawler.py` | feedparser + httpx + BeautifulSoup | Parse RSS, filter 7 days, scrape body, deduplicate |
| 2 | `indexer.py` | sentence-transformers + FAISS | Embed articles → MMR retrieval for top-K diverse articles |
| 3 | `kw_extractor.py` | scikit-learn + FAISS + Gemini | TF-IDF → MMR ranking → LLM editorial refine |
| 4 | `summarizer.py` | LangChain + Gemini 2.0 Flash | Executive summary + highlighted news (structured JSON) |
| 5 | `pipeline.py` | Python orchestrator | Ties all stages; used by both CLI and UI |

---

## 🚀 Quick Start

### 1. Clone & install

```bash
git clone https://github.com/hoangbaoro2003/news-ai-assistant.git
cd news-ai-assistant

python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

pip install -r requirements.txt
```

### 2. Configure API key

```bash
copy .env.example .env
# Mở .env và điền GEMINI_API_KEY
# Lấy key miễn phí tại: https://aistudio.google.com/apikey
```

> **Không có API key?** Hệ thống vẫn tự động chuyển sang chế độ Extractive Mode — chạy pipeline đầy đủ mà không cần gọi Gemini API.

### 3. Run

**Mode A – Streamlit Web UI (recommended for demo)**
```bash
streamlit run app/ui.py
# → Mở trình duyệt tại http://localhost:8501
```

**Mode B – CLI (for backend / automation)**
```bash
# Extractive mode (không cần API key)
python app/main_cli.py

# Với Gemini API trực tiếp
python app/main_cli.py --api-key AIza...

# Chạy với tuỳ chỉnh cấu hình
python app/main_cli.py --days 7 --top-k 12 --output-md reports/report.md
```

---

## 📁 Project Structure

```text
news-ai-assistant/
├── app/
│   ├── __init__.py
│   ├── crawler.py        # RSS collection + scraping + topic filter
│   ├── indexer.py        # FAISS vector index + MMR article retrieval
│   ├── kw_extractor.py   # TF-IDF → MMR → LLM keyword extraction
│   ├── summarizer.py     # Gemini report generation + extractive fallback
│   ├── pipeline.py       # Central orchestrator (used by CLI + UI)
│   ├── main_cli.py       # CLI entry point → exports .md + .json
│   └── ui.py             # Streamlit web interface
│
├── data/
│   └── raw_articles.json     # Auto-saved raw crawl output
│
├── reports/
│   ├── weekly_report.md      # Generated Markdown report
│   ├── weekly_report.json    # Generated JSON report
│   └── sample_report.json    # Pre-generated demo output
│
├── tests/
│   └── test_pipeline.py      # 22 unit + integration tests
│
├── .env.example
├── requirements.txt
└── README.md
```

---

## 🧪 Tests

Hệ thống được bao phủ bởi 22 bài test (unit + integration) kiểm tra các chức năng: crawler date filtering, topic relevance, HTML cleaning, TF-IDF extraction, MMR ranking, report structure validation, và pipeline smoke test.

```bash
python -m pytest tests/ -v
```

**Test Results:**
```text
platform win32 -- Python 3.14.4, pytest-9.0.3

22 passed, 3 warnings in 78.53s ✅

TestCrawler    (9 tests)  → All PASSED
TestKeyword    (4 tests)  → All PASSED
TestSummarizer (5 tests)  → All PASSED
TestIndexer    (2 tests)  → All PASSED
TestPipeline   (2 tests)  → All PASSED
```

---

## 🌐 CLI Options

```text
python app/main_cli.py [OPTIONS]

  --api-key     Gemini API key (hoặc GEMINI_API_KEY env var)
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
| **Google Gemini** ✅ | Yes (Gemini 2.0 Flash) | [aistudio.google.com](https://aistudio.google.com/apikey) |
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
| LLM | Google Gemini 2.0 Flash via `LangChain` | Executive summary generation |
| Web UI | `Streamlit` | Interactive browser interface |
| Testing | `pytest` (22 tests) | Unit + integration coverage |
