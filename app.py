import streamlit as st
from model import generate_documentation, generate_readme
from utils import generate_pdf
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

/* Stat cards */
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

/* Language badge row */
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

/* Report type cards */
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
.rtype-card.selected {
    border-color: #6366f1;
    background: #1e1b4b;
}
.rtype-card:hover { border-color: #4f46e5; }
.rtype-emoji { font-size: 26px; }
.rtype-label { font-size: 12px; font-weight: 600; color: #cbd5e1; margin-top: 6px; }
.rtype-desc  { font-size: 10px; color: #64748b; margin-top: 2px; }

/* Section header */
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

# ─── Parse files & build stats ─────────────────────────────────────────────────
LANG_MAP = {
    "py":"Python","js":"JavaScript","ts":"TypeScript","jsx":"React JSX",
    "tsx":"React TSX","html":"HTML","css":"CSS","java":"Java","c":"C",
    "cpp":"C++","cs":"C#","go":"Go","rs":"Rust","php":"PHP",
    "rb":"Ruby","kt":"Kotlin","swift":"Swift","md":"Markdown","txt":"Text"
}

all_code = {}

if uploaded_files:
    for uf in uploaded_files:
        if uf.name.endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(uf.read()), "r") as z:
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
                content = uf.read().decode("utf-8", errors="ignore")
                all_code[uf.name] = content
            except Exception:
                pass

# ─── Stats Dashboard ───────────────────────────────────────────────────────────
if all_code:
    total_files = len(all_code)
    total_lines = sum(len(c.split("\n")) for c in all_code.values())
    total_chars = sum(len(c) for c in all_code.values())

    # Count functions (def / function / func / fn / public ... void/int etc.)
    func_pattern = re.compile(
        r'^\s*(def |function |func |fn |public |private |protected |async function )',
        re.MULTILINE
    )
    total_funcs = sum(len(func_pattern.findall(c)) for c in all_code.values())

    # Detect languages
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
            f'<span class="lang-badge">{'●'} {lang} <span style="color:#64748b">({count})</span></span>'
            for lang, count in sorted(detected_langs.items(), key=lambda x: -x[1])
        )
        st.markdown(f'<div class="lang-badges">{badges}</div>', unsafe_allow_html=True)

    # File list expander
    with st.expander(f"📂 View all {total_files} detected files"):
        for fname, code in all_code.items():
            lc = len(code.split("\n"))
            st.markdown(f"`{fname}` — {lc} lines")

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

# ─── Generate ──────────────────────────────────────────────────────────────────
st.markdown("")
generate_btn = st.button(
    "🚀 Generate Report & README",
    disabled=not all_code,
    use_container_width=True,
    type="primary"
)

if generate_btn:
    combined_code = ""
    for fname, code in all_code.items():
        combined_code += f"\n\n### File: {fname}\n```\n{code[:3000]}\n```"

    project_name   = custom_name.strip() if uploaded_files and custom_name.strip() else None
    extra_context  = custom_desc.strip()  if uploaded_files and custom_desc.strip()  else ""

    with st.spinner(f"🤖 Generating {report_type}..."):
        report = generate_documentation(combined_code, project_name, extra_context, report_type)
        readme = generate_readme(combined_code, project_name, extra_context)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="section-header">📘 Report Preview</div>', unsafe_allow_html=True)
        st.markdown(report)
    with col2:
        st.markdown('<div class="section-header">📗 README Preview</div>', unsafe_allow_html=True)
        st.markdown(readme)

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
