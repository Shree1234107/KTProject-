"""Cover letter: template fill, prompt, Ollama handling, PDF."""
import datetime as dt
import io
import json
import urllib.error

import pytest

from tracker import coverletter as cl


def test_fill_template_replaces_known_placeholders_only():
    f = cl.fields_for("Acme", "Data Intern", "", ["python", "sql"], dt.date(2026, 11, 18))
    out = cl.fill_template("{date}\nDear {hiring_manager}, {role} at {company}. {skills}. {other}", f)
    assert out == "November 18, 2026\nDear Hiring Manager, Data Intern at Acme. python and sql. {other}"


def test_shared_skills_uses_resume_and_jd():
    jd = "We need Python and SQL. Python daily. Kubernetes is a plus."
    resume = "Built ETL pipelines in Python and SQL."
    skills = cl.shared_skills(resume, jd)
    assert "Python" in skills and "SQL" in skills
    assert "Kubernetes" not in skills
    assert cl.shared_skills("", jd) == []


def test_prompt_contains_inputs_and_guardrails():
    p = cl.build_prompt("RESUME TEXT", "JD TEXT", "TEMPLATE TEXT", "Acme", "Intern")
    for bit in ("RESUME TEXT", "JD TEXT", "TEMPLATE TEXT", "Acme", "Never invent"):
        assert bit in p


def test_clean_model_output_strips_thinking_and_bold():
    assert cl.clean_model_output("<think>hmm</think>\n**Dear** team") == "Dear team"


def test_pdf_is_valid_and_handles_smart_quotes():
    data = cl.to_pdf("Dear “Team” — it’s me.\n\nThanks", "x")
    assert data[:5] == b"%PDF-"
    assert cl.file_name("Acme Co.", "Data Intern") == "Cover_Letter_Acme_Co_Data_Intern.pdf"


def test_ollama_models_empty_when_not_running(monkeypatch):
    def boom(*a, **k):
        raise urllib.error.URLError("refused")
    monkeypatch.setattr(cl.urllib.request, "urlopen", boom)
    assert cl.ollama_models() == []
    with pytest.raises(RuntimeError, match="Ollama app"):
        cl.generate_with_ollama("m", "p")


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_ollama_models_marks_cloud(monkeypatch):
    payload = {"models": [{"name": "big:cloud", "remote_model": "big"},
                          {"name": "huge:27b", "size": 18e9},
                          {"name": "small:4b", "size": 3e9}]}
    monkeypatch.setattr(cl.urllib.request, "urlopen",
                        lambda *a, **k: _Resp(json.dumps(payload).encode()))
    ms = cl.ollama_models()
    assert ms[0] == {"name": "small:4b", "cloud": False, "size_gb": 3.0}
    assert [m["name"] for m in ms] == ["small:4b", "huge:27b", "big:cloud"]
    assert ms[2]["cloud"] is True


def test_generate_surfaces_model_error(monkeypatch):
    monkeypatch.setattr(cl.urllib.request, "urlopen",
                        lambda *a, **k: _Resp(json.dumps({"error": "out of memory"}).encode()))
    with pytest.raises(RuntimeError, match="out of memory"):
        cl.generate_with_ollama("m", "p")


def test_memory_error_is_explained(monkeypatch):
    err = {"error": "model requires 16.9 GiB but only 10.2 GiB are available"}
    monkeypatch.setattr(cl.urllib.request, "urlopen", lambda *a, **k: _Resp(json.dumps(err).encode()))
    with pytest.raises(RuntimeError, match="too big"):
        cl.generate_with_ollama("m", "p")


def test_unbacked_skills_flags_claims_not_on_resume():
    jd = "Build pipelines with Python and Airflow. Work with Spark. Kubernetes a plus."
    resume = "Built pipelines in Python and Airflow."
    letter = "I know Python and Airflow, and I'm familiar with Spark."
    assert cl.unbacked_skills(letter, resume, jd) == ["Spark"]
    assert cl.unbacked_skills("I know Python.", resume, jd) == []


def _docx(paragraphs):
    import zipfile as zf
    w = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    body = "".join(f'<w:p><w:r><w:t xml:space="preserve">{p}</w:t></w:r></w:p>' for p in paragraphs)
    xml = f'<?xml version="1.0"?><w:document xmlns:w="{w}"><w:body>{body}</w:body></w:document>'
    buf = io.BytesIO()
    with zf.ZipFile(buf, "w") as z:
        z.writestr("word/document.xml", xml)
    return buf.getvalue()


def test_template_from_docx_keeps_paragraphs_and_placeholders():
    data = _docx(["{date}", "", "Dear {hiring_manager},", "", "", "", "I want the {role} job."])
    text = cl.template_from_file("My Template.DOCX", data)
    assert text == "{date}\n\nDear {hiring_manager},\n\nI want the {role} job."
    assert cl.placeholders_in(text) == ["{role}", "{hiring_manager}", "{date}"]


