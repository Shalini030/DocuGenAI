from groq import Groq

# ✅ Paste your Groq API key here (free at console.groq.com)
GROQ_API_KEY = "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"

client = Groq(api_key=GROQ_API_KEY)
MODEL = "llama-3.3-70b-versatile"


def _call(prompt: str) -> str:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=4096,
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
    report_type: str = "Final Year Project Report"
) -> str:
    name_hint    = f"The project is called '{project_name}'." if project_name else "Infer the project name from the code."
    context_hint = f"Additional context: {extra_context}" if extra_context else ""
    instructions = REPORT_PROMPTS.get(report_type, REPORT_PROMPTS["Final Year Project Report"])

    prompt = f"""You are an expert technical writer. Analyze the following source code and generate the document described below.

{name_hint}
{context_hint}

{instructions}

Be specific — reference actual function names, file names, and logic from the code. Write in formal/appropriate tone for the document type.

---

{code_context}
"""
    return _call(prompt)


def generate_readme(code_context: str, project_name: str = None, extra_context: str = "") -> str:
    name_hint    = f"The project is called '{project_name}'." if project_name else "Infer the project name from the code."
    context_hint = f"Additional context: {extra_context}" if extra_context else ""

    prompt = f"""You are a senior developer. Analyze the following source code and generate a professional **GitHub README.md**.

{name_hint}
{context_hint}

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
