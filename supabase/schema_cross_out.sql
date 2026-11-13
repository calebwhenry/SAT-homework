-- Homework grouping + "Cross out, then find" sets.
-- Students cross out extra information, then pick the subject and verb from what's left.
-- Grading runs on the server: crossing out is right when every "extra" word is crossed
-- out and neither the subject nor the verb is; optional words can go either way.

alter table public.practice_sets add column if not exists homework int not null default 1;
alter table public.practice_sets drop constraint if exists practice_sets_kind_check;
alter table public.practice_sets add constraint practice_sets_kind_check
  check (kind in ('subject_verb', 'multiple_choice', 'trim_subject_verb'));

update public.practice_sets set homework = 1, position = 1 where id = 'subject-verb';
update public.practice_sets set homework = 1, position = 2 where id = 'words-in-context';
insert into public.practice_sets (id, title, kind, position, homework, blurb) values
  ('cross-out', 'Cross Out, Then Find', 'trim_subject_verb', 1, 2,
   'Cross out the extra information, then find the subject and verb.')
on conflict (id) do update set title = excluded.title, kind = excluded.kind, homework = excluded.homework,
  position = excluded.position, blurb = excluded.blurb;
update public.practice_sets set blurb = 'Find the simple subject and the simple predicate.' where id = 'subject-verb';
update public.practice_sets set blurb = 'Choose the most logical and precise word.' where id = 'words-in-context';

create table if not exists public.trim_questions (
  id text primary key,
  set_id text not null references public.practice_sets (id) on delete cascade,
  position int not null,
  sentence text not null,
  words text[] not null,
  unique (set_id, position)
);

create table if not exists public.trim_keys (
  question_id text primary key references public.trim_questions (id) on delete cascade,
  extra_idx int[] not null,
  optional_idx int[] not null default '{}',
  subject_idx int[] not null,
  predicate_idx int[] not null,
  trimmed text not null,
  explanation text not null
);

create table if not exists public.trim_attempts (
  id bigint generated always as identity primary key,
  user_id uuid not null references auth.users (id) on delete cascade,
  question_id text not null references public.trim_questions (id) on delete cascade,
  removed_sel int[] not null,
  subject_sel int[] not null,
  predicate_sel int[] not null,
  removal_correct boolean not null,
  subject_correct boolean not null,
  predicate_correct boolean not null,
  created_at timestamptz not null default now(),
  unique (user_id, question_id)
);
create index if not exists trim_attempts_question_idx on public.trim_attempts (question_id);

alter table public.trim_questions enable row level security;
alter table public.trim_keys enable row level security;
alter table public.trim_attempts enable row level security;

revoke all on public.trim_questions, public.trim_keys, public.trim_attempts from anon, authenticated;
grant select on public.trim_questions, public.trim_attempts to authenticated;

drop policy if exists "signed-in users read trim questions" on public.trim_questions;
create policy "signed-in users read trim questions" on public.trim_questions for select to authenticated using (true);
drop policy if exists "own trim attempts read" on public.trim_attempts;
create policy "own trim attempts read" on public.trim_attempts for select to authenticated
  using ((select auth.uid()) = user_id);

create or replace function public.trim_feedback(a public.trim_attempts, k public.trim_keys)
returns jsonb language sql stable set search_path = '' as $$
  select jsonb_build_object(
    'question_id', a.question_id,
    'removed_sel', a.removed_sel, 'subject_sel', a.subject_sel, 'predicate_sel', a.predicate_sel,
    'removal_correct', a.removal_correct, 'subject_correct', a.subject_correct, 'predicate_correct', a.predicate_correct,
    'extra_idx', k.extra_idx, 'optional_idx', k.optional_idx,
    'subject_idx', k.subject_idx, 'predicate_idx', k.predicate_idx,
    'trimmed', k.trimmed, 'explanation', k.explanation);
$$;

create or replace function public.submit_trim(p_question_id text, p_removed int[], p_subject int[], p_predicate int[])
returns jsonb language plpgsql security definer set search_path = '' as $$
declare
  v_uid uuid := (select auth.uid());
  k public.trim_keys;
  a public.trim_attempts;
  n int;
  v_removed int[] := coalesce(p_removed, '{}');
