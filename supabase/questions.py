"""Question bank for the simple subject / simple predicate practice.

Each entry: (id, set_name, sentence, subject_words, predicate_words, explanation, decoys)
subject_words / predicate_words name the key words in the sentence. A word that
appears more than once is written "word#2" for its second occurrence.

Run `python3 -I questions.py` to verify every key word is found and to write
seed.sql (the INSERT statements loaded into Supabase).
"""

import json
import re
import sys

Q = [
    # ---------------- Warm-up ----------------
    ("W1", "Warm-up", "The singer, along with her band, was rehearsing.",
     ["singer"], ["was", "rehearsing"],
     "\"Along with her band\" is an interrupter, not part of the subject, so the subject is \"singer.\" The helping verb \"was\" and the main verb \"rehearsing\" together form the predicate.",
     "band"),
    ("W2", "Warm-up", "Neither the coach nor the players were told about the change.",
     ["coach", "players"], ["were", "told"],
     "Neither...nor joins two subjects, so both \"coach\" and \"players\" count. \"Were told\" is the verb phrase; \"about the change\" is a prepositional phrase.",
     "change"),
    ("W3", "Warm-up", "Rarely do we see such talent.",
     ["we"], ["do", "see"],
     "Put it in normal order: \"We do rarely see such talent.\" The subject is \"we,\" and the predicate is the split verb \"do ... see.\"",
     "talent"),
    ("W4", "Warm-up", "Only after the storm did the power return.",
     ["power"], ["did", "return"],
     "Normal order: \"The power did return only after the storm.\" \"Storm\" is inside a prepositional phrase, so it can't be the subject.",
     "storm"),
    ("W5", "Warm-up", "Off the coast of Maine lie hundreds of small islands.",
     ["hundreds"], ["lie"],
     "Normal order: \"Hundreds of small islands lie off the coast of Maine.\" \"Islands\" sits inside \"of small islands,\" so the subject is \"hundreds.\"",
     "coast, Maine, islands"),

    # ---------------- Challenge ----------------
    ("C1", "Challenge", "The collection of rare manuscripts, letters, and maps that the historians spent years cataloging is now housed in the university library.",
     ["collection"], ["is", "housed"],
     "Ask what \"is housed\": the collection. \"Manuscripts, letters, and maps\" sit inside an \"of\" phrase, and \"spent\" belongs to the clause \"that the historians spent...\". \"Now\" is an adverb.",
     "manuscripts, maps, historians, spent, cataloging"),
    ("C2", "Challenge", "Exhausted from hours of rehearsing the difficult passages that the conductor had added, the violinists in the second row finally lowered their instruments.",
     ["violinists"], ["lowered"],
     "The opening phrase (\"Exhausted...\") describes the violinists and has no verb of its own. \"Had added\" belongs to the \"that\" clause, and \"row\" is inside \"in the second row.\"",
     "Exhausted, rehearsing, conductor, had added, row"),
    ("C3", "Challenge", "The decision by the board members, several of whom had opposed the plan from the beginning, to postpone the expansion surprised investors.",
     ["decision"], ["surprised"],
     "The core noun is \"decision\"; \"by the board members\" and the \"several of whom\" clause interrupt it. \"To postpone\" is an infinitive describing the decision, not the main verb.",
     "members, several, had opposed, to postpone"),
    ("C4", "Challenge", "Along the old railroad tracks, which had been abandoned decades earlier by a company that went bankrupt, run a narrow footpath and a row of crumbling stone walls.",
     ["footpath", "row"], ["run"],
     "Normal order: \"A footpath and a row ... run along the tracks.\" \"Had been abandoned\" and \"went\" belong to side clauses, and \"walls\" is inside \"of crumbling stone walls.\"",
     "tracks, had been abandoned, company, went, walls"),
    ("C5", "Challenge", "Each of the paintings displayed in the gallery's newest wing, including several portraits attributed to Rembrandt's students, was carefully restored.",
     ["Each"], ["was", "restored"],
     "\"Each\" is the subject, which is why the verb is singular \"was.\" \"Paintings\" is inside \"of the paintings,\" and \"displayed\" and \"attributed\" are participles.",
     "paintings, displayed, portraits, attributed"),
    ("C6", "Challenge", "The ability of migrating birds to navigate thousands of miles using the Earth's magnetic field continues to fascinate researchers.",
     ["ability"], ["continues"],
     "Ask what continues: the ability. \"Migrating\" and \"using\" are participles, \"to navigate\" describes the ability, and \"to fascinate\" is an infinitive acting as the object of \"continues.\"",
     "birds, migrating, to navigate, using, to fascinate"),
    ("C7", "Challenge", "Not one of the forty applicants who interviewed for the position, despite their impressive résumés, was offered the job.",
     ["one"], ["was", "offered"],
     "\"Not one\" is the subject, so the verb is singular. \"Applicants\" is inside \"of the forty applicants,\" and \"interviewed\" belongs to the \"who\" clause.",
     "applicants, interviewed, résumés"),
    ("C8", "Challenge", "Having been warned repeatedly about the icy roads, the drivers making the overnight delivery to the mountain towns nonetheless chose the shorter route.",
     ["drivers"], ["chose"],
     "\"Having been warned\" is a participial phrase with no subject. \"Making\" describes the drivers, and \"nonetheless\" is an adverb.",
     "Having been warned, making, towns"),
    ("C9", "Challenge", "The scientist whose research on coral reefs earned her international recognition, along with two graduate students from her lab, is traveling to Australia next month.",
     ["scientist"], ["is", "traveling"],
     "The \"whose\" clause has its own verb (\"earned\"), and \"along with two graduate students\" is an interrupter. The singular \"is traveling\" agrees with \"scientist.\"",
     "research, earned, students"),
    ("C10", "Challenge", "Beneath layers of volcanic ash that had accumulated over centuries lay the remains of an entire Roman village.",
     ["remains"], ["lay"],
     "Normal order: \"The remains of a village lay beneath layers of ash.\" \"Had accumulated\" belongs to the \"that\" clause.",
     "layers, ash, had accumulated, village"),
    ("C11", "Challenge", "The number of students who say that they feel overwhelmed by homework has risen sharply.",
     ["number"], ["has", "risen"],
     "\"The number\" is singular, so it takes \"has risen.\" \"Students,\" \"say,\" and \"feel\" belong to the phrase and clauses that describe it.",
     "students, say, feel, overwhelmed"),
    ("C12", "Challenge", "Swimming in the frigid waters off the coast of Maine, which locals insist is refreshing even in early June, requires considerable courage.",
     ["Swimming"], ["requires"],
     "\"Swimming in the frigid waters\" is a gerund phrase acting as the subject. \"Insist\" and \"is\" belong to the \"which\" clause.",
     "waters, locals, insist, is"),
    ("C13", "Challenge", "Neither the lead actor nor the understudies, all of whom had memorized the revised script, were ready for the director's sudden changes.",
     ["actor", "understudies"], ["were"],
     "Neither...nor joins two subjects. \"Had memorized\" belongs to the \"all of whom\" clause, and \"were\" is a linking verb (\"ready\" describes the subjects).",
     "all, had memorized"),
    ("C14", "Challenge", "The painting hanging above the fireplace in the study where my grandfather wrote his novels belonged to his mother.",
     ["painting"], ["belonged"],
     "\"Hanging\" is a participle describing the painting. \"Wrote\" belongs to the \"where\" clause.",
     "hanging, study, grandfather, wrote"),
    ("C15", "Challenge", "Only by carefully reviewing the data collected from hundreds of patients over a decade could the researchers confirm their hypothesis.",
     ["researchers"], ["could", "confirm"],
     "Normal order: \"The researchers could confirm their hypothesis only by reviewing...\" \"Reviewing\" is a gerund and \"collected\" is a participle.",
     "reviewing, data, collected, patients"),
    ("C16", "Challenge", "The list of items that the hikers forgot to pack, which included a map, a compass, and extra water, was alarmingly long.",
     ["list"], ["was"],
     "\"Items\" is inside \"of items.\" \"Forgot\" and \"included\" belong to side clauses, and \"to pack\" is an infinitive.",
     "items, hikers, forgot, to pack, included"),
    ("C17", "Challenge", "Tired of waiting for the delayed train, a few of the commuters standing on the crowded platform decided to walk.",
     ["few"], ["decided"],
     "\"Few\" is the subject; \"commuters\" is inside \"of the commuters.\" \"Tired,\" \"waiting,\" and \"standing\" are verbals, and \"to walk\" is the object of \"decided.\"",
     "Tired, waiting, commuters, standing, to walk"),
    ("C18", "Challenge", "The effects of the new policy, which critics claimed would harm small businesses, have been surprisingly modest.",
     ["effects"], ["have", "been"],
     "Plural \"effects\" takes \"have been.\" \"Claimed\" and \"would harm\" belong to the \"which\" clause.",
     "policy, critics, claimed, would harm"),
    ("C19", "Challenge", "Did any of the senators who had promised to oppose the bill actually vote against it?",
     ["any"], ["Did", "vote"],
     "Turn the question into a statement: \"Any of the senators did vote against it.\" \"Had promised\" belongs to the \"who\" clause; \"actually\" is an adverb.",
     "senators, had promised, to oppose"),
    ("C20", "Challenge", "Rising steadily over the past decade, the cost of housing in cities that attract technology companies has pushed many families into the suburbs.",
     ["cost"], ["has", "pushed"],
     "\"Rising steadily\" is a participle describing the cost. \"Housing\" is inside \"of housing,\" and \"attract\" belongs to the \"that\" clause.",
     "Rising, housing, cities, attract, families"),
    ("C21", "Challenge", "Among the documents discovered in the attic of the abandoned farmhouse was a letter signed by Abraham Lincoln.",
     ["letter"], ["was"],
     "Normal order: \"A letter was among the documents.\" \"Discovered\" and \"signed\" are participles.",
     "documents, discovered, farmhouse, signed"),
    ("C22", "Challenge", "The teacher's insistence that every student rewrite the essay, regardless of the grade earned on the first draft, frustrated the class.",
     ["insistence"], ["frustrated"],
     "\"Rewrite\" belongs to the \"that\" clause after \"insistence,\" and \"earned\" is a participle. Ask what frustrated the class: the insistence.",
     "student, rewrite, grade, earned"),
    ("C23", "Challenge", "The flock of geese flying south for the winter, honking loudly as they passed over the lake, was visible from miles away.",
     ["flock"], ["was"],
     "\"Flying\" and \"honking\" are participles, and \"passed\" belongs to the \"as\" clause. Singular \"flock\" takes \"was.\"",
     "geese, flying, honking, passed"),
    ("C24", "Challenge", "To the surprise of everyone attending the ceremony, the award for outstanding service went to the janitor, who had worked at the school for forty years.",
     ["award"], ["went"],
     "\"To the surprise of everyone\" is an opening prepositional phrase, and \"attending\" is a participle. \"Had worked\" belongs to the \"who\" clause about the janitor.",
     "surprise, attending, service, janitor, had worked"),
    ("C25", "Challenge", "The extent to which social media platforms shape the opinions of young voters remains a subject of intense debate.",
     ["extent"], ["remains"],
     "\"Platforms\" and \"shape\" form a side clause (\"to which platforms shape...\"). The main subject is \"extent,\" and it remains a subject of debate.",
     "platforms, shape, opinions, voters"),
    ("C26", "Challenge", "Seldom have the members of the city council, a group known for its bitter disagreements, voted unanimously.",
     ["members"], ["have", "voted"],
     "Normal order: \"The members have seldom voted unanimously.\" \"A group known for...\" is an appositive describing the council.",
     "council, group, known"),
    ("C27", "Challenge", "The recipe, handed down through five generations of my mother's family and scribbled on a yellowed index card, requires three kinds of chocolate.",
     ["recipe"], ["requires"],
     "\"Handed\" and \"scribbled\" are participles set off by commas, not verbs. The recipe requires chocolate.",
     "handed, scribbled, generations, card"),
    ("C28", "Challenge", "The sound of children laughing and the smell of popcorn drifting from the concession stand make the fair unforgettable.",
     ["sound", "smell"], ["make"],
     "Two subjects joined by \"and\" take the plural \"make.\" \"Laughing\" and \"drifting\" are participles.",
     "children, laughing, popcorn, drifting"),
    ("C29", "Challenge", "A series of mistakes made by the engineers responsible for designing the bridge's supports was blamed for the collapse.",
     ["series"], ["was", "blamed"],
     "\"Series\" is singular, so it takes \"was blamed.\" \"Mistakes\" and \"engineers\" sit inside phrases, and \"made\" and \"designing\" are verbals.",
     "mistakes, made, engineers, designing"),
    ("C30", "Challenge", "The athlete who had trained for years to qualify for the Olympics, only to be injured weeks before the trials, now coaches young runners.",
     ["athlete"], ["coaches"],
     "\"Had trained\" belongs to the \"who\" clause, and \"to qualify\" and \"to be injured\" are infinitives. \"Now\" is an adverb.",
     "had trained, to qualify, to be injured"),
    ("C31", "Challenge", "In the corner of the museum's dimly lit east gallery, protected by a glass case and guarded by two security officers, sits a diamond the size of a walnut.",
     ["diamond"], ["sits"],
     "Normal order: \"A diamond sits in the corner of the gallery.\" \"Protected\" and \"guarded\" are participles describing the diamond.",
     "corner, gallery, protected, guarded, officers"),
    ("C32", "Challenge", "The professor, together with several colleagues from universities in Germany and Japan, has published a study challenging long-held assumptions about memory.",
     ["professor"], ["has", "published"],
     "\"Together with several colleagues\" is an interrupter, so the singular \"has published\" agrees with \"professor.\" \"Challenging\" is a participle.",
     "colleagues, universities, challenging"),
    ("C33", "Challenge", "Keeping a journal, a habit that many successful writers credit with sharpening their observational skills, takes only a few minutes a day.",
     ["Keeping"], ["takes"],
     "\"Keeping a journal\" is a gerund phrase acting as the subject. \"A habit that...\" renames it, and \"credit\" belongs to that clause.",
     "journal, habit, writers, credit, sharpening"),
    ("C34", "Challenge", "Hardly had the speaker begun her presentation when the fire alarm sounded.",
     ["speaker"], ["had", "begun"],
     "Normal order: \"The speaker had hardly begun her presentation when...\" The \"when\" clause is subordinate, so \"alarm\" and \"sounded\" are decoys.",
     "alarm, sounded"),
    ("C35", "Challenge", "The reasons the company gave for canceling the product, most of which were vague, did not satisfy shareholders.",
     ["reasons"], ["did", "satisfy"],
     "\"The company gave\" is a side clause describing the reasons, and \"were\" belongs to \"most of which were vague.\" \"Not\" is an adverb.",
     "company, gave, canceling, most, were"),
    ("C36", "Challenge", "Every one of the volunteers who signed up to clean the beach after the oil spill received a certificate.",
     ["one"], ["received"],
     "\"Every one\" is the subject; \"volunteers\" is inside \"of the volunteers.\" \"Signed\" belongs to the \"who\" clause.",
     "volunteers, signed, to clean"),
    ("C37", "Challenge", "The quality of the photographs taken by the rover exploring the surface of Mars has astonished astronomers.",
     ["quality"], ["has", "astonished"],
     "\"Photographs\" is inside \"of the photographs,\" and \"taken\" and \"exploring\" are participles. The quality has astonished astronomers.",
     "photographs, taken, rover, exploring"),
    ("C38", "Challenge", "Why has the shipment of medical supplies destined for the clinics in the northern villages been delayed again?",
     ["shipment"], ["has", "been", "delayed"],
     "Statement form: \"The shipment has been delayed again.\" \"Destined\" is a participle, and \"supplies\" and \"clinics\" sit inside phrases.",
     "supplies, destined, clinics"),
    ("C39", "Challenge", "The old man sitting on the bench feeding pigeons, whom the neighborhood children call \"the Professor,\" was once a famous mathematician.",
     ["man"], ["was"],
     "\"Sitting\" and \"feeding\" are participles, and \"call\" belongs to the \"whom\" clause. \"Once\" is an adverb.",
     "sitting, feeding, pigeons, children, call"),
    ("C40", "Challenge", "Not until the last of the votes cast in the rural counties had been counted did the candidate concede.",
     ["candidate"], ["did", "concede"],
     "Normal order: \"The candidate did not concede until...\" The \"until\" clause (\"had been counted\") is subordinate.",
     "last, votes, cast, had been counted"),
    ("C41", "Challenge", "The diversity of plant species found in the rainforest canopy, much of which remains unexplored, rivals that of entire continents.",
     ["diversity"], ["rivals"],
     "\"Species\" is inside \"of plant species,\" \"found\" is a participle, and \"remains\" belongs to the \"much of which\" clause.",
     "species, found, canopy, much, remains"),
    ("C42", "Challenge", "Before them, stretching to the horizon under a sky streaked with pink and orange, lay the vast desert they would have to cross.",
     ["desert"], ["lay"],
     "Normal order: \"The vast desert lay before them.\" \"Stretching\" and \"streaked\" are participles, and \"would have\" belongs to the clause \"they would have to cross.\"",
     "them, stretching, sky, streaked, would have"),
    ("C43", "Challenge", "The committee's report, praised by some for its thoroughness and criticized by others for its length, has not yet been released to the public.",
     ["report"], ["has", "been", "released"],
     "\"Praised\" and \"criticized\" are participles set off by commas. \"Not\" and \"yet\" are adverbs inside the verb phrase.",
     "praised, criticized"),
    ("C44", "Challenge", "Learning to play an instrument as an adult, despite the frustrations that inevitably accompany early practice, can be deeply rewarding.",
     ["Learning"], ["can", "be"],
     "\"Learning to play an instrument\" is a gerund phrase acting as the subject. \"Rewarding\" is an adjective after the linking verb \"can be.\"",
     "to play, instrument, frustrations, accompany, rewarding"),
    ("C45", "Challenge", "A team of archaeologists led by a researcher from Cairo, working alongside local excavators, has uncovered a previously unknown tomb.",
     ["team"], ["has", "uncovered"],
     "\"Archaeologists\" is inside \"of archaeologists,\" and \"led\" and \"working\" are participles. Singular \"team\" takes \"has uncovered.\"",
     "archaeologists, led, researcher, working"),
    ("C46", "Challenge", "Either the students in the advanced section or their teacher is responsible for organizing the trip.",
     ["students", "teacher"], ["is"],
     "Either...or joins two subjects; the verb agrees with the nearer one, \"teacher,\" so it's \"is.\" \"Organizing\" is a gerund.",
     "section, organizing"),
    ("C47", "Challenge", "The tradition of lighting lanterns on the final night of the festival, which dates back more than a thousand years, draws visitors from around the world.",
     ["tradition"], ["draws"],
     "\"Lighting\" is a gerund inside \"of lighting lanterns,\" and \"dates\" belongs to the \"which\" clause.",
     "lighting, lanterns, festival, dates"),
    ("C48", "Challenge", "So convincing was the forger's imitation of the master's brushwork that even the experts examining the canvas were fooled.",
     ["imitation"], ["was"],
     "Normal order: \"The forger's imitation was so convincing that...\" \"Were fooled\" belongs to the subordinate \"that\" clause.",
     "forger's, brushwork, experts, examining, were fooled"),
    ("C49", "Challenge", "The students who the teacher believed had cheated on the exam were later cleared of any wrongdoing.",
     ["students"], ["were", "cleared"],
     "\"Believed\" and \"had cheated\" belong to the \"who the teacher believed\" clause. \"Later\" is an adverb.",
     "teacher, believed, had cheated"),
    ("C50", "Challenge", "Overlooking the harbor, where fishing boats painted in bright blues and reds bob gently in the morning tide, stands a lighthouse built in 1824.",
     ["lighthouse"], ["stands"],
     "Normal order: \"A lighthouse stands overlooking the harbor.\" \"Bob\" belongs to the \"where\" clause, and \"painted\" and \"built\" are participles.",
     "Overlooking, harbor, boats, painted, bob, built"),
]


