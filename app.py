import streamlit as st
from model import generate_documentation, generate_readme, answer_code_question, evaluate_scores, evaluate_llm_metrics
from utils import generate_pdf
from analyzer import detect_project_type, code_quality_score, build_mermaid_diagram
import zipfile
import io
import re

st.set_page_config(page_title="AI Project Report Generator", layout="wide", page_icon="📄")

# ─── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Space Grotesk', sans-serif;
}

.stat-grid {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 14px;
    margin: 20px 0 28px 0;
}
.stat-card {
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
    border: 1px solid #334155;
    border-radius: 14px;
    padding: 18px 14px;
    text-align: center;
    position: relative;
    overflow: hidden;
    transition: transform 0.2s, border-color 0.2s;
}
.stat-card:hover {
    transform: translateY(-3px);
    border-color: #6366f1;
}
.stat-card::before {
    content: '';
    position: absolute;
    top: -30px; right: -30px;
    width: 80px; height: 80px;
    border-radius: 50%;
    opacity: 0.08;
}
.stat-card.files::before  { background: #6366f1; }
.stat-card.lines::before  { background: #06b6d4; }
.stat-card.funcs::before  { background: #10b981; }
.stat-card.langs::before  { background: #f59e0b; }
.stat-card.chars::before  { background: #ec4899; }

.stat-icon  { font-size: 22px; margin-bottom: 6px; }
.stat-value { font-size: 28px; font-weight: 700; color: #f1f5f9; line-height: 1; }
.stat-label { font-size: 11px; color: #94a3b8; margin-top: 4px; letter-spacing: 0.05em; text-transform: uppercase; }

.lang-badges { display: flex; flex-wrap: wrap; gap: 8px; margin: 10px 0 24px 0; }
.lang-badge {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 20px;
    padding: 4px 12px;
    font-size: 12px;
    font-weight: 600;
    color: #a5b4fc;
    font-family: 'JetBrains Mono', monospace;
}

.rtype-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin: 12px 0 20px 0;
}
.rtype-card {
    background: #0f172a;
    border: 2px solid #1e293b;
    border-radius: 12px;
    padding: 16px 12px;
    text-align: center;
    cursor: pointer;
    transition: all 0.2s;
}
.rtype-card.selected { border-color: #6366f1; background: #1e1b4b; }
.rtype-card:hover { border-color: #4f46e5; }
.rtype-emoji { font-size: 26px; }
.rtype-label { font-size: 12px; font-weight: 600; color: #cbd5e1; margin-top: 6px; }
.rtype-desc  { font-size: 10px; color: #64748b; margin-top: 2px; }

.section-header {
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #6366f1;
    margin: 24px 0 10px 0;
    display: flex;
    align-items: center;
    gap: 8px;
}
.section-header::after {
    content: '';
    flex: 1;
    height: 1px;
    background: linear-gradient(90deg, #334155, transparent);
}

.quality-bar-wrap {
    background: #1e293b;
    border-radius: 999px;
    height: 10px;
    width: 100%;
    margin: 4px 0 2px 0;
    overflow: hidden;
}
.quality-bar-fill {
    height: 100%;
    border-radius: 999px;
    transition: width 0.6s ease;
}
.quality-pill {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 700;
    font-family: 'JetBrains Mono', monospace;
}

.ptype-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: linear-gradient(135deg, #312e81, #1e1b4b);
    border: 1px solid #4f46e5;
    border-radius: 8px;
    padding: 6px 14px;
    font-size: 13px;
    font-weight: 600;
    color: #a5b4fc;
    margin-bottom: 16px;
}

.chat-user {
    background: #1e293b;
    border-left: 3px solid #6366f1;
    border-radius: 0 10px 10px 0;
    padding: 10px 14px;
    margin: 8px 0;
    font-size: 14px;
    color: #e2e8f0;
}
.chat-ai {
    background: #0f172a;
    border-left: 3px solid #10b981;
    border-radius: 0 10px 10px 0;
    padding: 10px 14px;
    margin: 8px 0;
    font-size: 14px;
    color: #cbd5e1;
}

.score-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 10px;
    margin: 14px 0 20px 0;
}
.score-card {
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 10px;
    padding: 12px 8px;
    text-align: center;
}
.score-card:hover { border-color: #6366f1; }
.score-metric { font-size: 18px; font-weight: 700; color: #f1f5f9; font-family: 'JetBrains Mono', monospace; }
.score-label  { font-size: 10px; color: #64748b; margin-top: 3px; letter-spacing: 0.06em; text-transform: uppercase; }
.score-badge  {
    display: inline-block;
    font-size: 9px;
    font-weight: 700;
    padding: 1px 6px;
    border-radius: 999px;
    margin-top: 4px;
    font-family: 'JetBrains Mono', monospace;
}
</style>
""", unsafe_allow_html=True)

# ─── Header ────────────────────────────────────────────────────────────────────
st.markdown("## 📄 AI Project Report Generator")
st.markdown("<p style='color:#94a3b8;margin-top:-10px'>Upload your code → get a full report + GitHub README instantly</p>", unsafe_allow_html=True)
st.divider()

# ─── File Upload ───────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">📁 Upload Files</div>', unsafe_allow_html=True)

uploaded_files = st.file_uploader(
    "Drag & drop code files or a .zip of your project",
    type=["py","js","ts","jsx","tsx","html","css","java","c","cpp",
          "cs","go","rs","php","rb","kt","swift","txt","md","zip"],
    accept_multiple_files=True,
    label_visibility="collapsed"
)

# ─── KEY FIX: Parse files into session_state so they survive reruns ────────────
LANG_MAP = {
    "py":"Python","js":"JavaScript","ts":"TypeScript","jsx":"React JSX",
    "tsx":"React TSX","html":"HTML","css":"CSS","java":"Java","c":"C",
    "cpp":"C++","cs":"C#","go":"Go","rs":"Rust","php":"PHP",
    "rb":"Ruby","kt":"Kotlin","swift":"Swift","md":"Markdown","txt":"Text"
}

# Build a stable key from uploaded file names+sizes to detect changes
if uploaded_files:
    upload_signature = sorted([(f.name, f.size) for f in uploaded_files])
else:
    upload_signature = []

# Only re-parse when the uploaded files actually change
if upload_signature != st.session_state.get("upload_signature"):
    parsed = {}
    if uploaded_files:
        for uf in uploaded_files:
            raw = uf.read()  # read ONCE here, immediately
            if uf.name.endswith(".zip"):
                try:
                    with zipfile.ZipFile(io.BytesIO(raw), "r") as z:
                        for name in z.namelist():
                            if name.endswith("/") or "__pycache__" in name or name.startswith("."):
                                continue
                            try:
                                content = z.read(name).decode("utf-8", errors="ignore")
                                if content.strip():
                                    parsed[name] = content
                            except Exception:
                                pass
                except Exception as e:
                    st.warning(f"Could not open zip '{uf.name}': {e}")
            else:
                try:
                    content = raw.decode("utf-8", errors="ignore")
                    if content.strip():
                        parsed[uf.name] = content
                    else:
                        st.warning(f"'{uf.name}' appears empty, skipping.")
                except Exception as e:
                    st.warning(f"Could not read '{uf.name}': {e}")

    st.session_state["all_code"]          = parsed
    st.session_state["upload_signature"]  = upload_signature
    # Reset Q&A context when files change
    st.session_state["chat_history"]      = []
    st.session_state["qa_code_context"]   = ""

# Always read from session_state — survives every rerun
all_code: dict = st.session_state.get("all_code", {})

# ─── Stats Dashboard ───────────────────────────────────────────────────────────
if all_code:
    total_files = len(all_code)
    total_lines = sum(len(c.split("\n")) for c in all_code.values())
    total_chars = sum(len(c) for c in all_code.values())

    func_pattern = re.compile(
        r'^\s*(def |function |func |fn |public |private |protected |async function )',
        re.MULTILINE
    )
    total_funcs = sum(len(func_pattern.findall(c)) for c in all_code.values())

    detected_langs = {}
    for fname in all_code:
        ext = fname.rsplit(".", 1)[-1].lower() if "." in fname else ""
        lang = LANG_MAP.get(ext)
        if lang:
            detected_langs[lang] = detected_langs.get(lang, 0) + 1

    st.markdown('<div class="section-header">📊 Project Analysis</div>', unsafe_allow_html=True)

    st.markdown(f"""
    <div class="stat-grid">
        <div class="stat-card files">
            <div class="stat-icon">🗂️</div>
            <div class="stat-value">{total_files}</div>
            <div class="stat-label">Files</div>
        </div>
        <div class="stat-card lines">
            <div class="stat-icon">📝</div>
            <div class="stat-value">{total_lines:,}</div>
            <div class="stat-label">Lines of Code</div>
        </div>
        <div class="stat-card funcs">
            <div class="stat-icon">⚙️</div>
            <div class="stat-value">{total_funcs}</div>
            <div class="stat-label">Functions</div>
        </div>
        <div class="stat-card langs">
            <div class="stat-icon">🌐</div>
            <div class="stat-value">{len(detected_langs)}</div>
            <div class="stat-label">Languages</div>
        </div>
        <div class="stat-card chars">
            <div class="stat-icon">🔤</div>
            <div class="stat-value">{total_chars:,}</div>
            <div class="stat-label">Characters</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if detected_langs:
        badges = "".join(
            f'<span class="lang-badge">● {lang} <span style="color:#64748b">({count})</span></span>'
            for lang, count in sorted(detected_langs.items(), key=lambda x: -x[1])
        )
        st.markdown(f'<div class="lang-badges">{badges}</div>', unsafe_allow_html=True)

    with st.expander(f"📂 View all {total_files} detected files"):
        for fname, code in all_code.items():
            lc = len(code.split("\n"))
            st.markdown(f"`{fname}` — {lc} lines")

    # ── Project Type ──────────────────────────────────────────────────────────
    project_type, project_type_hint = detect_project_type(all_code)

    st.markdown('<div class="section-header">🔍 Project Type</div>', unsafe_allow_html=True)

    TYPE_ICONS = {
        "Flask API": "🌶️", "FastAPI Service": "⚡", "Django Web App": "🦄",
        "React App": "⚛️", "ML / Data Pipeline": "🤖", "Streamlit App": "🎈",
        "CLI Tool": "💻", "Node.js / Express": "🟩", "General Python Project": "🐍",
    }
    icon = TYPE_ICONS.get(project_type, "📦")
    st.markdown(
        f'<div class="ptype-badge">{icon} Auto-detected: <span style="color:#e0e7ff">{project_type}</span></div>',
        unsafe_allow_html=True
    )
    if project_type_hint:
        st.markdown(f"<p style='color:#64748b;font-size:12px;margin:-8px 0 12px 4px'>{project_type_hint}</p>", unsafe_allow_html=True)

    # ── Code Quality ──────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">🏆 Code Quality Score</div>', unsafe_allow_html=True)

    quality   = code_quality_score(all_code)
    score     = quality["score"]
    grade     = quality["grade"]

    GRADE_COLOR = {"A": "#10b981", "B": "#06b6d4", "C": "#f59e0b", "D": "#f97316", "F": "#ef4444"}
    bar_color   = GRADE_COLOR.get(grade, "#6366f1")

    qcol1, qcol2 = st.columns([3, 1])
    with qcol1:
        st.markdown(f"""
        <div style="margin-bottom:8px">
            <span style="font-size:13px;color:#94a3b8">Overall Score</span>
            <span style="float:right;font-size:13px;color:{bar_color};font-weight:700">{score}/100</span>
        </div>
        <div class="quality-bar-wrap">
            <div class="quality-bar-fill" style="width:{score}%;background:{bar_color}"></div>
        </div>
        """, unsafe_allow_html=True)

        for label, (s, mx, detail) in quality["breakdown"].items():
            pct = int((s / mx) * 100)
            st.markdown(f"""
            <div style="margin:6px 0 2px 0;font-size:11px;color:#94a3b8">
                {label}
                <span style="float:right;color:#64748b">{s}/{mx} — {detail}</span>
            </div>
            <div class="quality-bar-wrap">
                <div class="quality-bar-fill" style="width:{pct}%;background:{bar_color};opacity:0.7"></div>
            </div>
            """, unsafe_allow_html=True)

    with qcol2:
        st.markdown(f"""
        <div style="text-align:center;padding:20px 0">
            <div style="font-size:56px;font-weight:900;color:{bar_color};line-height:1">{grade}</div>
            <div style="font-size:11px;color:#64748b;margin-top:4px">Grade</div>
        </div>
        """, unsafe_allow_html=True)

    with st.expander("🔎 Code Smell Details"):
        for smell in quality["smells"]:
            st.markdown(f"- {smell}")

    # ── Mermaid Diagram ───────────────────────────────────────────────────────
    mermaid_src = build_mermaid_diagram(all_code)
    if mermaid_src:
        st.markdown('<div class="section-header">🗺️ Function Call Diagram</div>', unsafe_allow_html=True)
        with st.expander("📐 View auto-generated Mermaid diagram (paste into mermaid.live)"):
            st.markdown(mermaid_src)
            st.caption("💡 Copy the block above and paste it at [mermaid.live](https://mermaid.live) to view the interactive diagram.")

else:
    # Placeholders so layout doesn't collapse before upload
    project_type      = ""
    project_type_hint = ""

# ─── Report Type Selector ──────────────────────────────────────────────────────
st.markdown('<div class="section-header">📋 Report Type</div>', unsafe_allow_html=True)

REPORT_TYPES = {
    "Final Year Project Report": ("🎓", "Academic format with abstract, literature review & all standard sections"),
    "Internship Report":         ("💼", "Professional tone covering learnings, tasks & outcomes"),
    "Research Paper":            ("🔬", "IEEE/ACM style with methodology, experiments & citations"),
    "Technical Blog Post":       ("✍️",  "Casual, readable dev.to / Medium style writeup"),
}

report_type = st.radio(
    "Select report type",
    options=list(REPORT_TYPES.keys()),
    horizontal=True,
    label_visibility="collapsed"
)

emoji, desc = REPORT_TYPES[report_type]
st.markdown(f"<p style='color:#94a3b8;font-size:13px;margin:-8px 0 16px 0'>{emoji} {desc}</p>", unsafe_allow_html=True)

# ─── Optional Overrides ────────────────────────────────────────────────────────
with st.expander("✏️ Optional: Override Project Info"):
    custom_name = st.text_input("Project Title (leave blank to auto-detect)")
    custom_desc = st.text_area("Additional Context / Description (optional)")

# ─── Generate Button — ALWAYS RENDERED, never inside if all_code ───────────────
st.markdown("")
generate_btn = st.button(
    "🚀 Generate Report & README",
    disabled=(not all_code),          # greyed out until files loaded
    use_container_width=True,
    type="primary"
)

if generate_btn and all_code:
    combined_code = ""
    for fname, code in all_code.items():
        combined_code += f"\n\n### File: {fname}\n```\n{code[:3000]}\n```"

    project_name  = custom_name.strip() if custom_name.strip() else None
    extra_context = custom_desc.strip() if custom_desc.strip() else ""

    ptype      = project_type
    ptype_hint = project_type_hint

    with st.spinner(f"🤖 Generating {report_type}..."):
        report = generate_documentation(
            combined_code, project_name, extra_context, report_type,
            project_type=ptype, project_type_hint=ptype_hint
        )
        readme = generate_readme(combined_code, project_name, extra_context, project_type=ptype)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="section-header">📘 Report Preview</div>', unsafe_allow_html=True)
        st.markdown(report)
    with col2:
        st.markdown('<div class="section-header">📗 README Preview</div>', unsafe_allow_html=True)
        st.markdown(readme)

    # ── Evaluation Scores ──────────────────────────────────────────────────────
    st.markdown('<div class="section-header">📐 Model Evaluation Scores</div>', unsafe_allow_html=True)
    st.markdown(
        "<p style='color:#94a3b8;font-size:12px;margin:-8px 0 12px 0'>"
        "ROUGE &amp; BLEU measure n-gram overlap with source code. "
        "Faithfulness, Bias &amp; Fairness are computed mathematically — no LLM involved."
        "</p>",
        unsafe_allow_html=True,
    )

    def _score_color(val):
        if val >= 0.5: return "#10b981"
        if val >= 0.3: return "#f59e0b"
        return "#ef4444"

    def _score_label(val):
        if val >= 0.5: return "Good"
        if val >= 0.3: return "Fair"
        return "Low"

    with st.spinner("📊 Computing evaluation scores..."):
        report_scores = evaluate_scores(report, combined_code)
        readme_scores  = evaluate_scores(readme, combined_code)

    with st.spinner("🧮 Computing faithfulness, bias & fairness..."):
        report_llm = evaluate_llm_metrics(report, combined_code)
        readme_llm  = evaluate_llm_metrics(readme, combined_code)

    llm_scores_map = {"Report": report_llm, "README": readme_llm}

    score_tab1, score_tab2 = st.tabs(["📘 Report Scores", "📗 README Scores"])

    for tab, sc, label in [
        (score_tab1, report_scores, "Report"),
        (score_tab2, readme_scores,  "README"),
    ]:
        with tab:
            metrics = [
                ("ROUGE-1", sc["rouge1_f"], "F1-Score"),
                ("ROUGE-L", sc["rougeL_f"], "F1-Score"),
                ("BLEU",    sc["bleu"],     "4-gram"),
            ]
            cards_html = '<div class="score-grid">'
            for name, val, sublabel in metrics:
                color = _score_color(val)
                badge = _score_label(val)
                pct   = f"{val:.2%}"
                cards_html += f"""
                <div class="score-card">
                    <div class="score-metric" style="color:{color}">{pct}</div>
                    <div class="score-label">{name}</div>
                    <div style="font-size:9px;color:#475569">{sublabel}</div>
                    <span class="score-badge" style="background:{color}22;color:{color}">{badge}</span>
                </div>"""
            cards_html += "</div>"
            st.markdown(cards_html, unsafe_allow_html=True)

            st.markdown(
                "<div style='font-size:11px;color:#64748b;margin:4px 0 6px 0;letter-spacing:0.06em'>"
                "▸ LLM-AS-A-JUDGE METRICS</div>",
                unsafe_allow_html=True
            )
            lm = llm_scores_map[label]
            # Faithfulness = 1 - hallucination_rate (higher is always better, like RAGAS)
            faith_val = round(1.0 - lm["hallucination"], 2)
            bias_val  = lm["bias"]
            fair_val  = lm["fairness"]

            def _good_color(v):
                """Higher = better (faithfulness, fairness)"""
                if v >= 0.7: return "#10b981"
                if v >= 0.4: return "#f59e0b"
                return "#ef4444"
            def _good_label(v):
                if v >= 0.7: return "✅ High"
                if v >= 0.4: return "⚠️ Medium"
                return "🔴 Low"
            def _bad_color(v):
                """Lower = better (bias rate)"""
                if v <= 0.2: return "#10b981"
                if v <= 0.5: return "#f59e0b"
                return "#ef4444"
            def _bad_label(v):
                if v <= 0.2: return "✅ Low"
                if v <= 0.5: return "⚠️ Medium"
                return "🔴 High"

            llm_html = f"""
            <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:10px">
                <div class="score-card" style="border-color:#4f46e5">
                    <div class="score-metric" style="color:{_good_color(faith_val)}">{faith_val:.0%}</div>
                    <div class="score-label">Faithfulness</div>
                    <div style="font-size:9px;color:#475569">Higher is Better ↑</div>
                    <span class="score-badge" style="background:{_good_color(faith_val)}22;color:{_good_color(faith_val)}">{_good_label(faith_val)}</span>
                </div>
                <div class="score-card" style="border-color:#4f46e5">
                    <div class="score-metric" style="color:{_bad_color(bias_val)}">{bias_val:.0%}</div>
                    <div class="score-label">Bias Rate</div>
                    <div style="font-size:9px;color:#475569">Lower is Better ↓</div>
                    <span class="score-badge" style="background:{_bad_color(bias_val)}22;color:{_bad_color(bias_val)}">{_bad_label(bias_val)}</span>
                </div>
                <div class="score-card" style="border-color:#4f46e5">
                    <div class="score-metric" style="color:{_good_color(fair_val)}">{fair_val:.0%}</div>
                    <div class="score-label">Fairness</div>
                    <div style="font-size:9px;color:#475569">Higher is Better ↑</div>
                    <span class="score-badge" style="background:{_good_color(fair_val)}22;color:{_good_color(fair_val)}">{_good_label(fair_val)}</span>
                </div>
            </div>"""
            st.markdown(llm_html, unsafe_allow_html=True)

            with st.expander("🧮 Calculation Details"):
                st.markdown(f"""
| Metric | Formula | Result | Detail |
|--------|---------|--------|--------|
| **Faithfulness** | grounded sentences ÷ total sentences | `{faith_val:.0%}` | {lm['hallucination_reason']} |
| **Bias Rate** | Coefficient of Variation of per-file mentions | `{bias_val:.0%}` | {lm['bias_reason']} |
| **Fairness** | files mentioned ÷ total uploaded files | `{fair_val:.0%}` | {lm['fairness_reason']} |

> All three metrics are **pure mathematics** — no LLM involved.
> - **Faithfulness**: counts sentences containing a real function/class/import name from source code
> - **Bias Rate**: CV = σ/μ of per-file mention counts (low CV = balanced = low bias)
> - **Fairness**: what fraction of your uploaded files are named in the report
""")

            with st.expander(f"ℹ️ How to read {label} scores"):
                st.markdown(f"""
| Metric | Type | What it measures | Your score |
|--------|------|-----------------|------------|
| **ROUGE-1** | Statistical | F1 overlap of individual words between report and source code | `{sc['rouge1_f']:.2%}` |
| **ROUGE-L** | Statistical | Longest common subsequence F1 — captures phrase-level overlap | `{sc['rougeL_f']:.2%}` |
| **BLEU** | Statistical | 4-gram overlap measuring fluency and faithfulness | `{sc['bleu']:.2%}` |
| **Faithfulness** | LLM Judge | How grounded is the report in the source code? **(higher = better, 100% = fully grounded)** | `{faith_val:.0%}` |
| **Bias Rate** | LLM Judge | Unfair emphasis on certain parts **(lower = better, 0% = fully balanced)** | `{lm['bias']:.0%}` |
| **Fairness** | LLM Judge | Proportional coverage of all files **(higher = better, 100% = perfect)** | `{lm['fairness']:.0%}` |

> All 6 metrics are **pure mathematics** — no LLM opinion involved. Faithfulness, Bias & Fairness use identifier extraction + statistical formulas.
""")

    with st.spinner("📄 Building PDFs..."):
        report_pdf = generate_pdf(report, "project_report.pdf")
        readme_pdf = generate_pdf(readme, "readme.pdf")

    st.markdown('<div class="section-header">⬇️ Downloads</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        with open(report_pdf, "rb") as f:
            st.download_button("📥 Report PDF", f, file_name="project_report.pdf", mime="application/pdf", use_container_width=True)
    with c2:
        with open(readme_pdf, "rb") as f:
            st.download_button("📥 README PDF", f, file_name="readme.pdf", mime="application/pdf", use_container_width=True)
    with c3:
        st.download_button("📥 README.md", readme, file_name="README.md", mime="text/markdown", use_container_width=True)

# ─── Codebase Q&A Chat ─────────────────────────────────────────────────────────
if all_code:
    st.divider()
    st.markdown('<div class="section-header">💬 Ask Your Codebase</div>', unsafe_allow_html=True)
    st.markdown(
        "<p style='color:#94a3b8;font-size:13px;margin:-8px 0 16px 0'>"
        "🤖 Ask anything about your uploaded code — functions, logic, architecture, bugs…"
        "</p>",
        unsafe_allow_html=True
    )

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Build Q&A context once and cache it
    if not st.session_state.get("qa_code_context"):
        qa_context = ""
        for fname, code in all_code.items():
            qa_context += f"\n\n### File: {fname}\n```\n{code[:5000]}\n```"
        st.session_state.qa_code_context = qa_context

    for turn in st.session_state.chat_history:
        if turn["role"] == "user":
            st.markdown(f'<div class="chat-user">🧑 {turn["content"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="chat-ai">🤖 {turn["content"]}</div>', unsafe_allow_html=True)

    qchat1, qchat2 = st.columns([5, 1])
    with qchat1:
        user_q = st.text_input(
            "Your question",
            placeholder='e.g. "What does generate_pdf do?" or "How is authentication handled?"',
            label_visibility="collapsed",
            key="qa_input"
        )
    with qchat2:
        ask_btn = st.button("Ask →", use_container_width=True, key="qa_ask")

    if ask_btn and user_q.strip():
        with st.spinner("🤖 Thinking..."):
            answer = answer_code_question(
                question     = user_q.strip(),
                code_context = st.session_state.qa_code_context,
                chat_history = st.session_state.chat_history,
            )
        st.session_state.chat_history.append({"role": "user",     "content": user_q.strip()})
        st.session_state.chat_history.append({"role": "assistant", "content": answer})
        st.rerun()

    if st.session_state.chat_history:
        if st.button("🗑️ Clear Chat", key="qa_clear"):
            st.session_state.chat_history = []
            st.rerun()
