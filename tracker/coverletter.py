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
# Template structure: header / greeting / body / sign-off
# ---------------------------------------------------------------------------

_GREETING = re.compile(r"^\s*(dear|to whom|hello|hi|greetings)\b", re.I)
_CLOSING = re.compile(
    r"^\s*(sincerely|best|kind regards|warm regards|regards|respectfully|"
    r"thank you|thanks|yours truly|yours sincerely|cordially|with gratitude)\b.{0,20}$",
    re.I,
)
# Parenthetical notes to the writer, e.g. "(remove if job is outside CO)".
# Phone area codes like "(303)" are left alone.
_NOTE = re.compile(r"\s*\((?=[^)]*[A-Za-z]{3})[^)]*\)")


def strip_notes(line: str) -> str:
    return re.sub(r"[ \t]{2,}", "  ", _NOTE.sub("", line)).rstrip()


def split_template(template: str) -> dict | None:
    """Split a template into header lines, greeting, body and sign-off lines.

    Returns None when there is no greeting ("Dear ...") or no sign-off
    ("Sincerely," ...) to anchor on.
    """
    lines = template.strip().split("\n")
    g = next((i for i, ln in enumerate(lines) if _GREETING.match(ln)), None)
    if g is None:
        return None
    c = next((i for i in range(len(lines) - 1, g, -1) if _CLOSING.match(lines[i])), None)
    if c is None:
        return None
    body = "\n".join(lines[g + 1:c]).strip()
    paragraphs = [b for b in re.split(r"\n\s*\n", body) if b.strip()]
    return {
        "header": [ln for ln in lines[:g] if ln.strip()],
        "greeting": lines[g],
        "body": body,
        "paragraphs": max(2, min(5, len(paragraphs))),
        "closing": lines[c:],
    }


def greeting_line(template_greeting: str, hiring_manager: str = "") -> str:
    if hiring_manager.strip():
        return f"Dear {hiring_manager.strip()},"
    text = strip_notes(template_greeting).strip().rstrip(",:")
    word, _, rest = text.partition(" ")
    rest = rest.split("/")[0].strip() or "Hiring Manager"   # "Hiring Manager/Committee"
    return f"{word} {rest},"


def _resume_name(resume: str) -> str:
    first = next((ln.strip() for ln in resume.split("\n") if ln.strip()), "")
    return first if 1 < len(first.split()) <= 5 else ""


_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_PHONE = re.compile(r"(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}")
_LINKEDIN = re.compile(r"(?:https?://)?(?:www\.)?linkedin\.com/in/[\w-]+/?", re.I)


def use_real_contacts(lines: list[str], resume: str) -> list[str]:
    """Replace any email, phone or LinkedIn URL in the lines with the resume's own."""
    real = {}
    for key, rx in (("email", _EMAIL), ("phone", _PHONE), ("linkedin", _LINKEDIN)):
        m = rx.search(resume)
        if m:
            real[key] = m.group(0)
    out = []
    for ln in lines:
        if "linkedin" in real:
            ln = _LINKEDIN.sub(real["linkedin"], ln)
        if "email" in real:
            ln = _EMAIL.sub(real["email"], ln)
        if "phone" in real:
            ln = _PHONE.sub(real["phone"], ln)
        out.append(ln)
    return out


def _assemble(header: list[str], greeting: str, paragraphs: list[str],
              closing: list[str]) -> str:
    parts = []
    if header:
        parts.append("\n".join(header))
    parts.append(greeting)
    parts.extend(p.strip() for p in paragraphs if p.strip())
    out = "\n\n".join(parts) + "\n\n" + "\n".join(closing).strip()
    return re.sub(r"\n{3,}", "\n\n", out).strip()


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


_CLICHES = ("I am excited to", "I am thrilled", "passionate about", "leverage",
            "dynamic", "fast-paced", "synergy", "I believe I would be a great fit",
            "hit the ground running", "team player")


def style_rules(resume: str, job_description: str, voice: str = "") -> str:
    """Prompt rules that make the letter sound like the user and use the posting's words."""
    terms = shared_skills(resume, job_description, limit=10)
    out = []
    if terms:
        out.append("- Use these exact words from the job posting, each where it truthfully "
                   "fits my experience: " + ", ".join(terms) + ".")
    out.append("- Reuse the posting's own phrasing for what the team does, instead of "
               "generic praise for the company.")
    out.append("- Sound like a real person, not a template. Avoid: "
               + "; ".join(f"'{c}'" for c in _CLICHES) + ".")
    if voice.strip():
        out.append("- Write in MY VOICE: copy the sentence length, word choice, tone and "
                   "level of formality of MY WRITING SAMPLE. Do not copy its facts.")
    return "\n".join(out) + "\n"


