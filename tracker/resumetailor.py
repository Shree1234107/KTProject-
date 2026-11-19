"""Tailor a resume to a job posting with the local AI (Ollama), honestly.

The model may reorder, reword and emphasise what is already on the resume, and
use the posting's own words for it. It may not add jobs, numbers, tools or
skills, except the missing keywords the user has confirmed they really have.
``added_claims`` double-checks the result so anything new can be flagged.
"""
from __future__ import annotations

import io
import json
import re

from tracker import coverletter as cl


_BULLET = re.compile(r"^\s*[-•*–▪]\s*")
_NUM = re.compile(r"\d[\d,.]*\s*[%xX+kKmM]?")
_INFLATE = ("expert", "expertise", "led", "lead", "managed", "senior", "spearheaded",
            "mastery", "advanced", "extensive", "pipelines")
_SUMMARY = ("SUMMARY", "PROFILE", "OBJECTIVE", "ABOUT")


def _is_heading(line: str) -> bool:
    s = line.strip()
    return bool(s) and s.isupper() and len(s) < 40 and not _BULLET.match(s)


def _rewritable(lines: list[str]) -> list[int]:
    """Indexes of bullet lines and summary sentences: the only lines the AI may touch."""
    out, section = [], ""
    for i, line in enumerate(lines):
        if _is_heading(line):
            section = line.strip().upper()
        elif _BULLET.match(line) or (line.strip() and section.startswith(_SUMMARY)):
            out.append(i)
    return out


def _relevance(line: str, job_description: str) -> int:
    return len(cl.shared_skills(line, job_description, limit=50))


def _numbers(text: str) -> set[str]:
    return {re.sub(r"\s", "", n).rstrip(".,").lower() for n in _NUM.findall(text)}


def _stem(word: str) -> str:
    """Rough word root: "collaborated", "collaboration", "collaborate" → "collab"."""
    w = word.lower()
    return w[:6] if len(w) >= 7 else w


def _backed_by_line(term: str, line: str) -> bool:
    """True when every word of a keyword shares a root with a word in the line
    (e.g. "collaboration" is backed by "Collaborated")."""
    roots = {_stem(w) for w in re.findall(r"[a-zA-Z]+", line)}
    return all(_stem(w) in roots for w in re.findall(r"[a-zA-Z]+", term))


def soft_terms(job_description: str) -> list[str]:
    """Soft-skill keywords from the posting (communication, collaboration...)."""
    from tracker.ats.keywords import extract_keywords
    from tracker.ats.extractor import clean_text
    return [k["keyword"] for k in extract_keywords(clean_text(job_description))
            if k.get("category") == "Soft skills"]


def bullet_ok(new: str, old: str, job_description: str, confirmed: list[str]) -> bool:
    """True when a rewritten line keeps every number and claims no new skill."""
    if not new.strip() or len(new) > len(old) * 1.6 + 40:
        return False
    if not _numbers(old) <= _numbers(new):
        return False
    old_words = set(re.findall(r"[a-z]+", old.lower()))
    if any(w in re.findall(r"[a-z]+", new.lower()) and w not in old_words for w in _INFLATE):
        return False
    soft = {t.lower() for t in soft_terms(job_description)}
    extra = cl.unbacked_skills(new, old + "\n" + "\n".join(confirmed), job_description)
    return all(t.lower() in soft or _backed_by_line(t, old) for t in extra)


def _rewrite_lines(model: str, lines: list[str], job_description: str,
                   request: str, confirmed: list[str]) -> list[str]:
    terms = cl.shared_skills("\n".join(lines), job_description, limit=12)
    from tracker.ats.keywords import extract_keywords, keywords_in_text
    from tracker.ats.extractor import clean_text
    wanted = extract_keywords(clean_text(job_description))
    _, gaps = keywords_in_text(clean_text("\n".join(lines)), wanted)
    gap_terms = [g["keyword"] for g in gaps
                 if g.get("category") == "Soft skills" or g["keyword"] in [c.lower() for c in confirmed]
                 or any(_backed_by_line(g["keyword"], l) for l in lines)]
    prompt = (
        "Rewrite each resume line below so it fits the job posting better.\n"
        "Rules:\n"
        "- One output line per input line, same order, same count.\n"
        "- Keep the meaning, every number, and every tool or product name. Never add "
        "a tool, skill, number, employer or result that the line doesn't already say.\n"
        "- Start with a strong past-tense verb. About the same length.\n"
        "- Where it truthfully describes the same work, use the posting's own words"
        + (" (for example: " + ", ".join(terms) + ")" if terms else "") + ".\n"
        + ("- The posting's screening software looks for these exact words. Work each one "
           "into a line that already describes that work: " + ", ".join(gap_terms) + ".\n"
           if gap_terms else "")
        + "- Reuse the posting's exact phrases (e.g. how it names the work, the product, the "
        "team) instead of your own synonyms, when they describe the same thing.\n"
        + (f"- Also follow this request where it doesn't break a rule: {request.strip()[:600]}\n"
           if request.strip() else "")
        + 'Return JSON: {"lines": ["...", "..."]}\n\n'
        f"LINES:\n{json.dumps(lines)}\n\nJOB POSTING:\n{job_description.strip()[:4000]}"
    )
    try:
        raw = cl.generate_with_ollama(model, prompt, json_mode=True, temperature=0.3, timeout=300)
        out = json.loads(raw).get("lines", [])
    except (ValueError, AttributeError):
        return lines
    if not isinstance(out, list) or len(out) != len(lines):
        return lines
    return [str(o).strip() for o in out]


