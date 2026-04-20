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


def generate_documentation(code_context: str, project_name: str = None, extra_context: str = "") -> str:
    name_hint = f"The project is called '{project_name}'." if project_name else "Infer the project name from the code."
    context_hint = f"Additional context from the user: {extra_context}" if extra_context else ""

    prompt = f"""You are an expert academic technical writer. Analyze the following source code and generate a comprehensive **Final Year Project Report** in Markdown format.

{name_hint}
{context_hint}

The report must include ALL of the following sections, written in a formal academic tone:

1. **Project Title**
2. **Abstract** (150–200 words summarizing the project)
3. **Introduction** (problem statement, motivation, objectives)
4. **Literature Review / Related Work** (mention 3–5 relevant technologies or prior work)
5. **System Architecture** (describe components and how they interact)
6. **Modules / Features** (describe each major module/feature with purpose)
7. **Tech Stack** (list and briefly explain each technology used)
8. **Implementation Details** (key algorithms, logic, or design patterns used)
9. **Results & Discussion** (expected outcomes, performance, use cases)
10. **Conclusion**
11. **Future Scope**
12. **References** (cite the technologies/frameworks used)

Infer everything from the code provided. Be specific — reference actual function names, file names, and logic from the code.

---

{code_context}
"""
    return _call(prompt)


def generate_readme(code_context: str, project_name: str = None, extra_context: str = "") -> str:
    name_hint = f"The project is called '{project_name}'." if project_name else "Infer the project name from the code."
    context_hint = f"Additional context: {extra_context}" if extra_context else ""

    prompt = f"""You are a senior developer writing documentation. Analyze the following source code and generate a professional **GitHub README.md** in standard Markdown format.

{name_hint}
{context_hint}

The README must include:

1. **Project Title** with a relevant emoji
2. **Badges** (use shields.io badges for detected languages/frameworks)
3. **Short Description** (1–2 lines)
4. **Table of Contents**
5. **Features** (bullet list)
6. **Tech Stack** (with version info if detectable)
7. **Project Structure** (file/folder tree based on uploaded files)
8. **Installation** (step-by-step setup commands)
9. **Usage** (how to run with example commands)
10. **API / Module Reference** (list key functions/endpoints if applicable)
11. **Screenshots** (placeholder: `![Screenshot](./screenshots/demo.png)`)
12. **Contributing**
13. **License** (MIT)
14. **Author** section

Use proper Markdown: headers, code blocks with language hints, tables where appropriate.

---

{code_context}
"""
    return _call(prompt)