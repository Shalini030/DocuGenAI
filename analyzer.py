"""
analyzer.py — Static analysis helpers (no LLM needed).
Provides:
  - detect_project_type(all_code) → str
  - code_quality_score(all_code)  → dict
  - build_mermaid_diagram(all_code) → str
"""

import re
from collections import defaultdict


# ── 1. Project-type detection ──────────────────────────────────────────────────

PROJECT_SIGNATURES = {
    "Flask API": {
        "files": [],
        "content": ["from flask import", "Flask(__name__)", "@app.route", "flask"],
    },
    "FastAPI Service": {
        "files": [],
        "content": ["from fastapi import", "FastAPI()", "@app.get", "@app.post", "fastapi"],
    },
    "Django Web App": {
        "files": ["manage.py", "settings.py", "urls.py"],
        "content": ["from django", "django.db", "INSTALLED_APPS"],
    },
    "React App": {
        "files": ["package.json", "index.jsx", "App.jsx", "App.tsx"],
        "content": ["import React", "ReactDOM", "useState", "useEffect"],
    },
    "ML / Data Pipeline": {
        "files": [],
        "content": ["import pandas", "import numpy", "sklearn", "torch", "tensorflow",
                    "model.fit", "train_test_split", "DataFrame"],
    },
    "Streamlit App": {
        "files": [],
        "content": ["import streamlit", "st.write", "st.button", "st.sidebar"],
    },
    "CLI Tool": {
        "files": [],
        "content": ["argparse", "click", "typer", "sys.argv", "if __name__"],
    },
    "Node.js / Express": {
        "files": ["package.json", "server.js", "index.js"],
        "content": ["require('express')", "express()", "app.listen", "require(\"express\")"],
    },
    "General Python Project": {
        "files": [],
        "content": ["import os", "import sys"],
    },
}

PROJECT_REPORT_HINTS = {
    "Flask API":          "Focus on REST endpoints, request/response flow, and API design.",
    "FastAPI Service":    "Highlight async endpoints, Pydantic models, and OpenAPI docs.",
    "Django Web App":     "Cover models, views, URL routing, templates, and ORM usage.",
    "React App":          "Describe component hierarchy, state management, and data flow.",
    "ML / Data Pipeline": "Emphasise dataset handling, model architecture, training loop, and evaluation metrics.",
    "Streamlit App":      "Cover widgets, session state, data visualisation, and user interaction flow.",
    "CLI Tool":           "Describe commands, arguments, and execution flow.",
    "Node.js / Express":  "Highlight middleware, routes, and async patterns.",
    "General Python Project": "",
}


def detect_project_type(all_code: dict) -> tuple[str, str]:
    """Return (project_type_label, report_hint)."""
    file_names = [f.lower() for f in all_code.keys()]
    combined   = "\n".join(all_code.values())[:50_000]

    scores: dict[str, int] = defaultdict(int)

    for ptype, sigs in PROJECT_SIGNATURES.items():
        for fname in sigs["files"]:
            if any(fname in fn for fn in file_names):
                scores[ptype] += 3
        for keyword in sigs["content"]:
            if keyword in combined:
                scores[ptype] += 1

    if not scores:
        return "General Python Project", ""

    best = max(scores, key=lambda k: scores[k])
    return best, PROJECT_REPORT_HINTS.get(best, "")


# ── 2. Code-quality scoring (industry-fair thresholds) ────────────────────────

