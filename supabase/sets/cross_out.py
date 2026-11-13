"""Homework 2: "Cross out, then find" questions.

Students first cross out the extra information (prepositional phrases, interrupters,
participial and infinitive phrases, side clauses), then pick the simple subject and
the simple predicate from the words that are left.

Each question names phrases, not indices; this script finds them in the sentence,
checks they don't overlap the subject or verb, and prints SQL for Supabase.

  extra    - must be crossed out (the material that hides the subject or verb)
  optional - fine either way (e.g. a prepositional phrase after the verb)

Run: python3 -I cross_out.py  (writes cross_out.sql next to this file)
"""
import json, os, re

SET_ID = "cross-out"

Q = [
    dict(sentence="The collection of letters written by soldiers during the Civil War, now preserved in a climate-controlled vault, reveals the daily hardships of camp life.",
         extra=["of letters written by soldiers during the Civil War,", "now preserved in a climate-controlled vault,"],
         optional=["of camp life."],
         subject=["collection"], predicate=["reveals"],
         trimmed="The collection reveals the daily hardships.",
         explanation='"Of letters written by soldiers during the Civil War" is a prepositional phrase, and "now preserved in a climate-controlled vault" is an interrupter. With both gone, the sentence is "The collection reveals the daily hardships." "Letters" and "soldiers" are decoys, and "written" and "preserved" are participles, not verbs.'),
    dict(sentence="One of the scientists who studied the coral reefs off the coast of Belize has published her findings in a major journal.",
         extra=["of the scientists who studied the coral reefs off the coast of Belize"],
         optional=["in a major journal."],
         subject=["One"], predicate=["has", "published"],
         trimmed="One has published her findings.",
         explanation='Everything from "of the scientists" through "Belize" describes "One": a prepositional phrase with a "who" clause inside it. Cross it out and you get "One has published her findings." "Studied" is the decoy verb; it belongs to the "who" clause.'),
    dict(sentence="Tucked behind the old mill at the edge of town, a small garden planted by volunteers from the high school blooms every spring.",
         extra=["Tucked behind the old mill at the edge of town,", "planted by volunteers from the high school"],
         optional=["every spring."],
         subject=["garden"], predicate=["blooms"],
         trimmed="A small garden blooms every spring.",
         explanation='The opening phrase ("Tucked behind...") and "planted by volunteers from the high school" are participial phrases that describe the garden. Remove them: "A small garden blooms every spring." "Tucked" and "planted" look like verbs but have no subject of their own.'),
    dict(sentence="Among the many artifacts recovered from the sunken ship was a bronze compass engraved with the captain's initials.",
         extra=["Among the many artifacts recovered from the sunken ship", "engraved with the captain's initials."],
         optional=[],
         subject=["compass"], predicate=["was"],
         trimmed="Was a bronze compass. (Normal order: A bronze compass was among the artifacts.)",
         explanation='This sentence is inverted: the verb comes before the subject. Cross out the opening prepositional phrase and "engraved with the captain\'s initials," and you are left with "was a bronze compass." Flip it to normal order: "A bronze compass was among the artifacts." "Artifacts" is a decoy because it sits inside "among the many artifacts."'),
    dict(sentence="The committee's decision to delay the vote, which several members had openly criticized at the previous meeting, was finally announced on Friday.",
         extra=["to delay the vote,", "which several members had openly criticized at the previous meeting,"],
         optional=["finally", "on Friday."],
         subject=["decision"], predicate=["was", "announced"],
         trimmed="The committee's decision was announced.",
         explanation='"To delay the vote" is an infinitive phrase describing the decision, and the "which" clause is an interrupter with its own verb ("had criticized"). Remove both: "The committee\'s decision was announced." The predicate is "was announced"; "finally" is an adverb.'),
]


def find_phrase(words, phrase, taken):
    target = phrase.split()
    for i in range(len(words) - len(target) + 1):
        if words[i:i + len(target)] == target and not set(range(i, i + len(target))) & taken:
            return list(range(i, i + len(target)))
    raise SystemExit(f"phrase not found: {phrase!r}")


def find_word(words, w):
    hits = [i for i, x in enumerate(words) if re.sub(r"[^\w'’-]", "", x) == w]
    if len(hits) != 1:
        raise SystemExit(f"word {w!r} found {len(hits)} times")
    return hits[0]


def build():
    out = []
    for pos, q in enumerate(Q, 1):
        words = q["sentence"].split()
        taken = set()
        extra = []
        for p in q["extra"]:
            idx = find_phrase(words, p, taken); extra += idx; taken |= set(idx)
        optional = []
        for p in q["optional"]:
            idx = find_phrase(words, p, taken); optional += idx; taken |= set(idx)
        subj = sorted(find_word(words, w) for w in q["subject"])
        pred = sorted(find_word(words, w) for w in q["predicate"])
        core = set(subj) | set(pred)
        assert not core & taken, f"Q{pos}: subject/verb inside a crossed-out phrase"
        kept = [w for i, w in enumerate(words) if i not in set(extra) | set(optional)]
        print(f"Q{pos}: S={[words[i] for i in subj]} V={[words[i] for i in pred]}")
        print(f"     kept after crossing out: {' '.join(kept)}")
        out.append(dict(id=f"{SET_ID}-{pos:02d}", position=pos, sentence=q["sentence"], words=words,
                        extra=sorted(extra), optional=sorted(optional), subject=subj, predicate=pred,
                        trimmed=q["trimmed"], explanation=q["explanation"]))
    return out


def sql(rows):
    def s(x): return "'" + x.replace("'", "''") + "'"
    def arr(a): return "'{" + ",".join(map(str, a)) + "}'::int[]"
    qv = ",\n".join(f"({s(r['id'])},'{SET_ID}',{r['position']},{s(r['sentence'])})" for r in rows)
    kv = ",\n".join(f"({s(r['id'])},{arr(r['extra'])},{arr(r['optional'])},{arr(r['subject'])},{arr(r['predicate'])},{s(r['trimmed'])},{s(r['explanation'])})" for r in rows)
    return f"""insert into public.trim_questions (id, set_id, position, sentence, words)
select v.id, v.set_id, v.pos, v.t, string_to_array(v.t, ' ') from (values
{qv}
) v(id, set_id, pos, t)
on conflict (id) do update set position = excluded.position, sentence = excluded.sentence, words = excluded.words;
insert into public.trim_keys (question_id, extra_idx, optional_idx, subject_idx, predicate_idx, trimmed, explanation) values
{kv}
on conflict (question_id) do update set extra_idx = excluded.extra_idx, optional_idx = excluded.optional_idx,
  subject_idx = excluded.subject_idx, predicate_idx = excluded.predicate_idx, trimmed = excluded.trimmed, explanation = excluded.explanation;
"""


if __name__ == "__main__":
    rows = build()
    here = os.path.dirname(os.path.abspath(__file__))
    open(os.path.join(here, "cross_out.sql"), "w").write(sql(rows))
    print(f"{len(rows)} questions OK; wrote cross_out.sql")
