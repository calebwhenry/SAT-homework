-- SAT Homework schema.
-- Students can read questions but never the answer key. Grading happens in
-- submit_answer(), which runs on the server and records the first attempt only.
-- The teacher reads everything through teacher_* functions, gated by is_teacher().

-- Profiles: one row per signed-in student (name shown on the teacher dashboard)
create table if not exists public.profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  full_name text not null check (length(trim(full_name)) between 1 and 80),
  email text,
  created_at timestamptz not null default now()
);

-- Teachers: user ids allowed to open the dashboard (added by hand, never by the app)
create table if not exists public.teachers (
  user_id uuid primary key references auth.users (id) on delete cascade,
  added_at timestamptz not null default now()
);

-- Questions: what students see
create table if not exists public.questions (
  id text primary key,
  position int not null unique,
  set_name text not null,
  sentence text not null,
  words text[] not null
);

-- Answer key: never readable by students
create table if not exists public.question_keys (
  question_id text primary key references public.questions (id) on delete cascade,
  subject_idx int[] not null,
  predicate_idx int[] not null,
  explanation text not null,
  decoys text
);

-- Attempts: one per student per question (the first submission is final)
create table if not exists public.attempts (
  id bigint generated always as identity primary key,
  user_id uuid not null references auth.users (id) on delete cascade,
  question_id text not null references public.questions (id) on delete cascade,
  subject_sel int[] not null,
  predicate_sel int[] not null,
  subject_correct boolean not null,
  predicate_correct boolean not null,
  created_at timestamptz not null default now(),
  unique (user_id, question_id)
);
create index if not exists attempts_question_idx on public.attempts (question_id);

alter table public.profiles enable row level security;
alter table public.teachers enable row level security;
alter table public.questions enable row level security;
alter table public.question_keys enable row level security;
alter table public.attempts enable row level security;

-- Table privileges: explicit, least privilege
revoke all on public.profiles, public.teachers, public.questions, public.question_keys, public.attempts from anon, authenticated;
grant select, insert, update (full_name) on public.profiles to authenticated;
grant select on public.questions to authenticated;
grant select on public.attempts to authenticated;

drop policy if exists "own profile read" on public.profiles;
create policy "own profile read" on public.profiles for select to authenticated
  using ((select auth.uid()) = id);
drop policy if exists "own profile insert" on public.profiles;
create policy "own profile insert" on public.profiles for insert to authenticated
  with check ((select auth.uid()) = id);
drop policy if exists "own profile update" on public.profiles;
create policy "own profile update" on public.profiles for update to authenticated
  using ((select auth.uid()) = id) with check ((select auth.uid()) = id);

drop policy if exists "signed-in users read questions" on public.questions;
create policy "signed-in users read questions" on public.questions for select to authenticated
  using (true);

drop policy if exists "own attempts read" on public.attempts;
create policy "own attempts read" on public.attempts for select to authenticated
  using ((select auth.uid()) = user_id);

-- Fill the profile's email from the auth record so it can't be spoofed
create or replace function public.profiles_set_email()
returns trigger language plpgsql security definer set search_path = '' as $$
begin
  new.email := (select u.email from auth.users u where u.id = new.id);
  return new;
end $$;
drop trigger if exists profiles_set_email on public.profiles;
create trigger profiles_set_email before insert or update on public.profiles
  for each row execute function public.profiles_set_email();

create or replace function public.is_teacher()
returns boolean language sql stable security definer set search_path = '' as $$
  select exists (select 1 from public.teachers t where t.user_id = (select auth.uid()));
$$;

create or replace function public.same_set(a int[], b int[])
returns boolean language sql immutable set search_path = '' as $$
  select coalesce((select array_agg(distinct x order by x) from unnest(a) x), '{}')
       = coalesce((select array_agg(distinct x order by x) from unnest(b) x), '{}');
$$;

-- Grade a submission. Returns the result plus the correct answer and explanation.
-- If the student already answered this question, returns their stored result instead.
create or replace function public.submit_answer(p_question_id text, p_subject int[], p_predicate int[])
returns jsonb language plpgsql security definer set search_path = '' as $$
declare
  v_uid uuid := (select auth.uid());
  k public.question_keys;
  a public.attempts;
  n int;
