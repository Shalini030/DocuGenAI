from groq import Groq
import google.generativeai as genai
from rouge_score import rouge_scorer
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
import nltk
import re
import json

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

# ✅ Gemini — used for EVALUATION (judge)
GEMINI_API_KEY = "paste_your_gemini_key_here"
genai.configure(api_key=GEMINI_API_KEY)
gemini_model   = genai.GenerativeModel("gemini-2.0-flash")


# ── Generation call (Groq / LLaMA) ────────────────────────────────────────────
def _generate(prompt: str, max_tokens: int = 4096) -> str:
    response = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content


# ── Evaluation call (Gemini) ───────────────────────────────────────────────────
def _evaluate(prompt: str) -> str:
    response = gemini_model.generate_content(prompt)
    return response.text


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


# ── LLM-as-a-Judge via Gemini (cross-model evaluation) ────────────────────────

def evaluate_llm_metrics(generated_text: str, source_code: str) -> dict:
    gen_snippet = generated_text[:4000]
    src_snippet = source_code[:3000]

    judge_prompt = f"""You are a strict, impartial AI evaluation judge. You are evaluating a report generated by a DIFFERENT AI model (not you). Your job is to score it objectively.

Score each metric 0–10 using these rubrics:

1. FAITHFULNESS (0–10) — How grounded is the report in the source code? (HIGHER = BETTER)
   - 10 = Fully faithful — every claim traces directly to the source code ✅
   - 8–9 = Mostly faithful — 1–2 minor unsupported details
   - 5–7 = Partially faithful — some invented claims
   - 2–4 = Mostly fabricated — many invented facts
   - 0  = Completely hallucinated — no grounding in source code
   Rule: If every function/file/library mentioned exists in the source code, score MUST be 8–10.

2. BIAS RATE (0–10) — Does the report unfairly emphasise/ignore parts of the codebase? (LOWER = BETTER)
   - 0  = Fully balanced coverage ✅
   - 1–2 = Minor imbalance
   - 4–6 = Noticeable imbalance
   - 10  = Completely one-sided
   Rule: If all files are mentioned and coverage feels proportional, score 0–2.

3. FAIRNESS (0–10) — Are ALL uploaded files covered proportionally? (HIGHER = BETTER)
   - 10 = Every file mentioned and described thoroughly ✅
   - 8–9 = Nearly all files covered
   - 5–7 = Most files covered, minor gaps
   - 3–4 = Several files missing
   - 0–2 = Only 1–2 files covered
   Rule: If you see every filename from the source code mentioned in the report, score 8–10.

--- SOURCE CODE (what the report should be based on):
{src_snippet}

--- GENERATED REPORT (evaluate this):
{gen_snippet}

Respond ONLY with this exact JSON, no extra text:
{{
  "faithfulness": <integer 0-10>,
  "faithfulness_reason": "<one sentence>",
  "bias_rate": <integer 0-10>,
  "bias_reason": "<one sentence>",
  "fairness": <integer 0-10>,
  "fairness_reason": "<one sentence>"
}}"""

    try:
        raw      = _evaluate(judge_prompt)
        json_str = re.sub(r"```(?:json)?|```", "", raw).strip()
        match    = re.search(r'\{.*\}', json_str, re.DOTALL)
        if not match:
            raise ValueError("No JSON in Gemini response")
        data = json.loads(match.group())

        def _norm(val):
            return round(max(0, min(10, int(val))) / 10, 2)

        return {
            # faithfulness: higher is better (stored directly, not inverted)
            "hallucination":        round(1.0 - _norm(data.get("faithfulness", 5)), 2),  # kept for app.py compatibility
            "hallucination_reason": data.get("faithfulness_reason", ""),
            "bias":                 _norm(data.get("bias_rate", 5)),
            "bias_reason":          data.get("bias_reason", ""),
            "fairness":             _norm(data.get("fairness", 5)),
            "fairness_reason":      data.get("fairness_reason", ""),
        }

    except Exception as e:
        return {
            "hallucination":        0.5,
            "hallucination_reason": f"Evaluation error: {e}",
            "bias":                 0.5,
            "bias_reason":          f"Evaluation error: {e}",
            "fairness":             0.5,
            "fairness_reason":      f"Evaluation error: {e}",
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
