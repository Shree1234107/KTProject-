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


def test_revise_is_a_strict_edit(monkeypatch):
    from tracker import coverletter as cl
    seen = []
    def fake(model, prompt, **kw):
        seen.append(prompt)
        return "word " * (200 if len(seen) == 1 else 40)
    monkeypatch.setattr(cl, "generate_with_ollama", fake)
    letter = "Dear X,\n\n" + "word " * 100 + "\n\nSincerely,\nJ"
    out = cl.revise_letter("m", letter, "make it shorter", RESUME, JD)
    assert len(seen) == 2 and len(out.split()) == 40           # retried when too long
    assert seen[0].startswith("MY REQUEST: make it shorter")
    assert "REMEMBER, MY REQUEST" in seen[0] and "JOB" not in seen[0] and "MY RESUME" not in seen[0]
    seen.clear()
    cl.revise_letter("m", letter, "mention my Excel charts", RESUME, JD)
    assert "MY RESUME (facts only)" in seen[0]


def test_word_family_keywords_are_proven_and_added(monkeypatch):
    jd = "Strong collaboration and communication skills. Python and SQL required for this role."
    res = "SKILLS\nPython\n\nEXPERIENCE\n- Collaborated with the sales team on reports"
    assert rt._backed_by_line("collaboration", "Collaborated with the sales team")
    assert not rt._backed_by_line("communication", "Collaborated with the sales team")
    monkeypatch.setattr(rt.cl, "generate_with_ollama",
                        lambda *a, **k: '{"lines": ["Collaborated with the sales team on reports"]}')
    out = rt.tailor_resume("m", res, jd)
    assert "Relevant skills: Collaboration" in out and "ommunication" not in out
    assert rt.added_claims(out, res, jd) == []


def test_head_noun_backing():
    assert rt._backed_by_line("financial modeling", "Built a model in Excel comparing returns")
    assert rt._backed_by_line("presentations", "Presented findings to 3 professors")
    assert not rt._backed_by_line("account reconciliations", "Counted the cash drawer")
    assert not rt._backed_by_line("quickbooks", "Kept the spreadsheet in Excel")
