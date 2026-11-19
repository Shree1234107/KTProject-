import json

from tracker import resumetailor as rt

JD = "We need Python, SQL, Tableau and Jenkins experience for this analytics intern role."
RESUME = """JANE DOE
jane@x.com

SUMMARY
Student who likes data.

EXPERIENCE
Analyst Intern — Acme (2024)
- Made charts in Excel for the sales team
- Cut report time by 40% using Python and SQL

SKILLS
Python, SQL, Excel"""


def test_bullet_ok_keeps_numbers_and_blocks_new_skills():
    old = "Cut report time by 40% using Python"
    assert rt.bullet_ok("Reduced report time by 40% with Python", old, JD, [])
    assert not rt.bullet_ok("Reduced report time with Python", old, JD, [])        # lost 40%
    assert not rt.bullet_ok("Cut report time 40% using Python and Tableau", old, JD, [])
    assert rt.bullet_ok("Cut report time 40% using Python and Tableau", old, JD, ["Tableau"])
    assert not rt.bullet_ok("Led a 40% cut in report time using Python", old, JD, [])  # inflated


def test_add_skills_appends_to_skills_section_once():
    out = rt.add_skills(RESUME, ["Tableau", "python"])
    assert out.splitlines()[-1] == "Python, SQL, Excel, Tableau"
    assert rt.add_skills("A\nB", ["Git"]).endswith("SKILLS\nGit")


def test_tailor_keeps_structure_and_rejects_bad_lines(monkeypatch):
    def fake(model, prompt, **kw):
        n = json.loads(prompt.split("LINES:\n")[1].split("\n\nJOB")[0])
        if len(n) == 1:
            return json.dumps({"lines": ["Data-focused student."]})
        return json.dumps({"lines": ["Built Excel charts for the sales team using Tableau",  # new skill
                                     "Reduced report time by 40% using Python and SQL"]})
    monkeypatch.setattr(rt.cl, "generate_with_ollama", fake)
    out = rt.tailor_resume("m", RESUME, JD, confirmed=["Jenkins"]).splitlines()
    assert out[0] == "JANE DOE" and "Analyst Intern — Acme (2024)" in out
    assert "Data-focused student." in out
    assert "- Made charts in Excel for the sales team" in out                 # bad rewrite rejected
    assert out.index("- Reduced report time by 40% using Python and SQL") < out.index(
        "- Made charts in Excel for the sales team")                         # most relevant first
    assert out[-1].endswith("Jenkins")


def test_tailor_wrong_count_keeps_original(monkeypatch):
    monkeypatch.setattr(rt.cl, "generate_with_ollama", lambda *a, **k: '{"lines": ["x"]}')
    out = rt.tailor_resume("m", RESUME, JD)
    assert "- Made charts in Excel for the sales team" in out


def test_style_rules_and_voice():
    from tracker import coverletter as cl
    r = cl.style_rules(RESUME, JD, voice="short sentences")
    assert "Python" in r and "MY VOICE" in r and "passionate" in r
    assert "MY VOICE" not in cl.style_rules(RESUME, JD)
