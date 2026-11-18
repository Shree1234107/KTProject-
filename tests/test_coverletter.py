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
    payload = {"models": [{"name": "small:4b", "size": 3e9},
                          {"name": "big:cloud", "remote_model": "big"}]}
    monkeypatch.setattr(cl.urllib.request, "urlopen",
                        lambda *a, **k: _Resp(json.dumps(payload).encode()))
    ms = cl.ollama_models()
    assert ms[0] == {"name": "small:4b", "cloud": False, "size_gb": 3.0}
    assert ms[1]["cloud"] is True


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
