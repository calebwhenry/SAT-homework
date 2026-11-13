"""Homework 2: "Subject & Verb (Level 2)".

Students first cross out the extra information, then pick the simple subject and the
simple predicate from the words that are left.

Rule: only information SET OFF by commas, dashes, or parentheses must be crossed out
(appositives, nonessential clauses, interrupters, introductory phrases). Other extra
information (e.g. a prepositional phrase that isn't set off) may be crossed out too,
but it isn't required.

  required - set off by commas, dashes, or parentheses; must be crossed out
  optional - other extra information; fine either way (shown as "you could also...")

Dashes are written spaced ("word — word") so each dash is its own, non-clickable token.
This script finds every phrase in the sentence, checks that each required phrase really
is set off by punctuation, that no phrase touches the subject or verb, and writes SQL.

Run: python3 -I cross_out.py  (writes cross_out.sql next to this file)
"""
import os, re

SET_ID = "cross-out"
SET_TITLE = "Subject & Verb (Level 2)"

Q = [
    dict(sentence="The collection of letters written by soldiers during the Civil War, now preserved in a climate-controlled vault, reveals the daily hardships of camp life.",
         required=["now preserved in a climate-controlled vault,"],
         optional=["of letters written by soldiers during the Civil War,", "of camp life."],
         subject=["collection"], predicate=["reveals"],
         trimmed="The collection reveals the daily hardships.",
         explanation='The commas set off "now preserved in a climate-controlled vault," so that has to go. "Of letters written by soldiers during the Civil War" is extra too, but it is not set off by commas, so crossing it out is optional. Either way, the core is "The collection reveals." "Letters" and "soldiers" are decoys.'),
    dict(sentence="One of the scientists — who studied the coral reefs off the coast of Belize for a decade — has published her findings in a major journal.",
         required=["who studied the coral reefs off the coast of Belize for a decade"],
         optional=["of the scientists", "in a major journal."],
         subject=["One"], predicate=["has", "published"],
         trimmed="One has published her findings.",
         explanation='The dashes set off the "who" clause, so cross it out. "Of the scientists" can go too. That leaves "One has published her findings." "Studied" is a decoy verb: it belongs to the "who" clause.'),
    dict(sentence="Tucked behind the old mill at the edge of town, a small garden planted by volunteers from the high school blooms every spring.",
         required=["Tucked behind the old mill at the edge of town,"],
         optional=["planted by volunteers from the high school", "every spring."],
         subject=["garden"], predicate=["blooms"],
         trimmed="A small garden blooms every spring.",
         explanation='The comma sets off the opening phrase, so cross out "Tucked behind the old mill at the edge of town." "Planted by volunteers from the high school" also describes the garden, but nothing sets it off, so it is optional. "Tucked" and "planted" are participles, not verbs.'),
    dict(sentence="Among the many artifacts recovered from the sunken ship was a bronze compass (engraved with the captain's initials) that still pointed north.",
         required=["(engraved with the captain's initials)"],
         optional=["Among the many artifacts recovered from the sunken ship", "that still pointed north."],
         subject=["compass"], predicate=["was"],
         trimmed="A bronze compass was among the artifacts.",
         explanation='The parentheses set off "engraved with the captain\'s initials," so cross it out. The sentence is inverted; in normal order it reads "A bronze compass was among the many artifacts." "Pointed" belongs to the "that" clause, so the main verb is "was."'),
    dict(sentence="The committee's decision to delay the vote, which several members had openly criticized at the previous meeting, was finally announced on Friday.",
         required=["which several members had openly criticized at the previous meeting,"],
         optional=["to delay the vote,", "finally", "on Friday."],
         subject=["decision"], predicate=["was", "announced"],
         trimmed="The committee's decision was announced.",
         explanation='The commas set off the "which" clause, so cross it out; its verb, "had criticized," is a decoy. "To delay the vote" describes the decision and can go too. The core: "The committee\'s decision was announced."'),
    dict(sentence="My grandmother, a retired pilot who flew cargo planes across the Pacific, still keeps her old flight logs in a trunk.",
         required=["a retired pilot who flew cargo planes across the Pacific,"],
         optional=["in a trunk."],
         subject=["grandmother"], predicate=["keeps"],
         trimmed="My grandmother still keeps her old flight logs.",
         explanation='The commas set off an appositive that renames the grandmother, so cross out "a retired pilot who flew cargo planes across the Pacific." "Flew" is a decoy verb inside it. The core: "My grandmother still keeps her old flight logs."'),
    dict(sentence="The bridge (completed in 1937 after four years of dangerous work) carries more than 100,000 vehicles every day.",
         required=["(completed in 1937 after four years of dangerous work)"],
         optional=["every day."],
         subject=["bridge"], predicate=["carries"],
         trimmed="The bridge carries more than 100,000 vehicles.",
         explanation='Everything in the parentheses is extra, so cross it out. "Completed" looks like a verb but is a participle with no subject. The core: "The bridge carries more than 100,000 vehicles."'),
    dict(sentence="Each of the paintings — several of which had been hidden in a farmhouse during the war — was restored by a team in Florence.",
         required=["several of which had been hidden in a farmhouse during the war"],
         optional=["of the paintings", "by a team in Florence."],
         subject=["Each"], predicate=["was", "restored"],
         trimmed="Each was restored.",
         explanation='The dashes set off "several of which had been hidden in a farmhouse during the war," so cross it out; "had been hidden" is a decoy. "Of the paintings" can go too. "Each" is singular, which is why the verb is "was restored."'),
    dict(sentence="Exhausted after the long climb, the hikers, along with their guide, finally reached the summit at dawn.",
         required=["Exhausted after the long climb,", "along with their guide,"],
         optional=["at dawn."],
         subject=["hikers"], predicate=["reached"],
         trimmed="The hikers finally reached the summit.",
         explanation='Two pieces are set off by commas: the opening phrase "Exhausted after the long climb" and the interrupter "along with their guide." Cross out both. "Along with" does not make a compound subject, so the subject is just "hikers."'),
    dict(sentence="The number of students who signed up for the program, according to the director, has doubled since last year.",
         required=["according to the director,"],
         optional=["of students who signed up for the program,", "since last year."],
         subject=["number"], predicate=["has", "doubled"],
         trimmed="The number has doubled.",
         explanation='The commas set off "according to the director," so cross it out. "Of students who signed up for the program" can go too; it hides the real subject, "number." "Signed" is a decoy verb, and singular "number" takes "has doubled."'),
    dict(sentence="Coral reefs, which cover less than one percent of the ocean floor, support about a quarter of all marine species.",
         required=["which cover less than one percent of the ocean floor,"],
         optional=["of all marine species."],
         subject=["reefs"], predicate=["support"],
         trimmed="Coral reefs support about a quarter.",
         explanation='The commas set off the "which" clause, so cross it out. Its verb, "cover," is a decoy. The core: "Coral reefs support about a quarter of all marine species."'),
    dict(sentence="The author's latest novel — set in a small fishing village in Maine — has been translated into twelve languages.",
         required=["set in a small fishing village in Maine"],
         optional=["into twelve languages."],
         subject=["novel"], predicate=["has", "been", "translated"],
         trimmed="The author's latest novel has been translated.",
         explanation='The dashes set off "set in a small fishing village in Maine," so cross it out. "Set" is a participle here, not the verb. The predicate needs every helping verb: "has been translated."'),
    dict(sentence="Neither the mayor nor her advisers, despite weeks of public pressure, have commented on the report.",
         required=["despite weeks of public pressure,"],
         optional=["on the report."],
         subject=["mayor", "advisers"], predicate=["have", "commented"],
         trimmed="Neither the mayor nor her advisers have commented.",
         explanation='The commas set off "despite weeks of public pressure," so cross it out. "Neither ... nor" joins two subjects, so pick both "mayor" and "advisers." The verb is "have commented."'),
    dict(sentence="In the back of the library, behind a shelf of old atlases, sits a small door that few visitors notice.",
         required=["In the back of the library,", "behind a shelf of old atlases,"],
         optional=["that few visitors notice."],
         subject=["door"], predicate=["sits"],
         trimmed="Sits a small door. (Normal order: A small door sits in the back of the library.)",
         explanation='Both opening phrases are set off by commas, so cross them out. The sentence is inverted: in normal order, "A small door sits in the back of the library." "Notice" belongs to the "that" clause, and "visitors" is its subject, not the sentence\'s.'),
    dict(sentence="The results of the survey (which included more than 3,000 teenagers) suggest that most students sleep fewer than seven hours a night.",
         required=["(which included more than 3,000 teenagers)"],
         optional=["of the survey"],
         subject=["results"], predicate=["suggest"],
         trimmed="The results suggest that most students sleep fewer than seven hours.",
         explanation='The parentheses set off the "which" clause, so cross it out. "Of the survey" can go too. "Sleep" is a decoy: it belongs to the "that" clause after the main verb, "suggest."'),
    dict(sentence="Walking to school every morning, even in the rain, keeps Maya alert during first period.",
         required=["even in the rain,"],
         optional=["during first period."],
         subject=["Walking"], predicate=["keeps"],
         trimmed="Walking to school every morning keeps Maya alert.",
         explanation='The commas set off "even in the rain," so cross it out. The subject is the gerund "Walking": the activity of walking is what keeps Maya alert. "Maya" is the object, not the subject.'),
    dict(sentence="The orchestra's conductor, whose gestures were famously small and precise, rarely raised her voice during rehearsals.",
         required=["whose gestures were famously small and precise,"],
         optional=["during rehearsals."],
         subject=["conductor"], predicate=["raised"],
         trimmed="The orchestra's conductor rarely raised her voice.",
         explanation='The commas set off the "whose" clause, so cross it out. "Gestures" and "were" are its subject and verb, both decoys. The core: "The conductor rarely raised her voice." "Rarely" is an adverb, not part of the verb.'),
    dict(sentence="A flock of geese, honking loudly as it passed over the lake, was visible from miles away.",
         required=["honking loudly as it passed over the lake,"],
         optional=["of geese,", "from miles away."],
         subject=["flock"], predicate=["was"],
         trimmed="A flock was visible.",
         explanation='The commas set off "honking loudly as it passed over the lake," so cross it out. "Of geese" can go too, which shows the subject is "flock," a singular noun, so the verb is "was."'),
    dict(sentence="The new library — which opened in March and already hosts weekly coding classes — has a rooftop garden.",
         required=["which opened in March and already hosts weekly coding classes"],
         optional=[],
         subject=["library"], predicate=["has"],
         trimmed="The new library has a rooftop garden.",
         explanation='The dashes set off the "which" clause, so cross it out. Its verbs, "opened" and "hosts," are decoys. The core: "The new library has a rooftop garden."'),
    dict(sentence="Only one of the twelve contestants, a high school junior from Ohio, correctly spelled the final word.",
         required=["a high school junior from Ohio,"],
         optional=["of the twelve contestants,"],
         subject=["one"], predicate=["spelled"],
         trimmed="Only one correctly spelled the final word.",
         explanation='The commas set off the appositive "a high school junior from Ohio," so cross it out. "Of the twelve contestants" can go too. The subject is "one," not "contestants" or "junior," and the verb is "spelled."'),
]

