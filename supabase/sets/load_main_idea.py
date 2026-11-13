"""Build SQL for the Main Idea set from main_idea.json + main_idea_explanations.py.

Verse (poems, play dialogue) comes out of the PDF as one short paragraph per line;
consecutive short paragraphs are joined with newlines so the page shows them as verse.
Writes main_idea_q1.sql, main_idea_q2.sql ... (questions, 5 per file) and main_idea_keys.sql.

Run: python3 -I load_main_idea.py
"""
import html, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from main_idea_explanations import E  # noqa: E402

SET_ID, TITLE, HW, POS = "main-idea", "Main Idea", 2, 2
BLURB = "Read a short passage and pick the choice that best states its main idea."


def plain(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s))


def join_verse(paras):
    out, run = [], []
    for p in paras:
        if len(plain(p)) <= 60:
            run.append(p)
        else:
            if run: out.append("\n".join(run) if len(run) > 1 else run[0]); run = []
            out.append(p)
    if run:
        out.append("\n".join(run) if len(run) > 1 else run[0])
    return out


def dq(obj):
    s = json.dumps(obj, ensure_ascii=False)
    assert "$j$" not in s
    return f"$j${s}$j$::jsonb"


def main():
    qs = json.load(open(os.path.join(HERE, "main_idea.json")))
    rows, keys = [], []
    for i, q in enumerate(qs, 1):
        e = E[q["qbank_id"]]
        wrong = sorted(e["wrong"])
        assert q["answer"] not in e["wrong"] and wrong == sorted(set("ABCD") - {q["answer"]}), q["qbank_id"]
        qid = f"{SET_ID}-{i:02d}"
        rows.append({"id": qid, "pos": i, "qbank_id": q["qbank_id"], "difficulty": q["difficulty"],
                     "passage": join_verse(q["passage"]), "stem": q["stem"], "choices": q["choices"]})
        keys.append({"id": qid, "answer": q["answer"], "right": e["right"], "wrong": e["wrong"]})
    header = (f"insert into public.practice_sets (id, title, kind, position, homework, blurb) values "
              f"('{SET_ID}', '{TITLE}', 'multiple_choice', {POS}, {HW}, '{BLURB}') "
              f"on conflict (id) do update set title = excluded.title, homework = excluded.homework, "
              f"position = excluded.position, blurb = excluded.blurb;\n")
    for n, start in enumerate(range(0, len(rows), 5), 1):
        chunk = rows[start:start + 5]
        sql = (header if n == 1 else "") + f"""insert into public.choice_questions (id, set_id, position, qbank_id, difficulty, passage, stem, choices)
select x.id, '{SET_ID}', x.pos, x.qbank_id, x.difficulty, array(select jsonb_array_elements_text(x.passage)), x.stem, x.choices
from jsonb_to_recordset({dq(chunk)}) as x(id text, pos int, qbank_id text, difficulty text, passage jsonb, stem text, choices jsonb)
on conflict (id) do update set position = excluded.position, qbank_id = excluded.qbank_id, difficulty = excluded.difficulty,
  passage = excluded.passage, stem = excluded.stem, choices = excluded.choices;
"""
        open(os.path.join(HERE, f"main_idea_q{n}.sql"), "w").write(sql)
    open(os.path.join(HERE, "main_idea_keys.sql"), "w").write(f"""insert into public.choice_keys (question_id, answer, rationale, why_right, why_wrong)
select x.id, x.answer, array[x.right], x.right, x.wrong
from jsonb_to_recordset({dq(keys)}) as x(id text, answer text, "right" text, wrong jsonb)
on conflict (question_id) do update set answer = excluded.answer, rationale = excluded.rationale,
  why_right = excluded.why_right, why_wrong = excluded.why_wrong;
""")
    print(f"{len(rows)} questions; answers:", " ".join(f"{r['qbank_id']}:{k['answer']}" for r, k in zip(rows, keys)))
    print("verse passages:", [r["id"] for r in rows if any("\n" in p for p in r["passage"])])


if __name__ == "__main__":
    main()
