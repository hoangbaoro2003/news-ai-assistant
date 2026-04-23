"""
ui.py – Streamlit Web UI for the AI News Assistant.

Chạy: streamlit run app/ui.py

Giao diện tương tác cho phép:
  - Nhập Gemini API key
  - Chọn số ngày lookback
  - Xem pipeline progress theo thời gian thực
  - Đọc báo cáo đẹp ngay trên browser
  - Download báo cáo dạng Markdown
"""

import sys
import os
import time
from pathlib import Path

# Allow running as `streamlit run app/ui.py` from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI News Assistant",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 1.5rem 0 0.5rem 0;
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        border-radius: 12px;
        margin-bottom: 1.5rem;
        color: white;
    }
    .kw-tag {
        display: inline-block;
        background: #0f3460;
        color: #00d4ff;
        border-radius: 20px;
        padding: 4px 14px;
        margin: 4px;
        font-size: 0.85rem;
        font-weight: 600;
    }
    .highlight-card {
        border-left: 4px solid #0f3460;
        background: #f8f9fa;
        padding: 1rem 1.2rem;
        border-radius: 0 8px 8px 0;
        margin-bottom: 1rem;
    }
    .highlight-card h4 { margin: 0 0 0.4rem 0; color: #1a1a2e; }
    .highlight-card p  { margin: 0 0 0.3rem 0; color: #333; font-size: 0.92rem; }
    .meta-tag { color: #666; font-size: 0.82rem; }
    .stat-box {
        background: #f0f4ff;
        border-radius: 8px;
        padding: 0.8rem 1rem;
        text-align: center;
    }
    .stat-box .number { font-size: 1.8rem; font-weight: 700; color: #0f3460; }
    .stat-box .label  { font-size: 0.8rem; color: #666; }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>📰 AI News Assistant</h1>
    <p style="color:#aaa; margin:0;">
        Hệ thống tự động thu thập · trích xuất từ khóa · tổng hợp tin tức công nghệ hàng tuần<br>
        <small>RSS Crawling → TF-IDF + FAISS MMR → Gemini LLM → Báo cáo cấu trúc</small>
    </p>
</div>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Cấu hình")

    api_key = st.text_input(
        "🔑 Gemini API Key",
        type="password",
        value=os.getenv("GEMINI_API_KEY", ""),
        placeholder="AIza...",
        help="Lấy miễn phí tại aistudio.google.com — để trống để dùng extractive mode",
    )

    st.markdown("---")
    days_back = st.slider("📅 Khoảng thời gian (ngày)", min_value=1, max_value=14, value=7)
    top_k = st.slider("📄 Số bài dùng cho summary", min_value=5, max_value=20, value=12)
    scrape = st.checkbox("🔍 Scrape nội dung bài (chậm hơn, phong phú hơn)", value=True)

    st.markdown("---")
    st.markdown("""
    **🏗️ Pipeline:**
    1. `crawler.py` → RSS + scrape
    2. `indexer.py` → FAISS + MMR
    3. `keyword.py` → TF-IDF + MMR + LLM
    4. `summarizer.py` → Gemini report
    """)
    st.markdown("---")
    st.caption("**Nguồn:** VnExpress · Thanh Niên · Tuổi Trẻ")
    st.caption("**Chủ đề:** Technology 🖥️")

# ── Main trigger ──────────────────────────────────────────────────────────────
col_btn, col_info = st.columns([1, 3])
with col_btn:
    run_btn = st.button("🚀 Tạo báo cáo tuần", use_container_width=True, type="primary")
with col_info:
    if not api_key:
        st.info("💡 Không có API key → sẽ dùng **Extractive Mode** (không cần Gemini)")

if run_btn:
    start_time = time.time()

    # Progress logs
    log_placeholder = st.empty()
    logs: list[str] = []

    def progress_cb(msg: str):
        logs.append(msg)
        log_placeholder.markdown(
            "\n".join(f"- {m}" for m in logs[-6:]),
        )

    with st.status("🔄 Đang chạy AI Pipeline…", expanded=True) as status:
        from app.pipeline import run as run_pipeline
        try:
            result = run_pipeline(
                days_back=days_back,
                top_k=top_k,
                api_key=api_key,
                scrape_content=scrape,
                progress_cb=progress_cb,
            )
            status.update(label="✅ Pipeline hoàn tất!", state="complete", expanded=False)
        except Exception as exc:
            status.update(label=f"❌ Lỗi: {exc}", state="error")
            st.error(str(exc))
            st.stop()

    elapsed = round(time.time() - start_time, 1)
    log_placeholder.empty()

    # ── Stats row ─────────────────────────────────────────────────────────────
    st.markdown("---")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""<div class="stat-box">
            <div class="number">{result.articles_total}</div>
            <div class="label">Bài thu thập</div></div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class="stat-box">
            <div class="number">{result.articles_used}</div>
            <div class="label">Bài dùng cho summary</div></div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class="stat-box">
            <div class="number">{len(result.keywords)}</div>
            <div class="label">Keywords</div></div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""<div class="stat-box">
            <div class="number">{elapsed}s</div>
            <div class="label">Thời gian xử lý</div></div>""", unsafe_allow_html=True)

    # ── Trending Keywords ──────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("🔥 Trending Keywords")
    tags_html = " ".join(f'<span class="kw-tag">#{k}</span>' for k in result.keywords)
    st.markdown(tags_html, unsafe_allow_html=True)

    # ── Executive Summary ──────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📋 Executive Summary")
    st.markdown(
        f'<div style="background:#f8f9fa;border-left:4px solid #0f3460;'
        f'padding:1rem 1.5rem;border-radius:0 8px 8px 0;font-size:1rem;line-height:1.7;">'
        f'{result.report.get("executive_summary", "")}</div>',
        unsafe_allow_html=True,
    )

    # ── Highlighted News ───────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📰 Highlighted News")

    highlights = result.report.get("highlights", [])
    col_left, col_right = st.columns(2)
    for i, item in enumerate(highlights):
        col = col_left if i % 2 == 0 else col_right
        with col:
            rank   = item.get("rank", i + 1)
            title  = item.get("title", "")
            summ   = item.get("summary", "")
            source = item.get("source", "")
            url    = item.get("source_url", "#")
            date   = item.get("published_at", "")
            st.markdown(
                f'<div class="highlight-card">'
                f'<h4>#{rank} {title}</h4>'
                f'<p>{summ}</p>'
                f'<span class="meta-tag">🏷️ {source} &nbsp;|&nbsp; 📅 {date} &nbsp;|&nbsp; '
                f'<a href="{url}" target="_blank">🔗 Xem bài gốc</a></span>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # ── Download ───────────────────────────────────────────────────────────────
    st.markdown("---")
    st.download_button(
        label="⬇️ Tải báo cáo (.md)",
        data=result.markdown.encode("utf-8"),
        file_name="weekly_tech_report.md",
        mime="text/markdown",
        use_container_width=True,
    )

# ── Empty state ───────────────────────────────────────────────────────────────
else:
    st.markdown("""
    <div style="text-align:center; padding:3rem; color:#888;">
        <div style="font-size:4rem;">🤖</div>
        <h3 style="color:#555;">Nhấn <em>Tạo báo cáo tuần</em> để bắt đầu</h3>
        <p>Hệ thống sẽ tự động thu thập tin tức công nghệ 7 ngày qua<br>
        từ VnExpress, Thanh Niên, Tuổi Trẻ và tổng hợp thành báo cáo có cấu trúc.</p>
    </div>
    """, unsafe_allow_html=True)