def code_quality_score(all_code: dict) -> dict:
    """
    Returns a dict with:
      score     int  0-100
      grade     str  A/B/C/D/F
      breakdown dict {category: (score, max, detail)}
      smells    list[str]

    Thresholds are calibrated to real-world projects:
    - A typical working project with moderate documentation scores B (70-84)
    - Only severe issues (no docs at all, extreme nesting) cause D/F
    """
    smells   = []
    combined = "\n".join(all_code.values())
    py_files = {f: c for f, c in all_code.items() if f.endswith(".py")}

    total_py_lines = sum(len(c.split("\n")) for c in py_files.values())

    # ── Docstring coverage (max 25) ───────────────────────────────────────────
    # Fair threshold: >= 30% documented = full marks (real projects rarely hit 100%)
    total_funcs = 0
    documented  = 0
    for code in py_files.values():
        fn_matches = list(re.finditer(
            r'^\s*(def |async def )\w+', code, re.MULTILINE
        ))
        total_funcs += len(fn_matches)
        for m in fn_matches:
            after      = code[m.end():]
            next_lines = after.split("\n")[:6]
            if any('"""' in l or "'''" in l for l in next_lines):
                documented += 1

    if total_funcs == 0:
        doc_score  = 20
        doc_detail = "No functions detected"
    else:
        ratio = documented / total_funcs
        if ratio >= 0.5:
            doc_score = 25
        elif ratio >= 0.30:
            doc_score = 20
        elif ratio >= 0.15:
            doc_score = 14
        elif ratio >= 0.05:
            doc_score = 8
        else:
            doc_score = 3
        doc_detail = f"{documented}/{total_funcs} functions documented ({ratio:.0%})"
        if ratio < 0.15:
            smells.append(f"🔴 Low docstring coverage ({ratio:.0%}) — add docstrings to key functions")
        elif ratio < 0.30:
            smells.append(f"🟡 Moderate docstring coverage ({ratio:.0%}) — aim for at least 30%")

    # ── Nesting depth (max 20) ────────────────────────────────────────────────
    # Fair: count deeply nested blocks relative to total lines (not absolute count)
    max_depth  = 0
    deep_count = 0
    for code in all_code.values():
        depth = 0
        for line in code.split("\n"):
            stripped = line.lstrip()
            if stripped.startswith(("if ", "for ", "while ", "with ", "try:", "elif ")):
                depth      = (len(line) - len(stripped)) // 4
                max_depth  = max(max_depth, depth)
                if depth >= 5:   # raised from 4 → 5 to be fairer
                    deep_count += 1

    # Normalise by file size
    deep_ratio = deep_count / max(total_py_lines, 1) * 100  # per 100 lines

    if deep_ratio <= 1.0:
        nest_score = 20
    elif deep_ratio <= 3.0:
        nest_score = 16
        smells.append(f"🟡 Some deep nesting ({deep_count} blocks ≥5 levels) — review for readability")
    elif deep_ratio <= 6.0:
        nest_score = 10
        smells.append(f"🟠 Moderate deep nesting ({deep_count} blocks) — consider extracting functions")
    else:
        nest_score = 5
        smells.append(f"🔴 Excessive nesting ({deep_count} deeply nested blocks) — refactor urgently")
    nest_detail = f"Max depth {max_depth}, {deep_count} deeply nested blocks"

    # ── Long functions (max 20) ───────────────────────────────────────────────
    # Fair: threshold raised to 80 lines (50 is too strict for real projects)
    long_funcs     = 0
    very_long_funcs = 0
    for code in py_files.values():
        fn_starts = [m.start() for m in re.finditer(r'^\s*(def |async def )\w+', code, re.MULTILINE)]
        for i, start in enumerate(fn_starts):
            end   = fn_starts[i + 1] if i + 1 < len(fn_starts) else len(code)
            lines = code[start:end].split("\n")
            if len(lines) > 100:
                very_long_funcs += 1
            elif len(lines) > 80:
                long_funcs += 1

    total_long = long_funcs + very_long_funcs
    if total_long == 0:
        len_score = 20
    elif very_long_funcs == 0 and long_funcs <= 3:
        len_score = 16
        smells.append(f"🟡 {long_funcs} functions exceed 80 lines — consider splitting")
    elif total_long <= 5:
        len_score = 11
        smells.append(f"🟠 {total_long} long functions (>80 lines) — refactor where possible")
    else:
        len_score = 6
        smells.append(f"🔴 {total_long} functions exceed 80 lines — split into smaller units")
    len_detail = f"{total_long} functions exceed 80 lines"

    # ── TODO / FIXME / HACK count (max 15) ───────────────────────────────────
    # Fair: normalise by total lines
    todo_count = len(re.findall(r'\b(TODO|FIXME|HACK|XXX)\b', combined, re.IGNORECASE))
    todo_ratio = todo_count / max(total_py_lines, 1) * 100  # per 100 lines

    if todo_ratio <= 0.5:
        todo_score = 15
    elif todo_ratio <= 1.5:
        todo_score = 11
        smells.append(f"🟡 {todo_count} TODO/FIXME comments — worth addressing before release")
    elif todo_ratio <= 3.0:
        todo_score = 7
        smells.append(f"🟠 {todo_count} TODO/FIXME markers — notable backlog")
    else:
        todo_score = 3
        smells.append(f"🔴 {todo_count} TODO/FIXME markers — large backlog of known issues")
    todo_detail = f"{todo_count} TODO/FIXME/HACK comments"

    # ── Bare except / error handling (max 10) ────────────────────────────────
    bare_except  = len(re.findall(r'except\s*:', combined))
    broad_except = len(re.findall(r'except Exception\s*:', combined))

    if bare_except == 0:
        err_score = 10
    elif bare_except <= 2:
        err_score = 7
        smells.append(f"🟡 {bare_except} bare `except:` — prefer explicit exception types")
    elif bare_except <= 5:
        err_score = 4
        smells.append(f"🟠 {bare_except} bare `except:` clauses — catch specific exceptions")
    else:
        err_score = 1
        smells.append(f"🔴 {bare_except} bare `except:` — fix error handling throughout")
    err_detail = f"{bare_except} bare except, {broad_except} broad Exception catches"

    # ── Unused imports heuristic (max 10) ─────────────────────────────────────
    unused_imports = 0
    for code in py_files.values():
        imports = re.findall(r'^import (\w+)|^from \w+ import (\w+)', code, re.MULTILINE)
        for grp in imports:
            name = grp[0] or grp[1]
            uses = len(re.findall(rf'\b{name}\b', code)) - 1
            if uses == 0:
                unused_imports += 1

    if unused_imports <= 1:
        imp_score = 10
    elif unused_imports <= 4:
        imp_score = 7
        smells.append(f"🟡 {unused_imports} possibly unused imports")
    elif unused_imports <= 8:
        imp_score = 4
        smells.append(f"🟠 {unused_imports} potentially unused imports — clean up")
    else:
        imp_score = 1
        smells.append(f"🔴 {unused_imports} unused imports — remove them")
    imp_detail = f"{unused_imports} possibly unused imports"

    total = doc_score + nest_score + len_score + todo_score + err_score + imp_score

    # Fairer grade boundaries
    if total >= 80:   grade = "A"
    elif total >= 65: grade = "B"
    elif total >= 50: grade = "C"
    elif total >= 35: grade = "D"
    else:             grade = "F"

    return {
        "score": total,
        "grade": grade,
        "breakdown": {
            "📝 Docstring Coverage": (doc_score,  25, doc_detail),
            "🔀 Nesting Depth":      (nest_score, 20, nest_detail),
            "📏 Function Length":    (len_score,  20, len_detail),
            "🗒️ Tech Debt (TODOs)":  (todo_score, 15, todo_detail),
            "🛡️ Error Handling":     (err_score,  10, err_detail),
            "📦 Import Hygiene":     (imp_score,  10, imp_detail),
        },
        "smells": smells or ["✅ No major code smells detected!"],
    }