PUNCT_ONLY = re.compile(r"^[^\w]+$")


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


def is_set_off(words, idx):
    """A required phrase must open at the sentence start or after ',', '—', '(' and close
    with ',', ')' or a following '—' (or end the sentence)."""
    first, last = idx[0], idx[-1]
    opens = first == 0 or words[first - 1].endswith(",") or words[first - 1] == "—" or words[first].startswith("(")
    closes = (words[last].endswith((",", ")", ")."))
              or (last + 1 < len(words) and words[last + 1] == "—")
              or last == len(words) - 1)
    return opens and closes


def build():
    out = []
    assert len(Q) == 20, len(Q)
    for pos, q in enumerate(Q, 1):
        words = q["sentence"].split()
        taken = set()
        req = []
        for p in q["required"]:
            idx = find_phrase(words, p, taken)
            assert is_set_off(words, idx), f"Q{pos}: {p!r} is not set off by commas, dashes, or parentheses"
            req += idx; taken |= set(idx)
        opt = []
        for p in q["optional"]:
            idx = find_phrase(words, p, taken); opt += idx; taken |= set(idx)
        subj = sorted(find_word(words, w) for w in q["subject"])
        pred = sorted(find_word(words, w) for w in q["predicate"])
        assert not (set(subj) | set(pred)) & taken, f"Q{pos}: subject/verb inside a crossed-out phrase"
        assert not any(PUNCT_ONLY.match(words[i]) for i in req + opt), f"Q{pos}: punctuation token in a phrase"
        kept = [w for i, w in enumerate(words) if i not in set(req) and not PUNCT_ONLY.match(w)]
        print(f"Q{pos:2}: S={[words[i] for i in subj]} V={[words[i] for i in pred]}  required-only -> {' '.join(kept)}")
        out.append(dict(id=f"{SET_ID}-{pos:02d}", position=pos, sentence=q["sentence"], words=words,
                        extra=sorted(req), optional=sorted(opt), subject=subj, predicate=pred,
                        trimmed=q["trimmed"], explanation=q["explanation"]))
    return out


def sql(rows):
    def s(x): return "'" + x.replace("'", "''") + "'"
    def arr(a): return "'{" + ",".join(map(str, a)) + "}'::int[]"
    qv = ",\n".join(f"({s(r['id'])},'{SET_ID}',{r['position']},{s(r['sentence'])})" for r in rows)
    kv = ",\n".join(f"({s(r['id'])},{arr(r['extra'])},{arr(r['optional'])},{arr(r['subject'])},{arr(r['predicate'])},{s(r['trimmed'])},{s(r['explanation'])})" for r in rows)
    return f"""update public.practice_sets set title = {s(SET_TITLE)},
  blurb = 'Cross out what''s set off by commas, dashes, or parentheses, then find the subject and verb.'
  where id = '{SET_ID}';
insert into public.trim_questions (id, set_id, position, sentence, words)
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
