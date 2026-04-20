# 📄 AI Project Report Generator

Upload any code files and instantly generate:
- ✅ A **Final Year Project Report** (PDF + preview)
- ✅ A **GitHub README.md** (PDF + `.md` download)

## Setup

```bash
pip install -r requirements.txt
```

Set your Anthropic API key:
```bash
export ANTHROPIC_API_KEY=your_key_here
```

Run:
```bash
streamlit run app.py
```

## Supported File Types
`.py`, `.js`, `.ts`, `.jsx`, `.tsx`, `.html`, `.css`, `.java`, `.c`, `.cpp`, `.cs`, `.go`, `.rs`, `.php`, `.rb`, `.kt`, `.swift`, `.txt`, `.md`, `.zip`

## How It Works
1. Upload one or more code files (or a `.zip` of your project)
2. Optionally add a project title / extra context
3. Click **Generate** — Claude analyzes your code and writes both documents
4. Download the PDF report, README PDF, or raw `README.md`