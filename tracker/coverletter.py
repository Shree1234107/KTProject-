"""Cover letter generator.

Two ways to write a letter, both free and private:

* ``fill_template``: swap {placeholders} in the user's own template for the
  job's details. No AI, works everywhere.
* ``generate_with_ollama``: ask a model running in Ollama
  (https://ollama.com) on this computer to write a tailored letter in the
  style of the user's template.

``to_pdf`` turns the final text into a downloadable PDF.
"""
from __future__ import annotations

import datetime as _dt
import io
import json
import re
import urllib.error
import urllib.request
import zipfile
from xml.etree import ElementTree as _ET

from fpdf import FPDF

from .ats.extractor import clean_text
from .ats.keywords import extract_keywords, keywords_in_text

OLLAMA_URL = "http://localhost:11434"

PLACEHOLDERS = {
    "{company}": "Company name",
    "{role}": "Job title",
    "{hiring_manager}": "Hiring manager (or 'Hiring Manager')",
    "{skills}": "Skills found in both your resume and the job description",
    "{date}": "Today's date",
}


# ---------------------------------------------------------------------------
# Template fill (no AI)
# ---------------------------------------------------------------------------

def shared_skills(resume_text: str, job_description: str, limit: int = 5) -> list[str]:
    """Skills that the job asks for and the resume already has, most-asked first."""
    if not resume_text.strip() or not job_description.strip():
        return []
    wanted = extract_keywords(clean_text(job_description))
    matched, _ = keywords_in_text(clean_text(resume_text), wanted)
    names = {m["keyword"] for m in matched}
    return [_as_written(k["keyword"], job_description)
            for k in wanted if k["keyword"] in names][:limit]


def unbacked_skills(letter: str, resume_text: str, job_description: str) -> list[str]:
    """Skills from the job posting that the letter mentions but the resume doesn't have.

    Small AI models sometimes claim a required skill anyway; this lets the app
    point it out so the user can fix it before sending.
    """
    if not letter.strip() or not job_description.strip():
        return []
    wanted = extract_keywords(clean_text(job_description))
    _, not_on_resume = keywords_in_text(clean_text(resume_text), wanted)
    in_letter, _ = keywords_in_text(clean_text(letter), not_on_resume)
    names = {m["keyword"] for m in in_letter}
    return [_as_written(k["keyword"], job_description) for k in wanted if k["keyword"] in names]


def _as_written(keyword: str, text: str) -> str:
    """Use the posting's own spelling ("SQL", "Airflow") for a lowercase keyword."""
    m = re.search(r"(?<![A-Za-z0-9])" + re.escape(keyword) + r"(?![A-Za-z0-9])", text, re.I)
    return m.group(0) if m else keyword


