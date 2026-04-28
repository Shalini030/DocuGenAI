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


def _call(prompt: str, max_tokens: int = 4096) -> str:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content


# ── Report type → prompt instructions ──────────────────────────────────────────
REPORT_PROMPTS = {
    "Final Year Project Report": """
Generate a comprehensive **Final Year Project Report** in formal academic Markdown format.
Include ALL of these sections:
1. Project Title
2. Abstract (150–200 words)
3. Introduction (problem statement, motivation, objectives)
4. Literature Review / Related Work (3–5 references)
5. System Architecture
6. Modules / Features
7. Tech Stack
8. Implementation Details
9. Results & Discussion
10. Conclusion
11. Future Scope
12. References
""",
    "Internship Report": """
Generate a professional **Internship Report** in Markdown format.
Include ALL of these sections:
1. Title Page (Project/Company/Duration)
2. Executive Summary
3. Introduction & Internship Objectives
4. Company/Project Overview
5. Work Done Week-by-Week (summarize tasks)
6. Technologies & Tools Used
7. Key Learnings & Skills Gained
8. Challenges & How They Were Resolved
9. Conclusion
10. Future Recommendations
""",
    "Research Paper": """
Generate an **IEEE/ACM-style Research Paper** in Markdown format.
Include ALL of these sections:
1. Title & Authors (use placeholders)
2. Abstract (200 words, structured: background, method, result, conclusion)
3. Keywords
4. I. Introduction
5. II. Related Work (cite 5+ real frameworks/papers relevant to the tech)
6. III. Proposed Methodology / System Design
7. IV. Implementation
8. V. Experimental Results & Evaluation
9. VI. Discussion
10. VII. Conclusion & Future Work
11. References (IEEE format)
""",
    "Technical Blog Post": """
Generate an engaging **Technical Blog Post** in Markdown format, suitable for dev.to or Medium.
Include:
1. Catchy Title with emoji
2. Hook paragraph (why this matters)
3. What We Built (brief overview)
4. Tech Stack (with why each was chosen)
5. How It Works (walkthrough with code snippets)
6. Key Challenges & Solutions
7. Demo / Results
8. What's Next
9. Conclusion & Call to Action (share/star/contribute)

Keep it conversational, use first-person, add humor where appropriate.
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
    name_hint    = f"The project is called '{project_name}'." if project_name else "Infer the project name from the code."
    context_hint = f"Additional context: {extra_context}" if extra_context else ""
    type_hint    = (
        f"This has been auto-detected as a **{project_type}** project. {project_type_hint}"
        if project_type else ""
    )
    instructions = REPORT_PROMPTS.get(report_type, REPORT_PROMPTS["Final Year Project Report"])

    prompt = f"""You are an expert technical writer. Analyze the following source code and generate the document described below.

{name_hint}
{context_hint}
{type_hint}

{instructions}

Be specific — reference actual function names, file names, and logic from the code. Write in formal/appropriate tone for the document type.

---

{code_context}
"""
    return _call(prompt)


def generate_readme(
    code_context: str,
    project_name: str = None,
    extra_context: str = "",
    project_type: str = "",
) -> str:
    name_hint    = f"The project is called '{project_name}'." if project_name else "Infer the project name from the code."
    context_hint = f"Additional context: {extra_context}" if extra_context else ""
    type_hint    = f"This is a **{project_type}** project." if project_type else ""

    prompt = f"""You are a senior developer. Analyze the following source code and generate a professional **GitHub README.md**.

{name_hint}
{context_hint}
{type_hint}

Include:
1. Project Title with emoji
2. Shields.io badges for detected languages/frameworks
3. Short description (1–2 lines)
4. Table of Contents
5. Features (bullet list)
6. Tech Stack
7. Project Structure (file tree)
8. Installation (step-by-step)
9. Usage (with example commands)
10. API / Module Reference (if applicable)
11. Screenshots placeholder
12. Contributing
13. License (MIT)
14. Author section

Use proper Markdown with code blocks, tables, and headers.

---

{code_context}
"""
    return _call(prompt)


# ── NLP Evaluation Scores ─────────────────────────────────────────────────────

def evaluate_scores(generated_text: str, reference_text: str) -> dict:
    """
    Computes ROUGE-1, ROUGE-L, and BLEU scores.
    
    - reference_text : the source code (what the report is based on)
    - generated_text : the AI-generated report / README
    
    Returns a dict with keys:
        rouge1_p, rouge1_r, rouge1_f
        rougeL_p, rougeL_r, rougeL_f
        bleu
    All values are floats in [0, 1].
    """
    # Strip markdown syntax so scoring is on plain text tokens
    def strip_md(text: str) -> str:
        text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
        text = re.sub(r"[#*_`>~\[\]()!]", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip().lower()

    gen_clean = strip_md(generated_text)
    ref_clean = strip_md(reference_text)

    # ── ROUGE ──────────────────────────────────────────────────────────────────
    scorer = rouge_scorer.RougeScorer(["rouge1", "rougeL"], use_stemmer=True)
    scores = scorer.score(ref_clean, gen_clean)

    r1 = scores["rouge1"]
    rl = scores["rougeL"]

    # ── BLEU ───────────────────────────────────────────────────────────────────
    ref_tokens = ref_clean.split()
    hyp_tokens = gen_clean.split()

    # Use smoothing to handle zero n-gram matches gracefully
    smoother = SmoothingFunction().method1
    bleu = sentence_bleu(
        [ref_tokens],
        hyp_tokens,
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


# ── LLM-as-a-Judge: Hallucination, Bias, Fairness ─────────────────────────────

def evaluate_llm_metrics(generated_text: str, source_code: str) -> dict:
    """
    Uses the LLM itself as a judge (LLM-as-a-Judge pattern) to evaluate:

      - Hallucination : Did the model invent facts, functions, or claims
                        not present in or inferable from the source code?
                        Score 0–10 where 0 = heavily hallucinated, 10 = fully grounded.

      - Bias          : Does the report favour certain technologies, approaches,
                        or framings unfairly, or does it over/under-represent
                        parts of the codebase?
                        Score 0–10 where 0 = heavily biased, 10 = fully balanced.

      - Fairness      : Is the report equally thorough across all files/modules?
                        Does it give proportional coverage without ignoring
                        smaller but important components?
                        Score 0–10 where 0 = very unfair coverage, 10 = fully fair.

    Returns dict with keys: hallucination, bias, fairness (each float 0.0–1.0),
    plus reasoning strings for each.
    """
    import json

    # Truncate inputs to stay within token budget
    gen_snippet = generated_text[:4000]
    src_snippet = source_code[:3000]

    judge_prompt = f"""You are a strict, impartial LLM evaluation judge. Your task is to evaluate an AI-generated technical report against the source code it was based on.

Score each metric from 0 to 10 using the rubrics below. Be precise and critical.

---
RUBRIC:

1. HALLUCINATION RATE (0–10)
   Evaluate: How much did the model fabricate or invent content NOT present in the source code?
   - 0   : Zero hallucination — every claim is directly traceable to the source code
   - 1–3 : Minimal hallucination — 1–2 minor unsupported details
   - 4–6 : Moderate hallucination — several invented claims or function names
   - 7–9 : Heavy hallucination — many fabricated facts not in the code
   - 10  : Completely hallucinated — almost no grounding in the source code
   NOTE: Give score 0 if the report only describes what is actually in the code.

2. BIAS RATE (0–10)
   Evaluate: How much does the report unfairly emphasise or downplay parts of the codebase?
   - 0   : Fully balanced — proportional, neutral coverage of all components
   - 1–3 : Very minor imbalance, mostly fair
   - 4–6 : Noticeable imbalance in coverage or tone
   - 7–9 : Heavily skewed toward certain parts
   - 10  : Completely one-sided — major parts ignored or over-hyped
   NOTE: Give score 0 if the report covers all parts proportionally.

3. FAIRNESS (0–10)
   Evaluate: Does the report give proportionally equal and thorough coverage to all files and modules?
   - 0   : Only 1–2 files covered, rest ignored entirely
   - 3–4 : Uneven coverage — some files significantly underrepresented
   - 5–7 : Most files covered with minor gaps
   - 8–9 : Nearly all files covered proportionally
   - 10  : All files/modules covered proportionally and thoroughly

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
            """Normalise 0–10 integer to 0.0–1.0 float."""
            return round(max(0, min(10, int(val))) / 10, 2)

        return {
            # hallucination & bias: raw score = rate (lower is better)
            "hallucination":        _norm(data.get("hallucination_rate", 5)),
            "hallucination_reason": data.get("hallucination_reason", ""),
            "bias":                 _norm(data.get("bias_rate", 5)),
            "bias_reason":          data.get("bias_reason", ""),
            # fairness: higher is better (0=bad, 1=perfect)
            "fairness":             _norm(data.get("fairness", 5)),
            "fairness_reason":      data.get("fairness_reason", ""),
        }

    except Exception as e:
        # Graceful fallback — never crash the app
        return {
            "hallucination":        0.5,
            "hallucination_reason": f"Could not evaluate: {e}",
            "bias":                 0.5,
            "bias_reason":          f"Could not evaluate: {e}",
            "fairness":             0.5,
            "fairness_reason":      f"Could not evaluate: {e}",
        }


# ── NEW: Codebase Q&A ──────────────────────────────────────────────────────────

def answer_code_question(
    question: str,
    code_context: str,
    chat_history: list[dict],
) -> str:
    """
    Answer a natural-language question about the uploaded codebase.
    chat_history is a list of {"role": "user"|"assistant", "content": str}.
    """
    system = f"""You are an expert code reviewer and technical assistant.
The user has uploaded a codebase. Your job is to answer questions about it clearly and accurately.
Reference specific function names, file names, and line-level logic when relevant.
Be concise but complete. Use markdown formatting where helpful (code blocks, bullet points).

--- CODEBASE START ---
{code_context[:40000]}
--- CODEBASE END ---
"""
    messages = [{"role": "user", "content": system}]
    # Inject prior turns
    for turn in chat_history[-10:]:   # keep last 10 turns to stay within context
        messages.append(turn)
    messages.append({"role": "user", "content": question})

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        max_tokens=1024,
    )
    return response.choices[0].message.content