begin
  if v_uid is null then raise exception 'Not signed in'; end if;
  select * into k from public.question_keys where question_id = p_question_id;
  if not found then raise exception 'Unknown question'; end if;
  select cardinality(words) into n from public.questions where id = p_question_id;
  if coalesce(cardinality(p_subject), 0) = 0 or coalesce(cardinality(p_predicate), 0) = 0 then
    raise exception 'Pick a subject and a predicate first';
  end if;
  if exists (select 1 from unnest(p_subject || p_predicate) x where x < 0 or x >= n) then
    raise exception 'Invalid selection';
  end if;

  insert into public.attempts (user_id, question_id, subject_sel, predicate_sel, subject_correct, predicate_correct)
  values (v_uid, p_question_id, p_subject, p_predicate,
          public.same_set(p_subject, k.subject_idx), public.same_set(p_predicate, k.predicate_idx))
  on conflict (user_id, question_id) do nothing;

  select * into a from public.attempts where user_id = v_uid and question_id = p_question_id;
  return jsonb_build_object(
    'question_id', a.question_id,
    'subject_sel', a.subject_sel, 'predicate_sel', a.predicate_sel,
    'subject_correct', a.subject_correct, 'predicate_correct', a.predicate_correct,
    'subject_idx', k.subject_idx, 'predicate_idx', k.predicate_idx,
    'explanation', k.explanation);
end $$;

-- A student's own graded attempts, with the key, so revisited questions show their feedback
create or replace function public.my_results()
returns table (question_id text, subject_sel int[], predicate_sel int[], subject_correct boolean,
               predicate_correct boolean, subject_idx int[], predicate_idx int[], explanation text)
language sql stable security definer set search_path = '' as $$
  select a.question_id, a.subject_sel, a.predicate_sel, a.subject_correct, a.predicate_correct,
         k.subject_idx, k.predicate_idx, k.explanation
  from public.attempts a join public.question_keys k on k.question_id = a.question_id
  where a.user_id = (select auth.uid());
$$;

-- Teacher: every student, answered or not
create or replace function public.teacher_students()
returns table (user_id uuid, full_name text, email text, joined timestamptz)
language plpgsql stable security definer set search_path = '' as $$
begin
  if not public.is_teacher() then raise exception 'Teachers only'; end if;
  return query
    select p.id, p.full_name, p.email, p.created_at from public.profiles p
    where p.id not in (select t.user_id from public.teachers t)
    order by p.full_name;
end $$;

-- Teacher: every attempt, with the words each student picked
create or replace function public.teacher_attempts()
returns table (user_id uuid, question_id text, subject_correct boolean, predicate_correct boolean,
               subject_words text, predicate_words text, created_at timestamptz)
language plpgsql stable security definer set search_path = '' as $$
begin
  if not public.is_teacher() then raise exception 'Teachers only'; end if;
  return query
    select a.user_id, a.question_id, a.subject_correct, a.predicate_correct,
      (select string_agg(regexp_replace(q.words[i + 1], '[^[:alnum:]''’-]', '', 'g'), ' ' order by i) from unnest(a.subject_sel) i),
      (select string_agg(regexp_replace(q.words[i + 1], '[^[:alnum:]''’-]', '', 'g'), ' ' order by i) from unnest(a.predicate_sel) i),
      a.created_at
    from public.attempts a join public.questions q on q.id = a.question_id;
end $$;

-- Teacher: the answer key, for the dashboard's question table
create or replace function public.teacher_keys()
returns table (question_id text, q_position int, sentence text, subject_words text, predicate_words text, decoys text)
language plpgsql stable security definer set search_path = '' as $$
begin
  if not public.is_teacher() then raise exception 'Teachers only'; end if;
  return query
    select q.id, q.position, q.sentence,
      (select string_agg(regexp_replace(q.words[i + 1], '[^[:alnum:]''’-]', '', 'g'), ' ' order by i) from unnest(k.subject_idx) i),
      (select string_agg(regexp_replace(q.words[i + 1], '[^[:alnum:]''’-]', '', 'g'), ' ' order by i) from unnest(k.predicate_idx) i),
      k.decoys
    from public.questions q join public.question_keys k on k.question_id = q.id
    order by q.position;
end $$;

-- Function access: signed-in users only
revoke execute on function public.profiles_set_email(), public.is_teacher(), public.same_set(int[], int[]),
  public.submit_answer(text, int[], int[]), public.my_results(), public.teacher_students(),
  public.teacher_attempts(), public.teacher_keys() from public, anon;
grant execute on function public.is_teacher(), public.submit_answer(text, int[], int[]), public.my_results(),
  public.teacher_students(), public.teacher_attempts(), public.teacher_keys() to authenticated;

-- Trigger and helper functions are never called directly
revoke execute on function public.profiles_set_email() from authenticated;
revoke execute on function public.same_set(int[], int[]) from authenticated;
