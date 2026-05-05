from groq import Groq
from rouge_score import rouge_scorer
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
import nltk
import re
import json
import math
from collections import Counter

# Download required NLTK data silently
try:
    nltk.data.find("tokenizers/punkt")
except LookupError:
    nltk.download("punkt", quiet=True)
try:
    nltk.data.find("tokenizers/punkt_tab")
except LookupError:
    nltk.download("punkt_tab", quiet=True)

# ✅ Groq — used for GENERATION
GROQ_API_KEY = "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"
groq_client  = Groq(api_key=GROQ_API_KEY)
GROQ_MODEL   = "llama-3.3-70b-versatile"


# ── Generation call (Groq / LLaMA) ────────────────────────────────────────────
def _generate(prompt: str, max_tokens: int = 4096) -> str:
    response = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content


# ── Shared grounding rules ─────────────────────────────────────────────────────
GROUNDING_RULES = """
CRITICAL RULES (follow strictly):

1. ANTI-HALLUCINATION:
   - Every function name you mention MUST exist in the uploaded code.
   - Every module, class, or file you reference MUST appear in the uploaded files.
   - Do NOT assume frameworks or features not explicitly imported/used.
   - Never invent version numbers, benchmarks, or metrics not in the code.

2. FAIRNESS — Cover ALL uploaded files proportionally:
   - You MUST mention every uploaded file at least once by name.
   - Give roughly equal depth to each file.
   - List all files in the System Architecture or Modules section.

3. ACCURACY:
   - Quote actual function signatures (e.g. `generate_pdf(content, filename)`).
   - Reference actual variable names, routes, or class names from the code.
   - Describe what the code ACTUALLY does, not what a generic project would do.
"""

# ── Report prompts ─────────────────────────────────────────────────────────────
REPORT_PROMPTS = {
    "Final Year Project Report": """
Generate a comprehensive **Final Year Project Report** in formal academic Markdown format.
Include ALL of these sections, referencing the actual code for each:
1. Project Title
2. Abstract (150–200 words)
3. Introduction (problem statement, motivation, objectives)
4. Literature Review / Related Work (only libraries actually imported in the code)
5. System Architecture (how actual files interact; list every file)
6. Modules / Features (one subsection per uploaded file with its real functions)
7. Tech Stack (only technologies actually used)
8. Implementation Details (real function names and logic)
9. Results & Discussion
10. Conclusion
11. Future Scope
12. References (only libraries/frameworks that appear in the code)
""",
    "Internship Report": """
Generate a professional **Internship Report** in Markdown format based strictly on the uploaded code.
Include ALL sections:
1. Title Page
2. Executive Summary
3. Introduction & Internship Objectives
4. Project Overview (list every file and its role)
5. Work Done (file by file — what each module does, what functions were written)
6. Technologies & Tools Used (only from actual imports)
7. Key Learnings & Skills Gained
8. Challenges & How They Were Resolved
9. Conclusion
10. Future Recommendations
""",
    "Research Paper": """
Generate an **IEEE/ACM-style Research Paper** in Markdown grounded in the uploaded code.
Include ALL sections:
1. Title & Authors (placeholders)
2. Abstract (200 words)
3. Keywords (from actual technologies used)
4. I. Introduction
5. II. Related Work (only frameworks/libraries in the code imports)
6. III. Proposed Methodology / System Design (mention every file)
7. IV. Implementation (actual functions, classes, logic)
8. V. Experimental Results & Evaluation
9. VI. Discussion
10. VII. Conclusion & Future Work
11. References (IEEE format; only real libraries used)
""",
    "Technical Blog Post": """
Generate an engaging **Technical Blog Post** in Markdown for dev.to or Medium.
Base everything on the uploaded code:
1. Catchy Title with emoji
2. Hook paragraph
3. What We Built (every file and its role)
4. Tech Stack (only what's imported; explain WHY each was chosen)
5. How It Works (actual function names, flow between files)
6. Key Challenges & Solutions (from complexity in the code)
7. Demo / Results
8. What's Next
9. Conclusion & Call to Action
"""
}


def generate_documentation(
    code_context: str,
    project_name: str = None,
    extra_context: str = "",
    report_type: str = "Final Year Project Report",
    project_type: str = "",
    project_type_hint: str = "",
) -> str:
    name_hint    = f"The project is called '{project_name}'." if project_name else "Infer the project name from the filenames and code."
    context_hint = f"Additional context: {extra_context}" if extra_context else ""
    type_hint    = f"Auto-detected as **{project_type}**. {project_type_hint}" if project_type else ""
    instructions = REPORT_PROMPTS.get(report_type, REPORT_PROMPTS["Final Year Project Report"])

    file_list = "\n".join(
        f"- {line.strip()}"
        for line in code_context.split("\n")
        if line.strip().startswith("### File:")
    )
    file_hint = f"\nFiles you MUST cover:\n{file_list}\n" if file_list else ""

    prompt = f"""You are an expert technical writer generating a grounded, accurate document from real source code.

{name_hint}
{context_hint}
{type_hint}
{file_hint}

{GROUNDING_RULES}

{instructions}

--- SOURCE CODE ---
{code_context}
"""
    return _generate(prompt)


