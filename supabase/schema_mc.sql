-- DRAFT, NOT APPLIED: a different mc_* schema already exists in the database
-- (migration mc_question_sets). Waiting on a decision before using this file.

-- Multiple-choice question sets (e.g. Educator Question Bank PDFs).
-- Same model as the subject/verb set: students read questions, never the key;
-- submit_mc() grades on the server and keeps the first attempt.

create table if not exists public.question_sets (
  id text primary key,
  title text not null,
  kind text not null check (kind in ('subject_verb', 'multiple_choice')),
  position int not null,
  blurb text
);

create table if not exists public.mc_questions (
  id text primary key,
  set_id text not null references public.question_sets (id) on delete cascade,
  position int not null,
  qbank_id text,
  difficulty text,
  passage text[] not null,           -- paragraphs; may contain <i> only
  stem text not null,
  choices jsonb not null,            -- {"A": "...", "B": "...", ...}
  unique (set_id, position)
);

create table if not exists public.mc_keys (
  question_id text primary key references public.mc_questions (id) on delete cascade,
  answer text not null check (answer in ('A', 'B', 'C', 'D')),
  rationale text[] not null
);

create table if not exists public.mc_attempts (
  id bigint generated always as identity primary key,
  user_id uuid not null references auth.users (id) on delete cascade,
  question_id text not null references public.mc_questions (id) on delete cascade,
  choice text not null check (choice in ('A', 'B', 'C', 'D')),
  correct boolean not null,
  created_at timestamptz not null default now(),
  unique (user_id, question_id)
);
create index if not exists mc_attempts_question_idx on public.mc_attempts (question_id);

alter table public.question_sets enable row level security;
alter table public.mc_questions enable row level security;
alter table public.mc_keys enable row level security;
alter table public.mc_attempts enable row level security;

revoke all on public.question_sets, public.mc_questions, public.mc_keys, public.mc_attempts from anon, authenticated;
grant select on public.question_sets, public.mc_questions, public.mc_attempts to authenticated;

drop policy if exists "signed-in users read sets" on public.question_sets;
create policy "signed-in users read sets" on public.question_sets for select to authenticated using (true);
drop policy if exists "signed-in users read mc questions" on public.mc_questions;
create policy "signed-in users read mc questions" on public.mc_questions for select to authenticated using (true);
drop policy if exists "own mc attempts read" on public.mc_attempts;
create policy "own mc attempts read" on public.mc_attempts for select to authenticated
  using ((select auth.uid()) = user_id);

insert into public.question_sets (id, title, kind, position, blurb) values
  ('subject-verb', 'Subject & Verb', 'subject_verb', 1, 'Find the simple subject and simple predicate.')
on conflict (id) do nothing;

create or replace function public.submit_mc(p_question_id text, p_choice text)
returns jsonb language plpgsql security definer set search_path = '' as $$
declare
  v_uid uuid := (select auth.uid());
  k public.mc_keys;
  a public.mc_attempts;
begin
  if v_uid is null then raise exception 'Not signed in'; end if;
  if p_choice not in ('A', 'B', 'C', 'D') then raise exception 'Pick an answer first'; end if;
  select * into k from public.mc_keys where question_id = p_question_id;
  if not found then raise exception 'Unknown question'; end if;
  insert into public.mc_attempts (user_id, question_id, choice, correct)
  values (v_uid, p_question_id, p_choice, p_choice = k.answer)
  on conflict (user_id, question_id) do nothing;
  select * into a from public.mc_attempts where user_id = v_uid and question_id = p_question_id;
  return jsonb_build_object('question_id', a.question_id, 'choice', a.choice, 'correct', a.correct,
                            'answer', k.answer, 'rationale', to_jsonb(k.rationale));
end $$;

create or replace function public.my_mc_results()
returns table (question_id text, choice text, correct boolean, answer text, rationale text[])
language sql stable security definer set search_path = '' as $$
  select a.question_id, a.choice, a.correct, k.answer, k.rationale
  from public.mc_attempts a join public.mc_keys k on k.question_id = a.question_id
  where a.user_id = (select auth.uid());
$$;

create or replace function public.teacher_mc_attempts()
returns table (user_id uuid, question_id text, choice text, correct boolean, created_at timestamptz)
language plpgsql stable security definer set search_path = '' as $$
begin
  if not public.is_teacher() then raise exception 'Teachers only'; end if;
  return query select a.user_id, a.question_id, a.choice, a.correct, a.created_at from public.mc_attempts a;
end $$;

create or replace function public.teacher_mc_keys()
returns table (question_id text, set_id text, q_position int, difficulty text, passage text[], stem text, choices jsonb, answer text)
language plpgsql stable security definer set search_path = '' as $$
begin
  if not public.is_teacher() then raise exception 'Teachers only'; end if;
  return query
    select q.id, q.set_id, q.position, q.difficulty, q.passage, q.stem, q.choices, k.answer
    from public.mc_questions q join public.mc_keys k on k.question_id = q.id
    order by q.set_id, q.position;
end $$;

revoke execute on function public.submit_mc(text, text), public.my_mc_results(),
  public.teacher_mc_attempts(), public.teacher_mc_keys() from public, anon;
grant execute on function public.submit_mc(text, text), public.my_mc_results(),
  public.teacher_mc_attempts(), public.teacher_mc_keys() to authenticated;
