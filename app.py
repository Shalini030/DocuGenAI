import streamlit as st
from model import generate_documentation, generate_readme
from utils import generate_pdf
import zipfile
import io
import re
import math
from collections import Counter
from rouge_score import rouge_scorer

# ── SCORING HELPERS ────────────────────────────────────────────────────────────

def _tokenize(text: str):
    return re.findall(r'\b\w+\b', text.lower())

def compute_rouge(reference: str, hypothesis: str):
    scorer = rouge_scorer.RougeScorer(['rouge1', 'rougeL'], use_stemmer=True)
    scores = scorer.score(reference, hypothesis)
    return {
        'rouge1': round(scores['rouge1'].fmeasure * 100, 1),
        'rougeL': round(scores['rougeL'].fmeasure * 100, 1),
    }

def compute_bleu(reference: str, hypothesis: str, max_n: int = 4) -> float:
    ref_tokens = _tokenize(reference)
    hyp_tokens = _tokenize(hypothesis)
    if not hyp_tokens or not ref_tokens:
        return 0.0
    scores = []
    for n in range(1, max_n + 1):
        ref_ngrams = Counter(tuple(ref_tokens[i:i+n]) for i in range(len(ref_tokens) - n + 1))
        hyp_ngrams = Counter(tuple(hyp_tokens[i:i+n]) for i in range(len(hyp_tokens) - n + 1))
        clip  = sum(min(c, ref_ngrams[g]) for g, c in hyp_ngrams.items())
        total = max(sum(hyp_ngrams.values()), 1)
        scores.append(clip / total if total else 0)
    if not any(scores):
        return 0.0
    log_avg = sum(math.log(s) if s > 0 else -999 for s in scores) / max_n
    bp = min(1.0, math.exp(1 - len(ref_tokens) / max(len(hyp_tokens), 1)))
    return round(bp * math.exp(log_avg) * 100, 1)

def score_label(val: float):
    """Return (label, color) based on score value (0-100)."""
    if val >= 70:
        return "Excellent", "#2ecc8f"
    elif val >= 45:
        return "Good", "#00bcd4"
    elif val >= 25:
        return "Fair", "#f0a500"
    else:
        return "Low", "#e05c5c"

# ── PAGE CONFIG ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="DocuGen AI", layout="wide", page_icon="📄")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.stApp {
    background-color: #0b1120;
    background-image:
        radial-gradient(ellipse 65% 55% at 98% 100%, rgba(13,90,80,0.38) 0%, transparent 68%),
        radial-gradient(ellipse 35% 35% at 2% 2%,   rgba(10,25,50,0.55) 0%,  transparent 60%);
    min-height: 100vh;
}

#MainMenu, footer, header { visibility: hidden; }

.block-container {
    padding: 2.5rem 2rem 4rem 2rem;
    max-width: 860px;
    margin: 0 auto;
}

