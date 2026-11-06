"""Turn a College Board Educator Question Bank PDF into JSON for the site.

Usage: python3 parse_bank.py bank.pdf out.json

Reads characters with their positions and fonts (PyMuPDF), so curly quotes,
apostrophes and italic titles stay where they belong. Italic text is wrapped
in <i>...</i>; everything else is plain text.
"""
import collections
import json
import re
import sys

import pymupdf

LABELS = {"Question", "Answer", "Rationale", "Assessment", "Test", "Domain", "Skill", "Difficulty"}
WORD_GAP = 1.0      # points; letter gaps are ~0, word gaps ~2.2
PARA_GAP = 20.0     # points between line centers that starts a new paragraph


def page_lines(page):
    """Return [(y, text_with_italics)] for one page, top to bottom."""
    chars, span_text = [], collections.defaultdict(str)
    for b in page.get_text("rawdict")["blocks"]:
        for l in b.get("lines", []):
            for s in l["spans"]:
                txt = "".join(c["c"] for c in s["chars"])
                span_text[s["font"]] += txt + "\n"
                for c in s["chars"]:
                    if c["c"].strip():
                        x0, y0, x1, y1 = c["bbox"]
                        chars.append(((y0 + y1) / 2, x0, x1, c["c"], s["font"]))

    # Body font has the most letters; italic fonts carry runs of letters but no labels.
    letters = collections.Counter()
    for font, txt in span_text.items():
        letters[font] = sum(ch.isalpha() for ch in txt)
    body = letters.most_common(1)[0][0] if letters else None
    italic = set()
    for font, txt in span_text.items():
        spans = [t.strip() for t in txt.split("\n") if t.strip()]
        if font == body or any(t in LABELS or t.startswith(("Question ID", "Correct Answer")) for t in spans):
            continue
        if any(re.search(r"[A-Za-z]{2}", t) for t in spans):
            italic.add(font)

    # Group characters into lines by vertical center (quote glyphs sit ~1pt off).
    chars.sort()
    rows = []
    for ch in chars:
        if rows and abs(ch[0] - rows[-1][0]) <= 3:
            rows[-1][1].append(ch)
        else:
            rows.append([ch[0], [ch]])

    out = []
    for y, cs in rows:
        cs.sort(key=lambda c: c[1])
        text, in_i, prev = "", False, None
        for _, x0, x1, c, font in cs:
            if prev is not None and x0 - prev > WORD_GAP:
                if prev is not None and x0 - prev > 60:   # table columns in the header
                    text += " | "
                else:
                    text += " "
            want_i = font in italic
            if want_i != in_i:
                if want_i:
                    text += "<i>"
                else:
                    # keep a trailing space outside the tag
                    sp = text.endswith(" ")
                    text = text.rstrip(" ") + "</i>" + (" " if sp else "")
                in_i = want_i
            text += c
            prev = x1
        if in_i:
            text += "</i>"
        out.append((y, text))
    return out


def paragraphs(lines):
    paras, cur, last_y = [], [], None
    for y, t in lines:
        if cur and last_y is not None and y - last_y > PARA_GAP:
            paras.append(" ".join(cur))
            cur = []
        cur.append(t)
        last_y = y
    if cur:
        paras.append(" ".join(cur))
    # tidy: "</i> <i>" joins, spaces before punctuation the PDF spaced oddly
    # join italic runs split by a space or a lone punctuation glyph (Giovanni’s Room)
    return [re.sub(r"</i>(\s*|[’'\u2019]\s*)<i>", r"\1", p) for p in paras]


def parse(pdf_path):
    doc = pymupdf.open(pdf_path)
    # Flatten all pages into one stream of (page, y, text) lines.
    stream = []
    for pno, page in enumerate(doc):
        for y, t in page_lines(page):
            stream.append((pno * 10000 + y, t))

    # Split into questions.
    questions, cur = [], None
    for y, t in stream:
        m = re.match(r"Question ID: ([0-9a-f]+)", t)
        if m:
            cur = {"id": m.group(1), "lines": []}
            questions.append(cur)
        elif cur:
            cur["lines"].append((y, t))

    out = []
    for q in questions:
        lines = q["lines"]
        texts = [t for _, t in lines]
        header = next(t for t in texts if "|" in t and re.search(r"\b(Easy|Medium|Hard)\b", t))
        difficulty = re.search(r"\b(Easy|Medium|Hard)\b", header).group(1)
        skill = header.split("|")[3].strip() if header.count("|") >= 4 else ""

        def index_of(label):
            return next(i for i, t in enumerate(texts) if t == label)

        i_q, i_a = index_of("Question"), index_of("Answer")
        i_c = next(i for i, t in enumerate(texts) if t.startswith("Correct Answer:"))
        i_r = index_of("Rationale")

        qparas = paragraphs(lines[i_q + 1:i_a])
        stem, passage = qparas[-1], qparas[:-1]
        choices = {}
        for t in texts[i_a + 1:i_c]:
            m = re.match(r"^([A-D])\.\s*(.*)$", t)
            if m:
                choices[m.group(1)] = m.group(2)
            elif choices:
                choices[list(choices)[-1]] += " " + t
        correct = re.match(r"Correct Answer:\s*([A-D])", texts[i_c]).group(1)
        rationale = [p for p in paragraphs(lines[i_r + 1:]) if not p.startswith("Question Difficulty:")]
        out.append({
            "id": q["id"], "skill": skill, "difficulty": difficulty,
            "passage": passage, "stem": stem,
            "choices": [choices[k] for k in "ABCD"],
            "correct": "ABCD".index(correct),
            "rationale": rationale,
        })
    return out


if __name__ == "__main__":
    data = parse(sys.argv[1])
    json.dump(data, open(sys.argv[2], "w"), indent=1, ensure_ascii=False)
    print(len(data), "questions:", dict(collections.Counter(q["difficulty"] for q in data)))