# ── 3. Mermaid function-call diagram ──────────────────────────────────────────

def build_mermaid_diagram(all_code: dict) -> str:
    """
    Generates a Mermaid flowchart showing:
      - Each file as a subgraph
      - Functions inside it
      - Call edges between functions (best-effort, same-project only)
    """
    file_funcs: dict[str, list[str]] = {}
    all_func_names: set[str] = set()

    for fname, code in all_code.items():
        if not fname.endswith((".py", ".js", ".ts", ".jsx", ".tsx")):
            continue
        funcs = re.findall(
            r'^\s*(?:def |async def |function |const \w+ = (?:async )?\(|export (?:default )?function )(\w+)',
            code, re.MULTILINE
        )
        seen   = set()
        unique = []
        for f in funcs:
            if f not in seen and f not in ("self", "cls"):
                seen.add(f)
                unique.append(f)
        if unique:
            short = fname.replace("/", "_").replace("\\", "_").replace(".", "_")
            file_funcs[short]  = unique[:12]
            all_func_names.update(unique)

    if not file_funcs:
        return ""

    edges: list[tuple[str, str]] = []
    for fname, code in all_code.items():
        short        = fname.replace("/", "_").replace("\\", "_").replace(".", "_")
        defined_here = set(file_funcs.get(short, []))
        for fn in defined_here:
            m = re.search(rf'def {fn}\b.*?(?=\ndef |\Z)', code, re.DOTALL)
            if not m:
                continue
            body = m.group()
            for called in all_func_names:
                if called == fn:
                    continue
                if re.search(rf'\b{called}\s*\(', body):
                    edges.append((fn, called))

    edges = list(dict.fromkeys(edges))[:30]

    lines = ["```mermaid", "flowchart TD"]

    for file_key, funcs in file_funcs.items():
        safe_label = file_key.replace("_py", ".py").replace("_js", ".js")
        lines.append(f'  subgraph {file_key}["{safe_label}"]')
        for fn in funcs:
            lines.append(f'    {fn}["{fn}()"]')
        lines.append("  end")

    for src, dst in edges:
        lines.append(f"  {src} --> {dst}")

    lines.append("```")
    return "\n".join(lines)