def voice_block(voice: str) -> str:
    return f"\nMY WRITING SAMPLE (style only):\n{voice.strip()[:3000]}\n" if voice.strip() else ""


def revise_letter(model: str, letter: str, request: str, resume: str,
                  job_description: str, voice: str = "") -> str:
    """Rewrite a letter following the user's instructions, staying honest."""
    prompt = (
        "Revise my cover letter following MY REQUEST.\n\n"
        "Rules:\n"
        "- Do exactly what MY REQUEST asks. Keep everything else that already works.\n"
        "- Keep the header, greeting and sign-off lines unless the request is about them.\n"
        "- Only use experience that is in MY RESUME. Never invent jobs, numbers, courses, "
        "tools or skills, even if the request asks for them; leave those out.\n"
        + style_rules(resume, job_description, voice) +
        "- Output only the full revised letter. No notes, no markdown.\n\n"
        f"MY REQUEST:\n{request.strip()[:1500]}\n\n"
        f"MY LETTER:\n{letter.strip()[:6000]}\n"
        + voice_block(voice) +
        f"\nMY RESUME:\n{resume.strip()[:5000]}\n\n"
        f"JOB DESCRIPTION:\n{job_description.strip()[:5000]}\n"
    )
    return generate_with_ollama(model, prompt, temperature=0.5)


def build_prompt(resume: str, job_description: str, template: str,
                 company: str, role: str, hiring_manager: str = "",
                 voice: str = "") -> str:
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
        + style_rules(resume, job_description, voice) +
        f"- Address it to {fields['{hiring_manager}']} and date it {fields['{date}']}.\n"
        "- Output only the letter text. No notes, no markdown, no subject line "
        "unless my template has one.\n\n"
        f"COMPANY: {company}\nROLE: {role}\n\n"
        f"MY TEMPLATE:\n{template.strip()}\n\n"
        f"MY RESUME:\n{resume.strip()[:6000]}\n\n"
        f"JOB DESCRIPTION:\n{job_description.strip()[:6000]}\n"
        + voice_block(voice)
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


def _fill_lines_with_ai(model: str, lines: list[str], resume: str) -> list[str]:
    """Swap sample details in header/sign-off lines for the real ones from the resume."""
    if not lines:
        return []
    prompt = (
        "These lines are from a cover letter template. Replace every sample or "
        "placeholder detail (name, city, email, phone, LinkedIn URL, degree, "
        "major, class year, blanks like ____) with my real details from MY RESUME. "
        "A line that is a document title such as 'X COVER LETTER TEMPLATE' "
        "becomes my full name. Remove notes in parentheses. Keep the same order "
        "and separators. If my resume doesn't have a detail, drop that piece.\n"
        'Return JSON: {"lines": [one string per input line, same count]}\n\n'
        f"LINES:\n{json.dumps(lines)}\n\nMY RESUME:\n{resume.strip()[:4000]}"
    )
    try:
        raw = generate_with_ollama(model, prompt, json_mode=True, temperature=0, timeout=180)
        out = json.loads(raw).get("lines", [])
    except (RuntimeError, ValueError, AttributeError):
        out = []
    if not isinstance(out, list) or len(out) != len(lines):
        out = lines
    name = _resume_name(resume)
    fixed = []
    for orig, new in zip(lines, out):
        new = strip_notes(str(new))
        if re.search(r"\btemplate\b", new, re.I) or re.search(r"\btemplate\b", orig, re.I) and not new.strip():
            new = name
        fixed.append(new)
    return use_real_contacts(fixed, resume)


