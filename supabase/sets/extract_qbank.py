"""Extract College Board Educator Question Bank questions from a PDF.

Usage: python3 -I extract_qbank.py <pdf> <out.json>

One question per page: ID, difficulty, passage, stem, choices A-D, correct answer,
rationale. Lines are grouped into paragraphs by vertical spacing. Two PDF quirks
are handled:
  * hairline "spaces" (width < 1pt) that split words like "par ts" are dropped;
  * fonts are embedded without style names, so a span set in a different font
    from the rest of its paragraph (e.g. a book title) is marked <i>italic</i>.
"""
import html, json, re, sys
from collections import Counter
import pymupdf

HEADINGS = {"Question", "Answer", "Rationale"}
STEM_ANY = re.compile(r"(?<=[.!?”\"] )(Based on the text|Which choice|Which statement|Which question|Which finding|According to the text|What does the text|In the text,|As used in the text|The text most strongly)")
STEM = re.compile(r"^(Which choice|As used in the text|Based on the text|What does)")


def page_lines(page):
    """Visual lines as (top, bottom, [(text, font)]): spans at the same height are
    merged left to right (quote marks and accented letters arrive as separate pieces)."""
    pieces = []
    for b in page.get_text("rawdict")["blocks"]:
        for l in b.get("lines", []):
            for s in l["spans"]:
                chars = [c for c in s["chars"]
                         if not (c["c"] == " " and c["bbox"][2] - c["bbox"][0] < 1.0)]
                if chars:
                    pieces.append((s["bbox"][1], s["bbox"][3], chars[0]["bbox"][0], chars[-1]["bbox"][2],
                                   "".join(c["c"] for c in chars), s["font"]))
    pieces.sort(key=lambda p: (p[0], p[2]))
    lines = []
    for top, bottom, x0, x1, text, font in pieces:
        if lines and abs(top - lines[-1]["top"]) < 2.5:
            lines[-1]["pieces"].append((x0, x1, text, font))
        else:
            lines.append({"top": top, "bottom": bottom, "pieces": [(x0, x1, text, font)]})
    out = []
    for ln in lines:
        ps = sorted(ln["pieces"])
        spans, prev_x1 = [], None
        for x0, x1, text, font in ps:
            if prev_x1 is not None and x0 - prev_x1 > 1.2 and spans and not spans[-1][0].endswith(" ") and not text.startswith(" "):
                spans.append((" ", None))
            spans.append((text, font))
            prev_x1 = x1
        if "".join(t for t, _ in spans).strip():
            out.append((ln["top"], ln["bottom"], spans))
    return out


def paragraphs(lines):
    """Group lines into paragraphs: lines inside a paragraph sit ~6pt apart, paragraphs 14pt+."""
    paras, cur, prev_bottom, prev_alone = [], [], None, False
    for top, bottom, spans in lines:
        text = "".join(t for t, _ in spans).strip()
        alone = text in HEADINGS or text.startswith("Correct Answer") or bool(re.match(r"[A-D]\.\s", text))
        if cur and (top - prev_bottom > 10 or alone or prev_alone):
            paras.append(cur); cur = []
        cur.append(spans)
        prev_bottom, prev_alone = bottom, alone
    if cur:
        paras.append(cur)
    return paras


def to_html(para):
    line_texts = ["".join(t for t, _ in line).strip() for line in para]
    verse = len(para) > 1 and all(len(t) <= 60 for t in line_texts)
    spans = [s for line in para for s in line + [("\n" if verse else " ", None)]]
    weight = Counter()
    for t, f in spans:
        if f and t.strip():
            weight[f] += len(t.strip())
    main = weight.most_common(1)[0][0] if weight else None
    out = ""
    for t, f in spans:
        e = html.escape(t, quote=False)
        # A real italic run has letters; lone quotes, dashes and accented letters
        # just come from a fallback font.
        italic = f and f != main and len(re.findall(r"[A-Za-z]", t)) >= 2
        out += f"<i>{e}</i>" if italic else e
    out = re.sub(r"</i>([\s’'éüñíï]*)<i>", r"\1", out)   # rejoin a title split by an apostrophe or accent
    out = re.sub(r"<i>(\s+)", r"\1<i>", out)
    out = re.sub(r"(\s+)</i>", r"</i>\1", out)
    out = re.sub(r"[ \t]+", " ", out)
    out = re.sub(r" *\n *", "\n", out).strip()
    return out if verse else re.sub(r"\s+", " ", out)


def plain(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


def parse_paragraphs(paras_html, page_text):
    q = {"choices": {}, "passage": [], "rationale": []}
    section = None
    for t in paras_html:
        p = plain(t)
        m = re.match(r"Question ID:\s*(\w+)", p)
        if m:
            q["qbank_id"] = m.group(1); continue
        m = re.match(r"Correct Answer:\s*([A-D])\b", p)
        if m:
            q["answer"] = m.group(1); section = None; continue
        if p in HEADINGS:
            section = p; continue
        if section == "Question":
            q["passage"].append(t)
        elif section == "Answer":
            for part in re.split(r"(?=\b[A-D]\.\s)", t):
                m = re.match(r"\s*([A-D])\.\s*(.*)", part)
                if m:
                    q["choices"][m.group(1)] = m.group(2).strip()
                elif part.strip() and q["choices"]:
                    # a choice that wrapped onto the next page
                    last = sorted(q["choices"])[-1]
                    q["choices"][last] += " " + part.strip()
        elif section == "Rationale":
            q["rationale"].append(t)
    m = re.search(r"\b(Easy|Medium|Hard)\b", page_text)
    q["difficulty"] = m.group(1) if m else None
    # The question stem is the last paragraph of the Question section.
    if q["passage"]:
        last = q["passage"].pop()
        # A stem printed tight under the passage gets merged into its last paragraph; split it off.
        starts = [m.start() for m in STEM_ANY.finditer(last)]
        if starts and starts[-1] > 0:
            q["passage"].append(last[:starts[-1]].strip())
            last = last[starts[-1]:]
        q["stem"] = last
    return q


def main(pdf, out):
    doc = pymupdf.open(pdf)
    # Read every page as one stream, then cut it into questions at each "Question ID".
    groups, texts = [], []
    for i, page in enumerate(doc, 1):
        paras = [to_html(p) for p in paragraphs(page_lines(page))]
        # skip running headers/footers that repeat on continuation pages
        paras = [p for p in paras if plain(p)]
        if paras and re.match(r"Question ID:", plain(paras[0])):
            groups.append({"pages": [i], "paras": []}); texts.append("")
        elif not groups:
            continue
        else:
            groups[-1]["pages"].append(i)
        groups[-1]["paras"] += paras
        texts[-1] += page.get_text()
    qs = []
    for g, text in zip(groups, texts):
        q = parse_paragraphs(g["paras"], text)
        q["page"] = g["pages"][0]
        q["pages"] = g["pages"]
        problems = [k for k in ("qbank_id", "answer", "stem", "difficulty") if not q.get(k)]
        if sorted(q["choices"]) != list("ABCD"):
            problems.append(f"choices={sorted(q['choices'])}")
        if not q["passage"] or not q["rationale"]:
            problems.append("passage/rationale missing")
        if problems:
            print(f"pages {g['pages']}: PROBLEMS {problems}")
        qs.append(q)
    json.dump(qs, open(out, "w"), indent=1, ensure_ascii=False)
    print(f"{len(qs)} questions extracted")


if __name__ == "__main__":
    main(*sys.argv[1:3])
