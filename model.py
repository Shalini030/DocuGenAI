from groq import Groq
from rouge_score import rouge_scorer
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
import nltk
import re

# Download required NLTK data silently
try:
    nltk.data.find("tokenizers/punkt")
except LookupError:
    nltk.download("punkt", quiet=True)
try:
    nltk.data.find("tokenizers/punkt_tab")
except LookupError:
    nltk.download("punkt_tab", quiet=True)

# ✅ Paste your Groq API key here (free at console.groq.com)
GROQ_API_KEY = "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"

client = Groq(api_key=GROQ_API_KEY)
MODEL = "llama-3.3-70b-versatile"


def _call(prompt: str, max_tokens: int = 8000) -> str:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content


# ── Shared grounding rules injected into every report prompt ───────────────────
GROUNDING_RULES = """
CRITICAL RULES TO FOLLOW (these affect evaluation scores — follow strictly):

1. ANTI-HALLUCINATION — Only write what is directly in the code:
   - Every function name you mention MUST exist in the uploaded code. Do NOT invent function names.
   - Every module, class, or file you reference MUST appear in the uploaded files.
   - Do NOT assume frameworks, libraries, or features not explicitly imported or used in the code.
   - If something is unclear, say "as implemented in [filename]" rather than guessing.
   - Never make up version numbers, performance benchmarks, or metrics not in the code.

2. FAIRNESS — Cover ALL uploaded files proportionally:
   - You MUST mention every uploaded file at least once by name.
   - Give roughly equal depth of coverage to each file — do not focus only on the largest file.
   - If there are helper files, utility modules, or config files, include them explicitly.
   - List all files covered in the System Architecture or Modules section.

3. ACCURACY — Be precise:
   - Quote actual function signatures when describing implementation (e.g. `generate_pdf(content, filename)`).
   - Reference actual variable names, routes, or class names from the code.
   - Describe what the code ACTUALLY does, not what a generic project of this type would do.
"""

