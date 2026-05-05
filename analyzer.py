"""
analyzer.py — Static analysis helpers (no LLM needed).
Provides:
  - detect_project_type(all_code) → str
  - code_quality_score(all_code)  → dict
  - build_mermaid_diagram(all_code) → str
"""

import re
import ast
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
    combined   = "\n".join(all_code.values())[:50_000]  # cap for speed

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


# ── 2. Code-quality scoring ────────────────────────────────────────────────────

class PyAnalyzerVisitor(ast.NodeVisitor):
    def __init__(self):
        self.functions = 0
        self.documented_functions = 0
        self.long_functions = 0
        self.max_depth = 0
        self.deep_blocks = 0
        self.bare_excepts = 0
        self.broad_excepts = 0
        self.current_depth = 0
        self.imported_names = set()
        self.used_names = set()

    def visit_FunctionDef(self, node):
        self._check_func(node)

    def visit_AsyncFunctionDef(self, node):
        self._check_func(node)
        
    def _check_func(self, node):
        self.functions += 1
        if ast.get_docstring(node):
            self.documented_functions += 1
        
        if hasattr(node, 'end_lineno') and hasattr(node, 'lineno'):
            if (node.end_lineno - node.lineno) > 50:
                self.long_functions += 1
                
        self.generic_visit(node)

    def _visit_nested_block(self, node):
        self.current_depth += 1
        self.max_depth = max(self.max_depth, self.current_depth)
        if self.current_depth >= 4:
            self.deep_blocks += 1
            
        self.generic_visit(node)
        self.current_depth -= 1

    def visit_If(self, node): self._visit_nested_block(node)
    def visit_For(self, node): self._visit_nested_block(node)
    def visit_AsyncFor(self, node): self._visit_nested_block(node)
    def visit_While(self, node): self._visit_nested_block(node)
    def visit_Try(self, node): self._visit_nested_block(node)
    def visit_With(self, node): self._visit_nested_block(node)
    def visit_AsyncWith(self, node): self._visit_nested_block(node)

    def visit_ExceptHandler(self, node):
        if node.type is None:
            self.bare_excepts += 1
        elif isinstance(node.type, ast.Name) and node.type.id == 'Exception':
            self.broad_excepts += 1
        self.generic_visit(node)

    def visit_Import(self, node):
        for alias in node.names:
            self.imported_names.add(alias.asname or alias.name.split('.')[0])
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        for alias in node.names:
            self.imported_names.add(alias.asname or alias.name)
        self.generic_visit(node)

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load):
            self.used_names.add(node.id)
        self.generic_visit(node)


