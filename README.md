# Subject & Verb Practice

SAT homework site for finding the simple subject and simple predicate. Students sign in, answer 55 sentences one at a time by clicking words, and get instant feedback with an explanation. The teacher dashboard shows each student's scores, the most-missed questions, and the decoys students fall for.

- `index.html` is the student page.
- `teacher.html` is the teacher dashboard.
- `supabase/` holds the database schema and the question bank.

## How it works

- Static files hosted on GitHub Pages, with no build step.
- Supabase handles accounts and stores answers.
- The answer key lives only in the database. Students never download it. Each submission is graded by the `submit_answer` database function, which returns the correct answer and explanation.
- A student's first submission for each question is final, so the dashboard reflects first attempts.

## One-time setup

1. **Turn off email confirmation.** Supabase's built-in email service only sends to members of your Supabase team, so students would never receive confirmation emails. In the Supabase dashboard, go to Authentication > Sign In / Providers > Email and turn off **Confirm email**.
2. **Publish on GitHub Pages.** In the repo, go to Settings > Pages, set Source to "Deploy from a branch," and choose `main` / root. The site will be at `https://<username>.github.io/SAT-homework/`.
3. **Make yourself the teacher.** Open `teacher.html` on the live site and create an account. Then, in Supabase's SQL editor, run this with your email:

   ```sql
   insert into public.teachers (user_id)
   select id from auth.users where email = 'you@example.com';
   ```

4. Send students the main site link. They choose "Create account" the first time.

## Weekly homework

Practice sets are grouped into weekly sections ("Homework 1", "Homework 2", ...) by the `homework` column in `practice_sets`. The newest homework shows first and is marked "This week." To start a new week, add sets with the next homework number.

Set types:

- `subject_verb`: click the simple subject, then the verb (`supabase/questions.py`).
- `multiple_choice`: Educator Question Bank style A-D questions (`supabase/sets/extract_qbank.py`, `load_sql.py`).
- `trim_subject_verb`: cross out the extra information, then find the subject and verb (`supabase/sets/cross_out.py`).

## Design

The look follows Apple's Liquid Glass language: glass toolbars and control dock over solid content cards (`css/tokens.css`, `js/refraction.js`, MIT-licensed from the apple-liquid-glass skill). The accent color is the purple from the logo. Run `./bump-version.sh` before committing so browsers load the new files right away.

## Common tasks

- **Student forgot their password:** in Supabase, go to Authentication > Users, find them, and use "Send password recovery" (requires custom SMTP) or delete the user so they can sign up again. Deleting a user also deletes their answers.
- **Let a student redo a question:** delete their row from the `attempts` table.
- **Change or add questions:** edit `supabase/questions.py`, run `python3 questions.py` to check every answer word is found, then load the generated `seed.sql` in the SQL editor.