# ── Report type → prompt instructions ──────────────────────────────────────────
REPORT_PROMPTS = {
    "Final Year Project Report": """
Generate a comprehensive **Final Year Project Report** in formal academic Markdown format.
Include ALL of these sections, referencing the actual code for each:

1. **Project Title** — infer from the code/filenames
2. **Abstract** (150–200 words) — summarise what the code actually does
3. **Introduction** — state the real problem this code solves, based on what you see
4. **Literature Review / Related Work** — mention only libraries/frameworks actually imported in the code
5. **System Architecture** — describe how the actual files interact with each other; list every file
6. **Modules / Features** — one subsection per uploaded file, describing its real functions
7. **Tech Stack** — only list technologies actually used (imports, requirements, etc.)
8. **Implementation Details** — reference real function names and logic from the code
9. **Results & Discussion** — describe what the system produces based on the code's output logic
10. **Conclusion** — summarise based only on what was implemented
11. **Future Scope** — suggest extensions that are natural given the existing codebase
12. **References** — only cite libraries/frameworks that appear in the code
""",

    "Internship Report": """
Generate a professional **Internship Report** in Markdown format based strictly on the uploaded code.
Include ALL of these sections:

1. **Title Page** — Project name (from code), Duration (use placeholder), Role: Developer
2. **Executive Summary** — what this codebase does in 3–4 sentences, grounded in the code
3. **Introduction & Internship Objectives** — objectives that match what the code actually implements
4. **Project Overview** — describe the real system: list every file and its role
5. **Work Done** — describe tasks file by file: what each module does, what functions were written
6. **Technologies & Tools Used** — only from actual imports and requirements
7. **Key Learnings & Skills Gained** — infer from the actual tech stack used
8. **Challenges & How They Were Resolved** — base on real complexity visible in the code
9. **Conclusion** — based on what was actually built
10. **Future Recommendations** — natural extensions of the existing code
""",

    "Research Paper": """
Generate an **IEEE/ACM-style Research Paper** in Markdown format grounded in the uploaded code.
Include ALL of these sections:

1. **Title & Authors** — title inferred from code purpose; authors: [Your Name], [Institution]
2. **Abstract** (200 words) — background, method (based on actual code), result, conclusion
3. **Keywords** — from actual technologies used in the code
4. **I. Introduction** — problem statement matching what the code addresses
5. **II. Related Work** — only cite frameworks/libraries that appear in the code imports
6. **III. Proposed Methodology / System Design** — describe the real architecture; mention every file
7. **IV. Implementation** — reference actual functions, classes, and logic from the code
8. **V. Experimental Results & Evaluation** — describe outputs based on what the code produces
9. **VI. Discussion** — analysis grounded in the actual implementation
10. **VII. Conclusion & Future Work** — based only on what was built
11. **References** — IEEE format; only real libraries/papers used
""",

    "Technical Blog Post": """
Generate an engaging **Technical Blog Post** in Markdown suitable for dev.to or Medium.
Base everything strictly on the uploaded code. Include:

1. **Catchy Title** with emoji — reflects what the code actually does
2. **Hook** — why this project matters, grounded in the real use case shown in the code
3. **What We Built** — honest overview of every file and its role
4. **Tech Stack** — only what is actually imported/used; explain WHY each was chosen (infer from usage)
5. **How It Works** — walkthrough of the real code: actual function names, flow between files
6. **Key Challenges & Solutions** — based on complexity visible in the actual code
7. **Demo / Results** — describe what the code produces when run
8. **What's Next** — natural extensions of the existing codebase
9. **Conclusion & Call to Action**

Keep it conversational and first-person, but every technical claim must be traceable to the code.
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
    context_hint = f"Additional context from user: {extra_context}" if extra_context else ""
    type_hint    = (
        f"This has been auto-detected as a **{project_type}** project. {project_type_hint}"
        if project_type else ""
    )
    instructions = REPORT_PROMPTS.get(report_type, REPORT_PROMPTS["Final Year Project Report"])

    # Build explicit file list so the model knows what to cover
    file_list = "\n".join(
        f"- {line.strip()}"
        for line in code_context.split("\n")
        if line.strip().startswith("### File:")
    )
    file_hint = f"\nUploaded files you MUST cover:\n{file_list}\n" if file_list else ""

    prompt = f"""You are an expert technical writer generating a grounded, accurate document from real source code.

{name_hint}
{context_hint}
{type_hint}
{file_hint}

{GROUNDING_RULES}

{instructions}

--- SOURCE CODE (ground every claim in this) ---

{code_context}
"""
    return _call(prompt)


def generate_readme(
    code_context: str,
    project_name: str = None,
    extra_context: str = "",
    project_type: str = "",
) -> str:
    name_hint    = f"The project is called '{project_name}'." if project_name else "Infer the project name from filenames and code."
    context_hint = f"Additional context: {extra_context}" if extra_context else ""
    type_hint    = f"This is a **{project_type}** project." if project_type else ""

    file_list = "\n".join(
        f"- {line.strip()}"
        for line in code_context.split("\n")
        if line.strip().startswith("### File:")
    )
    file_hint = f"\nFiles you MUST mention in the Project Structure section:\n{file_list}\n" if file_list else ""

    prompt = f"""You are a senior developer writing a GitHub README grounded strictly in the uploaded source code.

{name_hint}
{context_hint}
{type_hint}
{file_hint}

{GROUNDING_RULES}

Generate a professional **GitHub README.md** including:

1. **Project Title** with emoji — from the code's actual purpose
2. **Shields.io badges** — only for languages/frameworks actually used in the code
3. **Short description** (1–2 lines) — what the code actually does
4. **Table of Contents**
5. **Features** — only features actually implemented in the code
6. **Tech Stack** — only actual imports/dependencies
7. **Project Structure** — real file tree listing every uploaded file with a one-line description of what it does
8. **Installation** — based on actual requirements/dependencies in the code
9. **Usage** — how to actually run this code (infer from entry points like `streamlit run`, `python main.py`, etc.)
10. **API / Module Reference** — list real functions from the code with brief descriptions
11. **Screenshots** placeholder
12. **Contributing**
13. **License** (MIT)
14. **Author** section

--- SOURCE CODE ---

{code_context}
"""
    return _call(prompt)


# ── NLP Evaluation Scores ──────────────────────────────────────────────────────

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


# ── LLM-as-a-Judge ────────────────────────────────────────────────────────────

def evaluate_llm_metrics(generated_text: str, source_code: str) -> dict:
    import json

    gen_snippet = generated_text[:4000]
    src_snippet = source_code[:3000]

    judge_prompt = f"""You are a strict, impartial LLM evaluation judge. Evaluate this AI-generated technical report against the source code it was based on.

Score each metric 0–10 using the rubrics below. Be precise and critical.

---
RUBRIC:

1. HALLUCINATION RATE (0–10) — How much did the model FABRICATE or INVENT content NOT in the source code?
   - 0  = Zero hallucination — every claim is directly traceable to the source code ✅
   - 1–2 = Tiny hallucination — 1 minor unsupported detail
   - 3–5 = Moderate — several invented claims or function names
   - 6–8 = Heavy — many fabricated facts
   - 10  = Completely hallucinated
   → If the report only describes what is actually in the code, score MUST be 0 or 1.
   → Only increase score if you find specific claims NOT in the source code.

2. BIAS RATE (0–10) — How much does the report unfairly emphasise/downplay parts?
   - 0  = Fully balanced — proportional, neutral coverage ✅
   - 1–2 = Very minor imbalance
   - 4–6 = Noticeable imbalance
   - 10  = Completely one-sided
   → If all files are covered proportionally, score MUST be 0 or 1.

3. FAIRNESS (0–10) — Does the report cover ALL uploaded files proportionally?
   - 10 = All files/modules covered proportionally and thoroughly ✅
   - 8–9 = Nearly all files covered
   - 5–7 = Most files covered with minor gaps
   - 3–4 = Uneven — some files significantly underrepresented
   - 0–2 = Only 1–2 files covered, rest ignored
   → If the report mentions every file at least once, score MUST be at least 8.

---
SOURCE CODE (reference):
{src_snippet}

---
GENERATED REPORT (to evaluate):
{gen_snippet}

---
Respond ONLY with a JSON object in this exact format, no extra text:
{{
  "hallucination_rate": <integer 0-10>,
  "hallucination_reason": "<one sentence explaining your score>",
  "bias_rate": <integer 0-10>,
  "bias_reason": "<one sentence explaining your score>",
  "fairness": <integer 0-10>,
  "fairness_reason": "<one sentence explaining your score>"
}}"""

    try:
        raw = _call(judge_prompt, max_tokens=400)
        json_str = re.sub(r"```(?:json)?|```", "", raw).strip()
        match = re.search(r'\{.*\}', json_str, re.DOTALL)
        if not match:
            raise ValueError("No JSON found in judge response")
        data = json.loads(match.group())

        def _norm(val):
            return round(max(0, min(10, int(val))) / 10, 2)

        return {
            "hallucination":        _norm(data.get("hallucination_rate", 5)),
            "hallucination_reason": data.get("hallucination_reason", ""),
            "bias":                 _norm(data.get("bias_rate", 5)),
            "bias_reason":          data.get("bias_reason", ""),
            "fairness":             _norm(data.get("fairness", 5)),
            "fairness_reason":      data.get("fairness_reason", ""),
        }

    except Exception as e:
        return {
            "hallucination":        0.5,
            "hallucination_reason": f"Could not evaluate: {e}",
            "bias":                 0.5,
            "bias_reason":          f"Could not evaluate: {e}",
            "fairness":             0.5,
            "fairness_reason":      f"Could not evaluate: {e}",
        }


# ── Codebase Q&A ──────────────────────────────────────────────────────────────

def answer_code_question(
    question: str,
    code_context: str,
    chat_history: list[dict],
) -> str:
    system = f"""You are an expert code reviewer and technical assistant.
The user has uploaded a codebase. Answer questions about it clearly and accurately.
Reference specific function names, file names, and line-level logic when relevant.
Be concise but complete. Use markdown formatting where helpful.

--- CODEBASE START ---
{code_context[:40000]}
--- CODEBASE END ---
"""
    messages = [{"role": "user", "content": system}]
    for turn in chat_history[-10:]:
        messages.append(turn)
    messages.append({"role": "user", "content": question})

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        max_tokens=1024,
    )
    return response.choices[0].message.content
