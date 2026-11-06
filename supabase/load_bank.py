"""Write SQL that loads a parsed bank (from parse_bank.py) as a question set.

Usage: python3 load_bank.py bank.json set-id "Set Title" set-position [chunk-size]
Prints SQL in chunks separated by lines of '-- chunk'. Re-running replaces the set's questions.
"""
import json, sys

bank, set_id, title, pos = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
size = int(sys.argv[5]) if len(sys.argv) > 5 else 5
qs = json.load(open(bank))
s = lambda x: "'" + x.replace("'", "''") + "'"
j = lambda x: s(json.dumps(x, ensure_ascii=False)) + "::jsonb"
arr = lambda xs: "array[" + ",".join(s(x) for x in xs) + "]::text[]"

print(f"insert into public.question_sets (id, title, position) values ({s(set_id)}, {s(title)}, {pos}) "
      f"on conflict (id) do update set title = excluded.title, position = excluded.position;\n"
      f"delete from public.mc_questions where set_id = {s(set_id)};")
for start in range(0, len(qs), size):
    print("-- chunk")
    rows_q, rows_k = [], []
    for n, q in enumerate(qs[start:start + size], start=start + 1):
        rows_q.append(f"({s(q['id'])},{s(set_id)},{n},{s(q['difficulty'])},{j(q['passage'])},{s(q['stem'])},{arr(q['choices'])})")
        rows_k.append(f"({s(q['id'])},{q['correct']},{j(q['rationale'])})")
    print("insert into public.mc_questions (id,set_id,position,difficulty,passage,stem,choices) values\n" + ",\n".join(rows_q) + ";")
    print("insert into public.mc_keys (question_id,correct,rationale) values\n" + ",\n".join(rows_k) + ";")
