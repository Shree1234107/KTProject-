import io
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from tracker import coverletter as cl, db

LETTER = "Jane Doe\njane@x.com\n\nDear Ms. Lee,\n\nFirst para.\n\nSecond para.\n\nSincerely,\nJane Doe"


def test_save_and_delete_letters(tmp_path):
    conn = db.connect(tmp_path / "t.db")
    aid = db.add_application(conn, "Acme", "Intern")
    lid = db.save_letter(conn, aid, "hello")
    assert list(db.load_letters(conn)["id"]) == [lid]
    db.delete_application(conn, aid)
    assert db.load_letters(conn).empty


def test_plain_docx_has_text_and_bold_header():
    doc = Document(io.BytesIO(cl.to_docx(LETTER)))
    texts = [p.text for p in doc.paragraphs if p.text]
    assert texts[0] == "Jane Doe" and "Second para." in texts
    assert doc.paragraphs[0].runs[0].bold
    assert doc.paragraphs[0].alignment == WD_ALIGN_PARAGRAPH.CENTER


def test_styled_docx_copies_template_fonts():
    t = Document()
    h = t.add_paragraph(); r = h.add_run("{Your Name}"); r.font.name = "Garamond"; r.font.size = Pt(20)
    h.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    t.add_paragraph("Dear {Hiring Manager},")
    b = t.add_paragraph(); rb = b.add_run("Body text"); rb.font.name = "Georgia"; rb.font.size = Pt(12)
    t.add_paragraph("Sincerely,")
    t.add_paragraph("{Your Name}")
    buf = io.BytesIO(); t.save(buf)
    out = Document(io.BytesIO(cl.to_docx(LETTER, buf.getvalue())))
    paras = [p for p in out.paragraphs if p.text]
    assert paras[0].text == "Jane Doe" and paras[0].runs[0].font.name == "Garamond"
    assert paras[0].alignment == WD_ALIGN_PARAGRAPH.RIGHT
    body = next(p for p in paras if p.text == "First para.")
    assert body.runs[0].font.name == "Georgia" and body.runs[0].font.size == Pt(12)
    assert [p.text for p in paras][-2:] == ["Sincerely,", "Jane Doe"]


def test_bad_template_falls_back():
    assert cl.to_docx(LETTER, b"not a docx")[:2] == b"PK"