def code_quality_score(all_code: dict) -> dict:
    """
    Returns a dict with:
      score          int  0-100
      grade          str  A/B/C/D/F
      breakdown      dict {category: (score, max, detail)}
      smells         list[str]
    """
    smells = []
    combined = "\n".join(all_code.values())
    py_files = {f: c for f, c in all_code.items() if f.endswith(".py")}
    
    # Python AST Analysis
    visitor = PyAnalyzerVisitor()
    for code in py_files.values():
        try:
            tree = ast.parse(code)
            visitor.visit(tree)
        except SyntaxError:
            pass  # skip unparseable files
            
    # Fallback heuristics for non-Python files
    non_py = {f: c for f, c in all_code.items() if not f.endswith(".py")}
    
    # ── Docstring coverage (max 25) ────────────────────────────────────────────
    total_funcs = visitor.functions
    documented = visitor.documented_functions
    
    # fallback for non-py
    for code in non_py.values():
        fn_matches = list(re.finditer(r'^\s*(function |func |fn )\w+', code, re.MULTILINE))
        total_funcs += len(fn_matches)
        for m in fn_matches:
            after = code[m.end():]
            next_lines = after.split("\n")[:6]
            if any('/**' in l or '///' in l for l in next_lines):
                documented += 1

    doc_score = int((documented / total_funcs) * 25) if total_funcs else 20
    doc_detail = f"{documented}/{total_funcs} functions documented"
    if doc_score < 10:
        smells.append("🔴 Low docstring coverage — add docstrings to most functions")

    # ── Nesting depth (max 20) ─────────────────────────────────────────────────
    max_depth = visitor.max_depth
    deep_count = visitor.deep_blocks
    
    # fallback for non-py
    for code in non_py.values():
        depth = 0
        for line in code.split("\n"):
            stripped = line.lstrip()
            if stripped.startswith(("if (", "for (", "while (", "catch (")):
                depth = (len(line) - len(stripped)) // 4
                max_depth = max(max_depth, depth)
                if depth >= 4:
                    deep_count += 1

    if deep_count > 10:
        nest_score = 8
        smells.append(f"🟠 Deep nesting detected ({deep_count} instances ≥4 levels) — consider extracting functions")
    elif deep_count > 3:
        nest_score = 14
        smells.append(f"🟡 Some deep nesting ({deep_count} instances) — review for readability")
    else:
        nest_score = 20
    nest_detail = f"Max depth {max_depth}, {deep_count} deeply nested blocks"

    # ── Long functions (max 20) ────────────────────────────────────────────────
    long_funcs = visitor.long_functions
    
    # fallback for non-py
    for code in non_py.values():
        fn_starts = [m.start() for m in re.finditer(r'^\s*(function |func |fn )\w+', code, re.MULTILINE)]
        for i, start in enumerate(fn_starts):
            end = fn_starts[i + 1] if i + 1 < len(fn_starts) else len(code)
            lines = code[start:end].split("\n")
            if len(lines) > 50:
                long_funcs += 1

    if long_funcs > 5:
        len_score = 8
        smells.append(f"🔴 {long_funcs} functions exceed 50 lines — split into smaller units")
    elif long_funcs > 2:
        len_score = 14
        smells.append(f"🟡 {long_funcs} long functions (>50 lines) — consider refactoring")
    else:
        len_score = 20
    len_detail = f"{long_funcs} functions exceed 50 lines"

    # ── TODO / FIXME / HACK count (max 15) ────────────────────────────────────
    todo_count = len(re.findall(r'\b(TODO|FIXME|HACK|XXX)\b', combined, re.IGNORECASE))
    if todo_count > 15:
        todo_score = 5
        smells.append(f"🔴 {todo_count} TODO/FIXME markers — large backlog of known issues")
    elif todo_count > 5:
        todo_score = 10
        smells.append(f"🟡 {todo_count} TODO/FIXME comments — worth addressing before release")
    else:
        todo_score = 15
    todo_detail = f"{todo_count} TODO/FIXME/HACK comments"

    # ── Bare except / error handling (max 10) ─────────────────────────────────
    bare_except = visitor.bare_excepts
    broad_except = visitor.broad_excepts
    
    # fallback
    bare_except += len(re.findall(r'catch\s*\{\s*\}', "\n".join(non_py.values())))
    
    if bare_except > 3:
        err_score = 3
        smells.append(f"🔴 {bare_except} bare `except:` clauses — catch specific exceptions")
    elif bare_except > 0:
        err_score = 7
        smells.append(f"🟡 {bare_except} bare `except:` — prefer explicit exception types")
    else:
        err_score = 10
    err_detail = f"{bare_except} bare except, {broad_except} broad Exception catches"

    # ── Unused imports heuristic (max 10) ─────────────────────────────────────
    unused_imports = len(visitor.imported_names - visitor.used_names)
    
    if unused_imports > 5:
        imp_score = 3
        smells.append(f"🟠 {unused_imports} potentially unused imports — clean up")
    elif unused_imports > 2:
        imp_score = 7
        smells.append(f"🟡 {unused_imports} possibly unused imports")
    else:
        imp_score = 10
    imp_detail = f"{unused_imports} possibly unused imports"

    total = doc_score + nest_score + len_score + todo_score + err_score + imp_score

    if total >= 85:   grade = "A"
    elif total >= 70: grade = "B"
    elif total >= 55: grade = "C"
    elif total >= 40: grade = "D"
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
    # Collect all function definitions per file
    file_funcs: dict[str, list[str]] = {}
    all_func_names: set[str] = set()

    for fname, code in all_code.items():
        if not fname.endswith((".py", ".js", ".ts", ".jsx", ".tsx")):
            continue
        funcs = re.findall(
            r'^\s*(?:def |async def |function |const \w+ = (?:async )?\(|export (?:default )?function )(\w+)',
            code, re.MULTILINE
        )
        # deduplicate, keep order
        seen = set()
        unique = []
        for f in funcs:
            if f not in seen and f not in ("self", "cls"):
                seen.add(f)
                unique.append(f)
        if unique:
            short = fname.replace("/", "_").replace("\\", "_").replace(".", "_")
            file_funcs[short] = unique[:12]   # cap per file for readability
            all_func_names.update(unique)

    if not file_funcs:
        return ""

    # Build call edges: scan each file for calls to known functions
    edges: list[tuple[str, str]] = []
    for fname, code in all_code.items():
        short = fname.replace("/", "_").replace("\\", "_").replace(".", "_")
        defined_here = set(file_funcs.get(short, []))
        for fn in defined_here:
            # find the function body
            m = re.search(rf'def {fn}\b.*?(?=\ndef |\Z)', code, re.DOTALL)
            if not m:
                continue
            body = m.group()
            for called in all_func_names:
                if called == fn:
                    continue
                if re.search(rf'\b{called}\s*\(', body):
                    edges.append((fn, called))

    # Cap edges for diagram clarity
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