begin
  if v_uid is null then raise exception 'Not signed in'; end if;
  select * into k from public.trim_keys where question_id = p_question_id;
  if not found then raise exception 'Unknown question'; end if;
  select cardinality(words) into n from public.trim_questions where id = p_question_id;
  if coalesce(cardinality(p_subject), 0) = 0 or coalesce(cardinality(p_predicate), 0) = 0 then
    raise exception 'Pick a subject and a verb first';
  end if;
  if exists (select 1 from unnest(v_removed || p_subject || p_predicate) x where x < 0 or x >= n) then
    raise exception 'Invalid selection';
  end if;
  if (p_subject || p_predicate) && v_removed then
    raise exception 'Pick the subject and verb from the words you kept';
  end if;

  insert into public.trim_attempts (user_id, question_id, removed_sel, subject_sel, predicate_sel,
                                    removal_correct, subject_correct, predicate_correct)
  values (v_uid, p_question_id, v_removed, p_subject, p_predicate,
          k.extra_idx <@ v_removed and not (v_removed && (k.subject_idx || k.predicate_idx)),
          public.same_set(p_subject, k.subject_idx), public.same_set(p_predicate, k.predicate_idx))
  on conflict (user_id, question_id) do nothing;

  select * into a from public.trim_attempts where user_id = v_uid and question_id = p_question_id;
  return public.trim_feedback(a, k);
end $$;

create or replace function public.my_trim_results()
returns setof jsonb language sql stable security definer set search_path = '' as $$
  select public.trim_feedback(a, k)
  from public.trim_attempts a join public.trim_keys k on k.question_id = a.question_id
  where a.user_id = (select auth.uid());
$$;

create or replace function public.trim_words(p_words text[], p_idx int[])
returns text language sql immutable set search_path = '' as $$
  select string_agg(regexp_replace(p_words[i + 1], '[^[:alnum:]''’-]', '', 'g'), ' ' order by i) from unnest(p_idx) i;
$$;

create or replace function public.teacher_trim_attempts()
returns table (user_id uuid, question_id text, removal_correct boolean, subject_correct boolean, predicate_correct boolean,
               missed_words text, cut_core_words text, subject_words text, predicate_words text, created_at timestamptz)
language plpgsql stable security definer set search_path = '' as $$
begin
  if not public.is_teacher() then raise exception 'Teachers only'; end if;
  return query
    select a.user_id, a.question_id, a.removal_correct, a.subject_correct, a.predicate_correct,
      public.trim_words(q.words, array(select x from unnest(k.extra_idx) x where x <> all (a.removed_sel))),
      public.trim_words(q.words, array(select x from unnest(k.subject_idx || k.predicate_idx) x where x = any (a.removed_sel))),
      public.trim_words(q.words, a.subject_sel), public.trim_words(q.words, a.predicate_sel), a.created_at
    from public.trim_attempts a
    join public.trim_questions q on q.id = a.question_id
    join public.trim_keys k on k.question_id = a.question_id;
end $$;

create or replace function public.teacher_trim_keys()
returns table (question_id text, set_id text, q_position int, sentence text, trimmed text, subject_words text, predicate_words text)
language plpgsql stable security definer set search_path = '' as $$
begin
  if not public.is_teacher() then raise exception 'Teachers only'; end if;
  return query
    select q.id, q.set_id, q.position, q.sentence, k.trimmed,
      public.trim_words(q.words, k.subject_idx), public.trim_words(q.words, k.predicate_idx)
    from public.trim_questions q join public.trim_keys k on k.question_id = q.id
    order by q.set_id, q.position;
end $$;

revoke execute on function public.trim_feedback(public.trim_attempts, public.trim_keys), public.trim_words(text[], int[]),
  public.submit_trim(text, int[], int[], int[]), public.my_trim_results(),
  public.teacher_trim_attempts(), public.teacher_trim_keys() from public, anon, authenticated;
grant execute on function public.submit_trim(text, int[], int[], int[]), public.my_trim_results(),
  public.teacher_trim_attempts(), public.teacher_trim_keys() to authenticated;