def _join(items: list[str]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " and " + items[-1]


def fields_for(company: str, role: str, hiring_manager: str = "",
               skills: list[str] | None = None, today=None) -> dict[str, str]:
    today = today or _dt.date.today()
    return {
        "{company}": company.strip(),
        "{role}": role.strip(),
        "{hiring_manager}": hiring_manager.strip() or "Hiring Manager",
        "{skills}": _join(skills or []),
        "{date}": f"{today:%B} {today.day}, {today.year}",
    }


def fill_template(template: str, fields: dict[str, str]) -> str:
    """Replace each {placeholder}. Unknown braces are left alone."""
    out = template
    for key, val in fields.items():
        out = out.replace(key, val)
    return out


# ---------------------------------------------------------------------------
# Reading a template from a file
# ---------------------------------------------------------------------------

TEMPLATE_TYPES = ["docx", "pdf", "txt", "md"]
_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _docx_text(data: bytes) -> str:
    """Paragraph text from a Word .docx, one paragraph per line."""
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        root = _ET.fromstring(z.read("word/document.xml"))
    lines = []
    for p in root.iter(f"{_W}p"):
        parts = []
        for node in p.iter():
            if node.tag == f"{_W}t" and node.text:
                parts.append(node.text)
            elif node.tag == f"{_W}tab":
                parts.append("\t")
            elif node.tag in (f"{_W}br", f"{_W}cr"):
                parts.append("\n")
        lines.append("".join(parts))
    return "\n".join(lines)


def _tidy(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [ln.rstrip() for ln in text.split("\n")]
    out = "\n".join(lines)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()


def template_from_file(filename: str, data: bytes) -> str:
    """Text of an uploaded template (.docx, .pdf, .txt or .md).

    Raises ValueError with a readable message for unsupported or empty files.
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    try:
        if ext == "docx":
            text = _docx_text(data)
        elif ext == "pdf":
            from .ats.extractor import extract_text_from_pdf
            text = extract_text_from_pdf(data)
        elif ext in ("txt", "md"):
            text = data.decode("utf-8-sig", errors="replace")
        else:
            raise ValueError("Use a .docx, .pdf, .txt or .md file. (For an old .doc file, "
                             "save it as .docx first.)")
    except (zipfile.BadZipFile, KeyError, _ET.ParseError) as e:
        raise ValueError("That Word file couldn't be read. Try saving it again as .docx.") from e
    text = _tidy(text)
    if not text:
        raise ValueError("That file has no text in it. (A scanned PDF won't work; "
                         "paste the text instead.)")
    return text


def placeholders_in(template: str) -> list[str]:
    return [k for k in PLACEHOLDERS if k in template]


# ---------------------------------------------------------------------------
# Ollama (local AI)
# ---------------------------------------------------------------------------

def ollama_models(timeout: float = 2.0) -> list[dict]:
    """Models installed in Ollama, or [] when Ollama isn't running.

    Each item: {"name", "cloud": bool, "size_gb"}, on-device models first,
    smallest first. Cloud models run on
    Ollama's servers, so text sent to them leaves this computer.
    """
    try:
        with urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=timeout) as r:
            data = json.load(r)
    except (urllib.error.URLError, OSError, ValueError):
        return []
    out = []
    for m in data.get("models", []):
        out.append({
            "name": m.get("name", ""),
            "cloud": bool(m.get("remote_model")) or m.get("name", "").endswith(":cloud"),
            "size_gb": round((m.get("size") or 0) / 1e9, 1),
        })
    # On-device first, smallest first (most likely to fit in memory); cloud last.
    out.sort(key=lambda m: (m["cloud"], m["size_gb"]))
    return out


def build_prompt(resume: str, job_description: str, template: str,
                 company: str, role: str, hiring_manager: str = "") -> str:
    fields = fields_for(company, role, hiring_manager)
    return (
        "Write a cover letter for the job below.\n\n"
        "Rules:\n"
        "- Follow the structure, length and tone of MY TEMPLATE closely.\n"
        "- Only mention experience that is in MY RESUME. Never invent jobs, "
        "numbers, schools or skills.\n"
        "- Connect my real experience to what the JOB DESCRIPTION asks for.\n"
        "- If the job asks for a skill or tool that is NOT in MY RESUME, do not "
        "claim it, not even 'familiarity'. Leave it out.\n"
        "- Don't state my class year (senior, junior...) or where I found the "
        "posting. Don't add any fact that isn't in MY RESUME or the JOB DESCRIPTION.\n"
        f"- Address it to {fields['{hiring_manager}']} and date it {fields['{date}']}.\n"
        "- Output only the letter text. No notes, no markdown, no subject line "
        "unless my template has one.\n\n"
        f"COMPANY: {company}\nROLE: {role}\n\n"
        f"MY TEMPLATE:\n{template.strip()}\n\n"
        f"MY RESUME:\n{resume.strip()[:6000]}\n\n"
        f"JOB DESCRIPTION:\n{job_description.strip()[:6000]}\n"
    )


def _friendly(msg: str) -> str:
    if "requires" in msg and "available" in msg:
        return ("this model is too big for your computer's free memory. "
                "Pick a smaller model, or close other apps and try again. "
                f"(Ollama said: {msg})")
    return msg


def _ollama_call(payload: dict, timeout: float) -> dict:
    req = urllib.request.Request(f"{OLLAMA_URL}/api/generate",
                                 data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def guess_company_role(model: str, job_description: str, timeout: float = 120) -> tuple[str, str]:
    """Ask the model for the company and job title named in a posting.

    Returns ("", "") for anything it can't find, so callers can fall back to
    asking the user.
    """
    prompt = (
        "From this job posting, return JSON with two keys: \"company\" (the hiring "
        "company's name) and \"role\" (the job title). Use an empty string if the "
        "posting doesn't say. Copy names exactly as written.\n\n"
        f"POSTING:\n{job_description.strip()[:4000]}"
    )
    try:
        data = _ollama_call({"model": model, "prompt": prompt, "stream": False,
                             "think": False, "format": "json",
                             "options": {"temperature": 0}}, timeout)
        found = json.loads(data.get("response") or "{}")
    except (urllib.error.URLError, OSError, ValueError):
        return "", ""
    clean = lambda v: re.sub(r"\s+", " ", str(v or "")).strip()[:80]
    return clean(found.get("company")), clean(found.get("role"))


_THINK = re.compile(r"<think>.*?</think>", re.S)


def clean_model_output(text: str) -> str:
    text = _THINK.sub("", text)
    text = text.replace("**", "")
    return text.strip()


def generate_with_ollama(model: str, prompt: str, timeout: float = 600) -> str:
    """Ask Ollama for a letter. Raises RuntimeError with a readable message."""
    body = json.dumps({
        "model": model, "prompt": prompt, "stream": False, "think": False,
        "options": {"temperature": 0.6},
    }).encode()
    req = urllib.request.Request(f"{OLLAMA_URL}/api/generate", data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.load(r)
    except urllib.error.HTTPError as e:
        try:
            msg = json.load(e).get("error", str(e))
        except Exception:
            msg = str(e)
        raise RuntimeError(_friendly(msg)) from e
    except (urllib.error.URLError, OSError) as e:
        raise RuntimeError("Couldn't reach Ollama. Is the Ollama app open?") from e
    if data.get("error"):
        raise RuntimeError(_friendly(data["error"]))
    text = clean_model_output(data.get("response", ""))
    if not text:
        raise RuntimeError("The model returned an empty letter. Try again.")
    return text


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------

_LATIN1_SWAPS = {
    "‘": "'", "’": "'", "“": '"', "”": '"',
    "–": "-", "—": "-", "…": "...", "•": "-",
    " ": " ", "→": "->",
}


def _latin1(text: str) -> str:
    for a, b in _LATIN1_SWAPS.items():
        text = text.replace(a, b)
    return text.encode("latin-1", "replace").decode("latin-1")


def to_pdf(text: str, title: str = "Cover letter") -> bytes:
    """A plain, one-column US Letter PDF of the letter text."""
    pdf = FPDF(format="Letter", unit="pt")
    pdf.set_title(_latin1(title))
    pdf.set_margins(72, 72, 72)
    pdf.set_auto_page_break(True, margin=72)
    pdf.add_page()
    pdf.set_font("Times", size=11.5)
    for para in _latin1(text.strip()).split("\n"):
        if para.strip():
            pdf.multi_cell(0, 16, para.rstrip(), new_x="LMARGIN", new_y="NEXT")
        else:
            pdf.ln(10)
    return bytes(pdf.output())


def file_name(company: str, role: str) -> str:
    slug = "_".join(re.sub(r"[^A-Za-z0-9]+", "", w) for w in f"{company} {role}".split())
    return f"Cover_Letter_{slug or 'Job'}.pdf"