/* ── HERO ── */
.hero { text-align: center; padding: 2.2rem 0 1.8rem 0; }
.hero h1 {
    font-size: 2.9rem; font-weight: 700;
    margin: 0 0 0.5rem 0; letter-spacing: -0.5px; line-height: 1.1;
}
.hero h1 .docu { color: #2ecc8f; }
.hero h1 .rest { color: #ffffff; }
.hero p { color: #8896a5; font-size: 1rem; margin: 0; font-weight: 400; }

/* ── CARD ── */
.card {
    background: #111827; border: 1px solid #1e2d3d;
    border-radius: 14px; padding: 1.6rem 1.75rem; margin-bottom: 1.1rem;
}
.card-title { color: #ffffff; font-weight: 600; font-size: 0.97rem; margin-bottom: 1rem; }

/* ── METRIC CARDS ── */
.metrics-row {
    display: flex; gap: 1rem; margin-bottom: 1.1rem;
}
.metric-card {
    flex: 1; background: #111827; border: 1px solid #1e2d3d;
    border-radius: 14px; padding: 1.3rem 1.2rem 1.1rem 1.2rem;
    text-align: center; position: relative; overflow: hidden;
}
.metric-card::before {
    content: ''; position: absolute; top: 0; left: 0; right: 0;
    height: 3px; border-radius: 14px 14px 0 0;
    background: var(--accent);
}
.metric-name {
    color: #8896a5; font-size: 0.75rem; font-weight: 600;
    letter-spacing: 0.1em; text-transform: uppercase; margin-bottom: 0.5rem;
}
.metric-value {
    font-size: 2rem; font-weight: 700; color: var(--accent);
    line-height: 1; margin-bottom: 0.35rem;
}
.metric-suffix { font-size: 1rem; font-weight: 500; }
.metric-badge {
    display: inline-block; font-size: 0.7rem; font-weight: 600;
    letter-spacing: 0.05em; padding: 0.18rem 0.6rem; border-radius: 20px;
    background: rgba(255,255,255,0.06); color: var(--accent);
    border: 1px solid rgba(255,255,255,0.1);
}
.metric-desc {
    color: #4a5a6e; font-size: 0.72rem; margin-top: 0.5rem; line-height: 1.4;
}

/* ── METRICS SECTION LABEL ── */
.metrics-label {
    color: #ffffff; font-weight: 600; font-size: 0.97rem;
    margin-bottom: 0.85rem; display: flex; align-items: center; gap: 0.5rem;
}
.metrics-sublabel {
    color: #8896a5; font-size: 0.78rem; font-weight: 400; margin-bottom: 1rem;
}

/* ── FILE UPLOADER ── */
[data-testid="stFileUploader"] section {
    background: #131f2e !important; border: 2px dashed #2e4060 !important;
    border-radius: 10px !important; padding: 2.4rem 1rem !important;
}
[data-testid="stFileUploader"] section:hover { border-color: #2ecc8f !important; }
[data-testid="stFileUploaderDropzoneInstructions"] div span {
    color: #8896a5 !important; font-family: 'Inter', sans-serif !important; font-size: 0.88rem !important;
}
[data-testid="stFileUploaderDropzoneInstructions"] div span:first-child {
    color: #ffffff !important; font-weight: 700 !important; font-size: 1rem !important;
}
[data-testid="stFileUploader"] section button { display: none !important; }

.file-info { color: #e2e8f0; font-size: 0.88rem; margin-top: 0.75rem; font-weight: 400; }

/* ── BUTTONS ── */
div[data-testid="stButton"] > button {
    background: linear-gradient(90deg, #2ecc8f 0%, #00bcd4 100%) !important;
    color: #0b1120 !important; font-family: 'Inter', sans-serif !important;
    font-weight: 700 !important; font-size: 0.93rem !important;
    border: none !important; border-radius: 8px !important;
    padding: 0.6rem 1.5rem !important; cursor: pointer !important;
    box-shadow: 0 2px 18px rgba(46,204,143,0.22) !important;
    transition: opacity 0.15s, transform 0.1s !important; letter-spacing: 0.01em !important;
}
div[data-testid="stButton"] > button:hover { opacity: 0.88 !important; transform: translateY(-1px) !important; }
div[data-testid="stButton"] > button:disabled {
    background: #1e2d3d !important; color: #3a5068 !important;
    box-shadow: none !important; cursor: not-allowed !important;
}

/* ── EXPANDER ── */
[data-testid="stExpander"] {
    background: #111827 !important; border: 1px solid #1e2d3d !important;
    border-radius: 10px !important; margin-bottom: 1.1rem !important;
}
[data-testid="stExpander"] summary {
    color: #8896a5 !important; font-size: 0.9rem !important;
    font-family: 'Inter', sans-serif !important; font-weight: 500 !important;
}
[data-testid="stExpander"] summary:hover { color: #ffffff !important; }

/* ── TEXT INPUTS ── */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    background: #0f1a2b !important; border: 1px solid #1e2d3d !important;
    border-radius: 8px !important; color: #ffffff !important;
    font-family: 'Inter', sans-serif !important; font-size: 0.88rem !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #2ecc8f !important; box-shadow: 0 0 0 2px rgba(46,204,143,0.12) !important;
}
.stTextInput label, .stTextArea label { color: #8896a5 !important; font-size: 0.82rem !important; }

/* ── TABS ── */
.stTabs [data-baseweb="tab-list"] {
    background: #0f1a2b !important; border-radius: 8px !important;
    padding: 3px !important; gap: 3px !important; border: 1px solid #1e2d3d !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important; color: #8896a5 !important;
    font-family: 'Inter', sans-serif !important; font-weight: 600 !important;
    font-size: 0.88rem !important; border-radius: 6px !important; padding: 0.4rem 1.1rem !important;
}
.stTabs [aria-selected="true"] { background: rgba(46,204,143,0.14) !important; color: #2ecc8f !important; }

/* ── DOWNLOAD BUTTONS ── */
.stDownloadButton > button {
    background: rgba(46,204,143,0.1) !important; border: 1px solid rgba(46,204,143,0.3) !important;
    color: #2ecc8f !important; font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important; font-size: 0.86rem !important;
    border-radius: 8px !important; width: 100% !important; padding: 0.5rem 1rem !important;
    transition: background 0.15s !important;
}
.stDownloadButton > button:hover { background: rgba(46,204,143,0.2) !important; }

/* ── SPINNER / ALERTS ── */
.stSpinner > div { border-top-color: #2ecc8f !important; }
.stAlert { border-radius: 8px !important; font-family: 'Inter', sans-serif !important; }
div[data-testid="stNotification"] {
    background: rgba(46,204,143,0.08) !important; border-color: rgba(46,204,143,0.3) !important;
}

/* ── MARKDOWN OUTPUT ── */
.element-container .stMarkdown p,
.element-container .stMarkdown li { color: #c8d6e0 !important; font-size: 0.9rem !important; line-height: 1.7 !important; }
.element-container .stMarkdown h1,
.element-container .stMarkdown h2,
.element-container .stMarkdown h3 { color: #ffffff !important; }
.element-container .stMarkdown code {
    background: #0f1a2b !important; color: #2ecc8f !important;
    border-radius: 4px !important; padding: 0.1em 0.4em !important; font-size: 0.83em !important;
}
.element-container .stMarkdown pre {
    background: #0f1a2b !important; border: 1px solid #1e2d3d !important;
    border-radius: 8px !important; padding: 1rem !important;
}
</style>
""", unsafe_allow_html=True)

# ── HERO ───────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <h1><span class="docu">Docu</span><span class="rest">Gen AI</span></h1>
  <p>Turn source files into clean technical docs in one click.</p>
</div>
""", unsafe_allow_html=True)

# ── UPLOAD CARD ────────────────────────────────────────────────────────────────
st.markdown('<div class="card"><div class="card-title">Upload Source Files</div>', unsafe_allow_html=True)

uploaded_files = st.file_uploader(
    "Drop files here",
    type=["py", "js", "ts", "jsx", "tsx", "html", "css", "java", "c", "cpp",
          "cs", "go", "rs", "php", "rb", "kt", "swift", "txt", "md", "zip"],
    accept_multiple_files=True,
    label_visibility="collapsed",
)

if uploaded_files:
    total_kb = sum(f.size for f in uploaded_files) // 1024
    st.markdown(
        f'<p class="file-info">Selected: {len(uploaded_files)} file(s), {total_kb} KB total</p>',
        unsafe_allow_html=True,
    )

st.markdown('</div>', unsafe_allow_html=True)

# ── OPTIONAL OVERRIDES ─────────────────────────────────────────────────────────
with st.expander("✏️  Optional: Override Project Info"):
    custom_name = st.text_input("Project Title", placeholder="Leave blank to auto-detect")
    custom_desc = st.text_area("Additional Context", placeholder="e.g. Flask REST API for inventory management…", height=85)

st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)

# ── GENERATE BUTTON ────────────────────────────────────────────────────────────
generate = st.button("Generate README", disabled=not uploaded_files, use_container_width=True)

# ── GENERATION ─────────────────────────────────────────────────────────────────
if generate:
    all_code = {}

    for uploaded_file in uploaded_files:
        filename = uploaded_file.name
        if filename.endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(uploaded_file.read()), "r") as z:
                for name in z.namelist():
                    if name.endswith("/") or "__pycache__" in name or name.startswith("."):
                        continue
                    try:
                        content = z.read(name).decode("utf-8", errors="ignore")
                        if content.strip():
                            all_code[name] = content
                    except Exception:
                        pass
        else:
            try:
                content = uploaded_file.read().decode("utf-8", errors="ignore")
                all_code[filename] = content
            except Exception:
                st.warning(f"Could not read {filename}, skipping.")

    if not all_code:
        st.error("No readable files found. Please upload valid text/code files.")
        st.stop()

    combined_code = ""
    for fname, code in all_code.items():
        combined_code += f"\n\n### File: {fname}\n```\n{code[:3000]}\n```"

    project_name = custom_name.strip() if custom_name.strip() else None
    extra_context = custom_desc.strip() if custom_desc.strip() else ""

    with st.spinner("Analyzing your code and generating documents…"):
        report = generate_documentation(combined_code, project_name, extra_context)
        readme = generate_readme(combined_code, project_name, extra_context)

    # ── COMPUTE METRICS ────────────────────────────────────────────────────────
    # Reference = raw source code; Hypothesis = generated docs (report + readme)
    reference_text  = " ".join(all_code.values())
    hypothesis_text = report + " " + readme

    rouge_scores = compute_rouge(reference_text, hypothesis_text)
    bleu_score   = compute_bleu(reference_text, hypothesis_text)

    r1_val,  r1_label,  r1_color  = rouge_scores['rouge1'], *score_label(rouge_scores['rouge1'])
    rl_val,  rl_label,  rl_color  = rouge_scores['rougeL'], *score_label(rouge_scores['rougeL'])
    bl_val,  bl_label,  bl_color  = bleu_score,             *score_label(bleu_score)

    st.success("✅ Documents generated successfully!")

    # ── METRIC CARDS ──────────────────────────────────────────────────────────
    st.markdown("""
    <div class="card">
      <div class="card-title">📊 Quality Metrics</div>
      <p class="metrics-sublabel">Scores measure how well the AI captured terminology &amp; structure from your source code.</p>
    </div>
    """, unsafe_allow_html=True)

    # Remove the wrapping card div, render metrics as 3 columns
    m1, m2, m3 = st.columns(3)

    with m1:
        st.markdown(f"""
        <div class="metric-card" style="--accent:{r1_color};">
            <div class="metric-name">ROUGE-1</div>
            <div class="metric-value">{r1_val}<span class="metric-suffix">%</span></div>
            <div class="metric-badge">{r1_label}</div>
            <div class="metric-desc">Unigram overlap between source code and generated docs</div>
        </div>
        """, unsafe_allow_html=True)

    with m2:
        st.markdown(f"""
        <div class="metric-card" style="--accent:{rl_color};">
            <div class="metric-name">ROUGE-L</div>
            <div class="metric-value">{rl_val}<span class="metric-suffix">%</span></div>
            <div class="metric-badge">{rl_label}</div>
            <div class="metric-desc">Longest common subsequence — measures fluency &amp; order</div>
        </div>
        """, unsafe_allow_html=True)

    with m3:
        st.markdown(f"""
        <div class="metric-card" style="--accent:{bl_color};">
            <div class="metric-name">BLEU</div>
            <div class="metric-value">{bl_val}<span class="metric-suffix">%</span></div>
            <div class="metric-badge">{bl_label}</div>
            <div class="metric-desc">N-gram precision score (1–4 grams) with brevity penalty</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)

    # ── OUTPUT CARD ──────────────────────────────────────────────────────────
    st.markdown('<div class="card"><div class="card-title">Generated Documentation:</div>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["📘  Project Report", "📗  GitHub README"])
    with tab1:
        st.markdown(report)
    with tab2:
        st.markdown(readme)

    st.markdown('</div>', unsafe_allow_html=True)

    # ── DOWNLOADS ────────────────────────────────────────────────────────────
    with st.spinner("Generating PDFs…"):
        report_pdf = generate_pdf(report, "project_report.pdf")
        readme_pdf = generate_pdf(readme, "readme.pdf")

    st.markdown('<div class="card"><div class="card-title">⬇️ Download</div>', unsafe_allow_html=True)

    dl1, dl2, dl3 = st.columns(3)
    with dl1:
        with open(report_pdf, "rb") as f:
            st.download_button("📥 Report PDF", f, file_name="project_report.pdf", mime="application/pdf")
    with dl2:
        with open(readme_pdf, "rb") as f:
            st.download_button("📥 README PDF", f, file_name="readme.pdf", mime="application/pdf")
    with dl3:
        st.download_button("📥 README.md", readme, file_name="README.md", mime="text/markdown")

    st.markdown('</div>', unsafe_allow_html=True)