def write_letter_from_template(model: str, resume: str, job_description: str,
                               template: str, company: str, role: str,
                               hiring_manager: str = "", voice: str = "") -> str:
    """AI letter that keeps the template's header, greeting and sign-off.

    The model writes only the body paragraphs (as many as the template has);
    the header and sign-off lines are the template's own, filled in with the
    resume's details. Falls back to a whole-letter prompt when the template
    has no greeting/sign-off to anchor on.
    """
    parts = split_template(fill_template(template, fields_for(company, role, hiring_manager)))
    if parts is None:
        return generate_with_ollama(model, build_prompt(
            resume, job_description, template, company, role, hiring_manager, voice))

    n = parts["paragraphs"]
    body_prompt = (
        f"Write the body of my cover letter for the {role} position at {company}: "
        f"exactly {n} paragraphs, separated by one blank line, about "
        f"{60 * n + 120} words in total.\n\n"
        "Rules:\n"
        "- Follow the guidance or mirror the sample in TEMPLATE BODY, paragraph by "
        "paragraph. Do not copy its instructions or brackets into the letter.\n"
        "- Only use experience that is in MY RESUME. Never invent jobs, numbers, "
        "courses or skills. If the job wants a skill I don't have, leave it out.\n"
        "- Don't describe my class year with a word like 'senior' or 'junior'. You "
        "may give my expected graduation date exactly as my resume states it.\n"
        "- Don't say where I found the posting.\n"
        + style_rules(resume, job_description, voice) +
        "- No greeting, no sign-off, no name, no headings, no markdown. Only the "
        f"{n} paragraphs.\n\n"
        f"TEMPLATE BODY:\n{parts['body'][:4000]}\n\n"
        f"MY RESUME:\n{resume.strip()[:5000]}\n\n"
        f"JOB DESCRIPTION:\n{job_description.strip()[:5000]}\n"
        + voice_block(voice)
    )
    body = generate_with_ollama(model, body_prompt)
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
    paragraphs = [p for p in paragraphs
                  if not _GREETING.match(p) and not _CLOSING.match(p.split("\n")[0])]

    header = [ln for ln in _fill_lines_with_ai(model, parts["header"], resume) if ln.strip()]
    closing = _fill_lines_with_ai(model, parts["closing"], resume)
    return _assemble(header, greeting_line(parts["greeting"], hiring_manager),
                     paragraphs, closing)


_THINK = re.compile(r"<think>.*?</think>", re.S)


def clean_model_output(text: str) -> str:
    text = _THINK.sub("", text)
    text = text.replace("**", "")
    return text.strip()


def generate_with_ollama(model: str, prompt: str, timeout: float = 600,
                         json_mode: bool = False, temperature: float = 0.6) -> str:
    """Ask Ollama for text. Raises RuntimeError with a readable message."""
    payload = {
        "model": model, "prompt": prompt, "stream": False, "think": False,
        "options": {"temperature": temperature},
    }
    if json_mode:
        payload["format"] = "json"
    body = json.dumps(payload).encode()
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
    if json_mode:
        return data.get("response", "")
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
    """A US Letter PDF of the letter, laid out like the text.

    Lines keep their breaks and blank lines. Text is left-aligned (not
    justified, so no stretched gaps between words). If the letter has a
    header above the greeting (name, contact line), it is centered and the
    first line is bold, like a letterhead.
    """
    lines = _latin1(text.strip()).split("\n")
    g = next((i for i, ln in enumerate(lines) if _GREETING.match(ln)), None)
    header_n = 0
    if g is not None:
        header_n = len([ln for ln in lines[:g] if ln.strip()])
        if header_n > 4:
            header_n = 0

    pdf = FPDF(format="Letter", unit="pt")
    pdf.set_title(_latin1(title))
    pdf.set_margins(72, 66, 72)
    pdf.set_auto_page_break(True, margin=66)
    pdf.add_page()
    seen_header = 0
    for ln in lines:
        if not ln.strip():
            pdf.ln(9)
            continue
        if seen_header < header_n:
            first = seen_header == 0
            pdf.set_font("Times", style="B" if first else "", size=15 if first else 10.5)
            pdf.multi_cell(0, 18 if first else 13, ln.strip(), align="C",
                           new_x="LMARGIN", new_y="NEXT")
            seen_header += 1
            if seen_header == header_n:
                pdf.ln(6)
            continue
        pdf.set_font("Times", size=11.5)
        pdf.multi_cell(0, 14.5, ln.rstrip(), align="L", new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())


def file_name(company: str, role: str) -> str:
    slug = "_".join(re.sub(r"[^A-Za-z0-9]+", "", w) for w in f"{company} {role}".split())
    return f"Cover_Letter_{slug or 'Job'}.pdf"


