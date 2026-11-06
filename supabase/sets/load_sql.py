"""Turn an extracted question-bank JSON file into SQL for the choice_* tables.

Usage: python3 -I load_sql.py <questions.json> <set_id> "<Set title>" <position> <outdir>
Writes set_and_questions.sql and keys_1.sql, keys_2.sql, ... (small enough to paste).
"""
import json, sys

src, set_id, title, position, outdir = sys.argv[1:6]
qs = json.load(open(src))

def dq(obj):
    s = json.dumps(obj, ensure_ascii=False)
    assert "$j$" not in s
    return f"$j${s}$j$::jsonb"

rows = [{"id": f"{set_id}-{i:02d}", "pos": i, "qbank_id": q["qbank_id"], "difficulty": q["difficulty"],
         "passage": q["passage"], "stem": q["stem"], "choices": q["choices"]} for i, q in enumerate(qs, 1)]
sql = f"""insert into public.practice_sets (id, title, kind, position) values ('{set_id}', '{title.replace("'", "''")}', 'multiple_choice', {int(position)})
on conflict (id) do update set title = excluded.title;
insert into public.choice_questions (id, set_id, position, qbank_id, difficulty, passage, stem, choices)
select x.id, '{set_id}', x.pos, x.qbank_id, x.difficulty, array(select jsonb_array_elements_text(x.passage)), x.stem, x.choices
from jsonb_to_recordset({dq(rows)}) as x(id text, pos int, qbank_id text, difficulty text, passage jsonb, stem text, choices jsonb)
on conflict (id) do update set position = excluded.position, qbank_id = excluded.qbank_id, difficulty = excluded.difficulty,
  passage = excluded.passage, stem = excluded.stem, choices = excluded.choices;
"""
open(f"{outdir}/set_and_questions.sql", "w").write(sql)

keys = [{"id": f"{set_id}-{i:02d}", "answer": q["answer"], "rationale": q["rationale"]} for i, q in enumerate(qs, 1)]
for n, start in enumerate(range(0, len(keys), 10), 1):
    chunk = keys[start:start + 10]
    open(f"{outdir}/keys_{n}.sql", "w").write(f"""insert into public.choice_keys (question_id, answer, rationale)
select x.id, x.answer, array(select jsonb_array_elements_text(x.rationale))
from jsonb_to_recordset({dq(chunk)}) as x(id text, answer text, rationale jsonb)
on conflict (question_id) do update set answer = excluded.answer, rationale = excluded.rationale;
""")
print("ok")