def tailor_resume(model: str, resume: str, job_description: str,
                  confirmed: list[str] | None = None, request: str = "",
                  current: str = "") -> str:
    """Tailored copy of the resume. Structure and facts stay exactly as written.

    Headings, names, titles, companies, dates and education are copied verbatim.
    Bullets (and summary lines) are reworded by the AI, one block at a time; a
    reworded line that drops a number or adds a skill is replaced by the
    original. Bullets in each block are then ordered most-relevant first, and
    confirmed skills are added to the Skills section.
    """
    confirmed = [c.strip() for c in (confirmed or []) if c.strip()]
    lines = resume.splitlines()
    idx = _rewritable(lines)
    blocks, cur = [], []
    for i in idx:
        if cur and i != cur[-1] + 1:
            blocks.append(cur); cur = []
        cur.append(i)
    if cur:
        blocks.append(cur)
    base = current.splitlines() if current.strip() and len(current.splitlines()) == len(lines) else lines
    out = list(base)
    for block in blocks:
        src = [_BULLET.sub("", base[i]).strip() for i in block]
        got = _rewrite_lines(model, src, job_description, request, confirmed)
        for i, new in zip(block, got):
            old = lines[i]
            prefix = _BULLET.match(old).group(0) if _BULLET.match(old) else ""
            new = _BULLET.sub("", new)
            out[i] = prefix + new if bullet_ok(new, old, job_description, confirmed) else base[i]
        if all(_BULLET.match(lines[i]) for i in block):
            ranked = sorted((out[i] for i in block),
                            key=lambda t: -_relevance(t, job_description))
            for i, t in zip(block, ranked):
                out[i] = t
    text = "\n".join(out)
    # Posting keywords the resume already proves (e.g. "Collaborated" → collaboration)
    # but that still aren't there word for word go on the Skills line.
    from tracker.ats.keywords import extract_keywords, keywords_in_text
    from tracker.ats.extractor import clean_text
    wanted = extract_keywords(clean_text(job_description))
    _, gaps = keywords_in_text(clean_text(text), wanted)
    proven = [g["keyword"] for g in gaps
              if any(_backed_by_line(g["keyword"], l) for l in lines if not _is_heading(l))]
    proven = [cl._as_written(k, job_description).capitalize() if k.islower() else k for k in proven]
    text = add_skills(text, confirmed)
    return add_skills(text, proven, label="Strengths")


def add_skills(text: str, skills: list[str], label: str = "") -> str:
    """Append confirmed skills to the end of the Skills section (or add one)."""
    have = text.lower()
    skills = [s for s in skills if s.lower() not in have]
    if not skills:
        return text
    lines = text.splitlines()
    start = next((i for i, l in enumerate(lines)
                  if _is_heading(l) and "SKILL" in l.upper()), None)
    if start is None:
        return text.rstrip() + "\n\nSKILLS\n" + ", ".join(skills)
    end = start + 1
    while end < len(lines) and not _is_heading(lines[end]):
        end += 1
    last = max((i for i in range(start + 1, end) if lines[i].strip()), default=None)
    if label:
        lines.insert((last if last is not None else start) + 1, f"{label}: " + ", ".join(skills))
    elif last is None:
        lines.insert(start + 1, ", ".join(skills))
    else:
        lines[last] = lines[last].rstrip() + ", " + ", ".join(skills)
    return "\n".join(lines)


def added_claims(new: str, original: str, job_description: str,
                 confirmed: list[str] | None = None) -> list[str]:
    """Posting skills the rewrite mentions that the original resume doesn't back."""
    backed = original + "\n" + "\n".join(confirmed or [])
    lines = [l for l in original.splitlines() if l.strip()]
    return [t for t in cl.unbacked_skills(new, backed, job_description)
            if not any(_backed_by_line(t, l) for l in lines)]


def to_docx(text: str) -> bytes:
    """Simple Word file: ALL-CAPS or short title-case lines become headings."""
    from docx import Document
    from docx.shared import Pt

    doc = Document()
    doc.styles["Normal"].font.size = Pt(10.5)
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        if s[:1] in "-•*–":
            doc.add_paragraph(s.lstrip("-•*– ").strip(), style="List Bullet")
        elif s.isupper() and len(s) < 40:
            doc.add_heading(s.title(), level=2)
        else:
            doc.add_paragraph(s)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
