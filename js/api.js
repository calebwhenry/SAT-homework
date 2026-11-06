// Every call to Supabase goes through this file.
import { createClient } from "https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2/+esm";
import { SUPABASE_URL, SUPABASE_KEY } from "./config.js";

const sb = createClient(SUPABASE_URL, SUPABASE_KEY);

function check({ data, error }) {
  if (error) throw new Error(error.message);
  return data;
}

export async function currentUser() {
  const { data } = await sb.auth.getSession();
  return data.session?.user ?? null;
}

export async function signIn(email, password) {
  const data = check(await sb.auth.signInWithPassword({ email, password }));
  return data.user;
}

// Returns the new user, or null when Supabase still requires email confirmation.
export async function signUp(email, password) {
  const data = check(await sb.auth.signUp({ email, password }));
  return data.session ? data.user : null;
}

export async function signOut() {
  await sb.auth.signOut();
}

export async function getProfile(userId) {
  return check(await sb.from("profiles").select("full_name").eq("id", userId).maybeSingle());
}

export async function createProfile(userId, fullName) {
  check(await sb.from("profiles").insert({ id: userId, full_name: fullName }));
}

export async function loadQuestions() {
  return check(await sb.from("questions").select("id, position, set_name, sentence, words").order("position"));
}

export async function myResults() {
  return check(await sb.rpc("my_results"));
}

export async function submitAnswer(questionId, subject, predicate) {
  return check(await sb.rpc("submit_answer", {
    p_question_id: questionId, p_subject: subject, p_predicate: predicate,
  }));
}

export async function isTeacher() {
  return check(await sb.rpc("is_teacher"));
}

export async function teacherData() {
  const [students, attempts, keys] = await Promise.all([
    sb.rpc("teacher_students"), sb.rpc("teacher_attempts"), sb.rpc("teacher_keys"),
  ]);
  return { students: check(students), attempts: check(attempts), keys: check(keys) };
}
