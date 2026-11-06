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

## Common tasks

- **Student forgot their password:** in Supabase, go to Authentication > Users, find them, and use "Send password recovery" (requires custom SMTP) or delete the user so they can sign up again. Deleting a user also deletes their answers.
- **Let a student redo a question:** delete their row from the `attempts` table.
- **Change or add questions:** edit `supabase/questions.py`, run `python3 questions.py` to check every answer word is found, then load the generated `seed.sql` in the SQL editor.