def norm(w):
    return re.sub(r"[^\w'’-]", "", w).lower()


def locate(words, spec, qid):
    name, _, nth = spec.partition("#")
    nth = int(nth or 1)
    hits = [i for i, w in enumerate(words) if norm(w) == name.lower()]
    if len(hits) < nth:
        sys.exit(f"{qid}: '{spec}' not found in {words}")
    if nth == 1 and len(hits) > 1:
        print(f"note {qid}: '{name}' appears {len(hits)}x, using first")
    return hits[nth - 1]


def sql_str(s):
    return "'" + s.replace("'", "''") + "'"


def main():
    rows = []
    seen = set()
    for pos, (qid, set_name, sentence, subj, pred, expl, decoys) in enumerate(Q, start=1):
        assert qid not in seen, qid
        seen.add(qid)
        words = sentence.split()
        s_idx = sorted(locate(words, s, qid) for s in subj)
        p_idx = sorted(locate(words, p, qid) for p in pred)
        assert not set(s_idx) & set(p_idx), qid
        rows.append((qid, pos, set_name, sentence, words, s_idx, p_idx, expl, decoys))
        print(f"{qid:4} S={' '.join(words[i] for i in s_idx):28} P={' '.join(words[i] for i in p_idx)}")

    out = ["-- Generated by questions.py. Do not edit by hand.",
           "begin;",
           "delete from public.question_keys;",
           "delete from public.questions where id not in (select question_id from public.attempts);"]
    for qid, pos, set_name, sentence, words, s_idx, p_idx, expl, decoys in rows:
        arr = "array[" + ",".join(sql_str(w) for w in words) + "]::text[]"
        out.append(
            f"insert into public.questions (id, position, set_name, sentence, words) values "
            f"({sql_str(qid)}, {pos}, {sql_str(set_name)}, {sql_str(sentence)}, {arr}) "
            f"on conflict (id) do update set position=excluded.position, set_name=excluded.set_name, "
            f"sentence=excluded.sentence, words=excluded.words;")
        out.append(
            f"insert into public.question_keys (question_id, subject_idx, predicate_idx, explanation, decoys) values "
            f"({sql_str(qid)}, array{s_idx}::int[], array{p_idx}::int[], {sql_str(expl)}, {sql_str(decoys)});")
    out.append("commit;")
    with open(__file__.replace("questions.py", "seed.sql"), "w") as f:
        f.write("\n".join(out) + "\n")
    print(f"\n{len(rows)} questions written to seed.sql")


if __name__ == "__main__":
    main()