def generate_readme(
    code_context: str,
    project_name: str = None,
    extra_context: str = "",
    project_type: str = "",
) -> str:
    name_hint    = f"The project is called '{project_name}'." if project_name else "Infer from filenames and code."
    context_hint = f"Additional context: {extra_context}" if extra_context else ""
    type_hint    = f"This is a **{project_type}** project." if project_type else ""

    file_list = "\n".join(
        f"- {line.strip()}"
        for line in code_context.split("\n")
        if line.strip().startswith("### File:")
    )
    file_hint = f"\nFiles to include in Project Structure:\n{file_list}\n" if file_list else ""

    prompt = f"""You are a senior developer writing a GitHub README grounded strictly in the uploaded source code.

{name_hint}
{context_hint}
{type_hint}
{file_hint}

{GROUNDING_RULES}

Generate a professional **GitHub README.md** including:
1. Project Title with emoji
2. Shields.io badges (only for actual languages/frameworks used)
3. Short description (1–2 lines)
4. Table of Contents
5. Features (only actually implemented features)
6. Tech Stack (only actual imports/dependencies)
7. Project Structure (real file tree — every uploaded file with one-line description)
8. Installation (based on actual requirements)
9. Usage (how to actually run this — infer from entry points)
10. API / Module Reference (real functions with brief descriptions)
11. Screenshots placeholder
12. Contributing
13. License (MIT)
14. Author section

--- SOURCE CODE ---
{code_context}
"""
    return _generate(prompt)


# ── ROUGE + BLEU ──────────────────────────────────────────────────────────────