# ---------------------------------------------------------------------------
# Word (.docx) output
# ---------------------------------------------------------------------------

def _parts(lines: list[str]) -> list[str]:
    """Label each line: header / greeting / body / closing / sign (after closing) / blank."""
    g = next((i for i, ln in enumerate(lines) if _GREETING.match(ln)), None)
    c = next((i for i, ln in enumerate(lines) if _CLOSING.match(ln)
              and (g is None or i > g)), None)
    out = []
    for i, ln in enumerate(lines):
        if not ln.strip():
            out.append("blank")
        elif g is not None and i < g:
            out.append("header")
        elif i == g:
            out.append("greeting")
        elif i == c:
            out.append("closing")
        elif c is not None and i > c:
            out.append("sign")
        else:
            out.append("body")
    return out


def _plain_docx(lines: list[str]):
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Pt, Inches

    doc = Document()
    for s in doc.sections:
        s.left_margin = s.right_margin = Inches(1)
        s.top_margin = s.bottom_margin = Inches(0.9)
    normal = doc.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(11.5)
    normal.paragraph_format.space_after = Pt(0)
    labels = _parts(lines)
    header_n = labels.count("header")
    seen = 0
    for ln, lab in zip(lines, labels):
        p = doc.add_paragraph()
        if lab == "blank":
            continue
        run = p.add_run(ln.strip() if lab == "header" else ln.rstrip())
        if lab == "header" and header_n <= 4:
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            if seen == 0:
                run.bold = True
                run.font.size = Pt(15)
            else:
                run.font.size = Pt(10.5)
            seen += 1
    return doc


def _styled_docx(lines: list[str], template_docx: bytes):
    """Rebuild the letter inside the user's own Word template, copying the
    paragraph and font formatting of the matching template part."""
    import copy
    from docx import Document
    from docx.oxml.ns import qn

    doc = Document(io.BytesIO(template_docx))
    tpl = [p for p in doc.paragraphs]
    tlines = [p.text for p in tpl]
    tlabels = _parts(tlines)
    if "greeting" not in tlabels:
        raise ValueError("no greeting in template")
    samples: dict[str, list] = {}
    for p, lab in zip(tpl, tlabels):
        samples.setdefault(lab, []).append(p)
    has_blank_paras = "blank" in samples

    def fmt(p):
        ppr = p._p.pPr
        r = next((r for r in p.runs if r.text.strip()), p.runs[0] if p.runs else None)
        rpr = r._r.rPr if r is not None else None
        return (copy.deepcopy(ppr) if ppr is not None else None,
                copy.deepcopy(rpr) if rpr is not None else None)

    body = doc.element.body
    for el in list(body):
        if el.tag != qn("w:sectPr"):
            body.remove(el)
    sect = body.find(qn("w:sectPr"))

    labels = _parts(lines)
    counters: dict[str, int] = {}
    for ln, lab in zip(lines, labels):
        if lab == "blank" and not has_blank_paras:
            continue  # template spaces paragraphs itself
        pool = samples.get(lab) or samples.get("body") or tpl
        i = counters.get(lab, 0)
        counters[lab] = i + 1
        src = pool[min(i, len(pool) - 1)]
        ppr, rpr = fmt(src)
        new_p = copy.deepcopy(src._p)
        for child in list(new_p):
            new_p.remove(child)
        if ppr is not None:
            new_p.append(ppr)
        if lab != "blank":
            r = new_p.makeelement(qn("w:r"), {})
            if rpr is not None:
                r.append(rpr)
            t = r.makeelement(qn("w:t"), {})
            t.text = ln.strip() if lab == "header" else ln.rstrip()
            t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            r.append(t)
            new_p.append(r)
        if sect is not None:
            sect.addprevious(new_p)
        else:
            body.append(new_p)
    return doc


def to_docx(text: str, template_docx: bytes | None = None) -> bytes:
    """A Word file of the letter. With the user's .docx template, it keeps that
    file's fonts, sizes, alignment, spacing and page margins."""
    lines = text.strip().split("\n")
    doc = None
    if template_docx:
        try:
            doc = _styled_docx(lines, template_docx)
        except Exception:  # odd template: fall back to the plain layout
            doc = None
    if doc is None:
        doc = _plain_docx(lines)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