def test_template_from_txt_and_pdf():
    assert cl.template_from_file("t.txt", "﻿Hello {company}\r\nBye".encode()) == "Hello {company}\nBye"
    pdf = cl.to_pdf("Dear {hiring_manager},\n\nI like {company}.")
    text = cl.template_from_file("t.pdf", pdf)
    assert "{hiring_manager}" in text and "{company}" in text


def test_template_from_file_rejects_bad_input():
    with pytest.raises(ValueError, match=".docx"):
        cl.template_from_file("old.doc", b"x")
    with pytest.raises(ValueError, match="Word file"):
        cl.template_from_file("broken.docx", b"not a zip")
    with pytest.raises(ValueError, match="no text"):
        cl.template_from_file("empty.txt", b"   \n ")


def test_guess_company_role_parses_json(monkeypatch):
    reply = {"response": json.dumps({"company": " Acme  Corp ", "role": "Data Intern"})}
    monkeypatch.setattr(cl.urllib.request, "urlopen", lambda *a, **k: _Resp(json.dumps(reply).encode()))
    assert cl.guess_company_role("m", "posting") == ("Acme Corp", "Data Intern")


def test_guess_company_role_blank_on_failure(monkeypatch):
    monkeypatch.setattr(cl.urllib.request, "urlopen", lambda *a, **k: _Resp(b'{"response": "not json"}'))
    assert cl.guess_company_role("m", "posting") == ("", "")


_LEEDS = """MY COVER LETTER TEMPLATE 2025
Boulder, CO (remove if outside CO)  first.last@colorado.edu  303-333-3333  www.linkedin.com/in/name

Dear Hiring Manager/Hiring Committee (use a name if you have one),

Paragraph one guidance.

Paragraph two guidance.

Paragraph three guidance.

Sincerely,

First Last
Bachelor of Science in ____, Class of 202X"""

_RES = "Pat Doe\nDenver, CO | pat.doe@colorado.edu | (720) 555-0101 | linkedin.com/in/pat-doe\nB.S. Finance, 2028"


def test_split_template_finds_parts():
    p = cl.split_template(_LEEDS)
    assert p["header"][0].startswith("MY COVER LETTER")
    assert p["greeting"].startswith("Dear")
    assert p["paragraphs"] == 3
    assert p["closing"][0] == "Sincerely," and p["closing"][-1].startswith("Bachelor")
    assert cl.split_template("No greeting here.\n\nThanks") is None


def test_greeting_and_notes():
    assert cl.greeting_line("Dear Hiring Manager/Hiring Committee (use a name),") == "Dear Hiring Manager,"
    assert cl.greeting_line("Dear X,", "Ms. Rivera") == "Dear Ms. Rivera,"
    assert cl.strip_notes("Call (303) 555-0101 (only if local)") == "Call (303) 555-0101"


def test_real_contacts_replace_samples():
    line = "Boulder, CO  first.last@colorado.edu  303-333-3333  www.linkedin.com/in/name"
    out = cl.use_real_contacts([line], _RES)[0]
    assert "pat.doe@colorado.edu" in out and "(720) 555-0101" in out
    assert "linkedin.com/in/pat-doe" in out and "first.last" not in out


def test_template_letter_keeps_structure(monkeypatch):
    calls = []

    def fake(model, prompt, **kw):
        calls.append(kw.get("json_mode", False))
        if kw.get("json_mode"):
            lines = json.loads(prompt.split("LINES:\n")[1].split("\n\nMY RESUME")[0])
            return json.dumps({"lines": lines})       # model changes nothing
        return "Para one.\n\nPara two.\n\nPara three."
    monkeypatch.setattr(cl, "generate_with_ollama", fake)
    out = cl.write_letter_from_template("m", _RES, "JD", _LEEDS, "Acme", "Intern")
    lines = out.split("\n")
    assert lines[0] == "Pat Doe"                       # title line -> resume name
    assert "pat.doe@colorado.edu" in lines[1] and "remove if" not in lines[1]
    assert "Dear Hiring Manager," in out
    assert "Para one.\n\nPara two.\n\nPara three.\n\nSincerely,\n\nFirst Last" in out


def test_pdf_is_left_aligned_not_justified():
    import re as _re
    import zlib
    pdf = cl.to_pdf("Name\nemail\n\nDear X,\n\n" + "word " * 120 + "\n\nSincerely,\nName")
    streams = _re.findall(rb"stream\r?\n(.*?)\r?\nendstream", pdf, _re.S)
    text = b"".join(zlib.decompress(s) if s[:1] == b"x" else s for s in streams)
    assert b" Tw" not in text   # Tw = word spacing, only used for justified text