def evaluate_scores(generated_text: str, reference_text: str) -> dict:
    def strip_md(text: str) -> str:
        text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
        text = re.sub(r"[#*_`>~\[\]()!]", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip().lower()

    gen_clean = strip_md(generated_text)
    ref_clean = strip_md(reference_text)

    scorer = rouge_scorer.RougeScorer(["rouge1", "rougeL"], use_stemmer=True)
    scores = scorer.score(ref_clean, gen_clean)
    r1 = scores["rouge1"]
    rl = scores["rougeL"]

    ref_tokens = ref_clean.split()
    hyp_tokens = gen_clean.split()
    smoother   = SmoothingFunction().method1
    bleu = sentence_bleu(
        [ref_tokens], hyp_tokens,
        weights=(0.25, 0.25, 0.25, 0.25),
        smoothing_function=smoother,
    )

    return {
        "rouge1_p": round(r1.precision, 4),
        "rouge1_r": round(r1.recall,    4),
        "rouge1_f": round(r1.fmeasure,  4),
        "rougeL_p": round(rl.precision, 4),
        "rougeL_r": round(rl.recall,    4),
        "rougeL_f": round(rl.fmeasure,  4),
        "bleu":     round(bleu,         4),
    }


# ── Mathematical Evaluation (no LLM) ─────────────────────────────────────────
#
# All three metrics are computed with real formulas:
#
# FAITHFULNESS  = fraction of sentences in the report that contain at least
#                 one real identifier (function name, file name, class name,
#                 imported library) extracted directly from the source code.
#                 Higher = better.  Range [0, 1].
#
# BIAS RATE     = 1 − coefficient_of_variation of per-file mention counts.
#                 CV = std / mean.  Low CV → balanced coverage → low bias.
#                 bias_rate = min(CV, 1.0).  Lower = better.  Range [0, 1].
#
# FAIRNESS      = fraction of uploaded files mentioned at least once in the
#                 generated text.  Higher = better.  Range [0, 1].

def _extract_identifiers(source_code: str) -> set[str]:
    """
    Extract real identifiers from source code:
      - function / method names  (def foo, function foo, async def foo)
      - class names              (class Foo)
      - imported library names   (import X, from X import ...)
      - filenames from ### File: headers
    Returns a set of lower-cased strings (length >= 3 to avoid noise).
    """
    ids: set[str] = set()

    # Function / method names
    for m in re.finditer(r'(?:def |async def |function )(\w+)', source_code):
        ids.add(m.group(1).lower())

    # Class names
    for m in re.finditer(r'class (\w+)', source_code):
        ids.add(m.group(1).lower())

    # Import names
    for m in re.finditer(r'^(?:import (\w+)|from (\w+) import)', source_code, re.MULTILINE):
        name = m.group(1) or m.group(2)
        if name:
            ids.add(name.lower())

    # File names from ### File: headers
    for m in re.finditer(r'### File:\s*(.+)', source_code):
        fname = m.group(1).strip()
        # add both full name and stem
        ids.add(fname.lower())
        stem = fname.rsplit(".", 1)[0].lower()
        ids.add(stem)

    # Remove very short tokens that cause false positives
    return {i for i in ids if len(i) >= 3}


def _extract_filenames(source_code: str) -> list[str]:
    """Extract the list of uploaded filenames from ### File: headers."""
    return [
        m.group(1).strip().lower()
        for m in re.finditer(r'### File:\s*(.+)', source_code)
    ]


def evaluate_llm_metrics(generated_text: str, source_code: str) -> dict:
    """
    Pure mathematical evaluation — zero LLM calls.

    Parameters
    ----------
    generated_text : the AI-generated report or README
    source_code    : the combined code context string (with ### File: headers)

    Returns
    -------
    dict with keys: hallucination, hallucination_reason,
                    bias, bias_reason,
                    fairness, fairness_reason
    (hallucination = 1 − faithfulness for app.py compatibility)
    """

    identifiers = _extract_identifiers(source_code)
    filenames   = _extract_filenames(source_code)

    # Clean generated text to plain sentences
    clean = re.sub(r"```.*?```", " ", generated_text, flags=re.DOTALL)
    clean = re.sub(r"[#*_`>~\[\]()!]", " ", clean)
    clean = re.sub(r"\s+", " ", clean).strip().lower()

    sentences = [s.strip() for s in re.split(r'[.!?\n]', clean) if len(s.strip()) > 20]

    # ── 1. FAITHFULNESS ───────────────────────────────────────────────────────
    # Fraction of sentences that mention at least one real identifier
    if not sentences:
        faithfulness = 0.0
        faith_detail = "No sentences found in generated text."
    elif not identifiers:
        faithfulness = 0.5
        faith_detail = "No identifiers extracted from source code."
    else:
        grounded = sum(
            1 for s in sentences
            if any(ident in s for ident in identifiers)
        )
        faithfulness = round(grounded / len(sentences), 4)
        faith_detail = (
            f"{grounded}/{len(sentences)} sentences contain a real identifier "
            f"from the source code ({faithfulness:.0%} grounded)."
        )

    # ── 2. FAIRNESS ───────────────────────────────────────────────────────────
    # Fraction of uploaded files mentioned at least once in the report
    if not filenames:
        fairness     = 1.0
        fair_detail  = "No file headers found in source context."
    else:
        mentioned = sum(1 for f in filenames if f in clean)
        fairness  = round(mentioned / len(filenames), 4)
        fair_detail = (
            f"{mentioned}/{len(filenames)} uploaded files are mentioned "
            f"in the generated text ({fairness:.0%} coverage)."
        )

    # ── 3. BIAS RATE ──────────────────────────────────────────────────────────
    # Coefficient of Variation of per-file mention counts.
    # Low CV = balanced coverage = low bias.
    if len(filenames) <= 1:
        bias_rate   = 0.0
        bias_detail = "Only one file — no inter-file bias possible."
    else:
        counts = [clean.count(f) for f in filenames]
        mean   = sum(counts) / len(counts)
        if mean == 0:
            bias_rate   = 1.0
            bias_detail = "No files mentioned at all — maximum bias."
        else:
            variance = sum((c - mean) ** 2 for c in counts) / len(counts)
            cv       = math.sqrt(variance) / mean          # coefficient of variation
            bias_rate = round(min(cv, 1.0), 4)             # cap at 1.0
            bias_detail = (
                f"Per-file mention counts: {dict(zip(filenames, counts))}. "
                f"CV = {cv:.3f} → bias rate = {bias_rate:.0%}."
            )

    return {
        # hallucination = 1 − faithfulness (kept for app.py compatibility)
        "hallucination":        round(1.0 - faithfulness, 4),
        "hallucination_reason": faith_detail,
        "bias":                 bias_rate,
        "bias_reason":          bias_detail,
        "fairness":             fairness,
        "fairness_reason":      fair_detail,
    }


# ── Codebase Q&A (Groq) ───────────────────────────────────────────────────────

def answer_code_question(
    question: str,
    code_context: str,
    chat_history: list[dict],
) -> str:
    system = f"""You are an expert code reviewer and technical assistant.
Answer questions about the uploaded codebase clearly and accurately.
Reference specific function names, file names, and logic when relevant.
Use markdown formatting where helpful.

--- CODEBASE START ---
{code_context[:40000]}
--- CODEBASE END ---
"""
    messages = [{"role": "user", "content": system}]
    for turn in chat_history[-10:]:
        messages.append(turn)
    messages.append({"role": "user", "content": question})

    response = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        max_tokens=1024,
    )
    return response.choices[0].message.content
