// Student page: sign-in, set menu, and the subject/verb practice.
import * as api from "./api.js?v=20261113114913";
import { showAuth } from "./auth.js?v=20261113114913";
import { $, show, esc, showDone as showDoneScreen } from "./ui.js?v=20261113114913";
import { openTrimSet } from "./trim.js?v=20261113114913";
import { openChoiceSet } from "./mc.js?v=20261113114913";

const state = {
  questions: [],
  results: {},   // question id -> graded result from the server
  drafts: {},    // question id -> { s: Set, p: Set, step }
  idx: 0,
  busy: false,
  loaded: false,
};
let sets = [];

// Split a word into leading punctuation, the clickable core, and trailing punctuation.
function splitWord(w) {
  const m = w.match(/^([^\p{L}\p{N}]*)(.*?)([^\p{L}\p{N}]*)$/u);
  return m && m[2] ? [m[1], m[2], m[3]] : ["", w, ""];
}
const core = (q, i) => splitWord(q.words[i])[1];
const wordsText = (q, idxs) => [...idxs].sort((a, b) => a - b).map((i) => core(q, i)).join(" ");

function draft(q) {
  if (!state.drafts[q.id]) state.drafts[q.id] = { s: new Set(), p: new Set(), step: "subject" };
  return state.drafts[q.id];
}

const current = () => state.questions[state.idx];
const answeredCount = () => state.questions.filter((q) => state.results[q.id]).length;
const firstUnanswered = () => state.questions.findIndex((q) => !state.results[q.id]);

// ---------- startup ----------

async function start() {
  show("loading");
  let user = await api.currentUser();
  let fullName = null;
  if (!user) {
    show("auth");
    ({ user, fullName } = await showAuth());
    show("loading");
  }

  let profile = await api.getProfile(user.id);
  if (!profile && fullName) {
    await api.createProfile(user.id, fullName);
    profile = { full_name: fullName };
  }
  if (!profile) profile = { full_name: await askName(user.id) };
  document.querySelectorAll(".who-name").forEach((el) => (el.textContent = profile.full_name));
  const first = profile.full_name.trim().split(/\s+/)[0];
  $("hello").textContent = first ? `Hi, ${first}` : "Your homework";

  sets = await api.loadSets();
  window.addEventListener("hashchange", route);
  await route();
}

// #subject-verb, #<multiple-choice set id>, or the menu
async function route() {
  const id = decodeURIComponent(location.hash.slice(1));
  const set = sets.find((x) => x.id === id);
  if (!set) return showMenu();
  show("loading");
  if (set.kind === "subject_verb") return openSubjectVerb();
  if (set.kind === "trim_subject_verb") return openTrimSet(set);
  return openChoiceSet(set);
}

const ICONS = {
  // cursor-in-text: pick words in a sentence
  subject_verb: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h9M4 12h6M4 17h9"/><path d="M17 5v14M15 5h4M15 19h4"/></svg>',
  // open book: reading passages
  multiple_choice: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 6.5C10 5 7.5 4.5 4 4.8v13.4c3.5-.3 6 .2 8 1.8 2-1.6 4.5-2.1 8-1.8V4.8c-3.5-.3-6 .2-8 1.7Z"/><path d="M12 6.5V20"/></svg>',
  // struck-through lines: cross out, then find
  trim_subject_verb: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M4 17h7"/><path d="M3 12h18" stroke-width="2.4"/><path d="M15 17h5"/></svg>',
};

function ring(answered, total) {
  const r = 14, c = 2 * Math.PI * r, f = total ? answered / total : 0;
  return `<svg class="ring${total && answered >= total ? " complete" : ""}" viewBox="0 0 34 34" aria-hidden="true">
    <circle class="track" cx="17" cy="17" r="${r}"/>
    <circle class="fill" cx="17" cy="17" r="${r}" stroke-dasharray="${c.toFixed(2)}" stroke-dashoffset="${(c * (1 - f)).toFixed(2)}"/></svg>`;
}

async function showMenu() {
  show("loading");
  const [svResults, index, choiceResults, trimIndex, trimResults] = await Promise.all([
    api.myResults(), api.choiceQuestionIndex(), api.myChoiceResults(), api.trimQuestionIndex(), api.myTrimResults(),
  ]);
  const choiceDone = new Map(choiceResults.map((r) => [r.question_id, r]));
  const trimDone = new Map(trimResults.map((r) => [r.question_id, r]));

  const progress = (set) => {
    if (set.kind === "subject_verb") {
      return { total: state.questions.length || 55, answered: svResults.length,
               right: svResults.filter((r) => r.subject_correct && r.predicate_correct).length };
    }
    const [idx, done, ok] = set.kind === "trim_subject_verb"
      ? [trimIndex, trimDone, (r) => r.removal_correct && r.subject_correct && r.predicate_correct]
      : [index, choiceDone, (r) => r.correct];
    const rs = idx.filter((q) => q.set_id === set.id).map((q) => done.get(q.id));
    return { total: rs.length, answered: rs.filter(Boolean).length, right: rs.filter((r) => r && ok(r)).length };
  };

  const weeks = [...new Set(sets.map((x) => x.homework))].sort((a, b) => b - a);
  const list = $("set-list");
  list.innerHTML = "";
  let i = 0;
  weeks.forEach((hw, w) => {
    const sec = document.createElement("section");
    sec.className = "homework rise";
    sec.style.setProperty("--i", i++);
    sec.innerHTML = `<div class="homework-head"><h2>Homework ${hw}</h2>${w === 0 ? '<span class="chip-now">This week</span>' : ""}</div>
      <div class="list-group"></div>`;
    const group = sec.querySelector(".list-group");
    for (const set of sets.filter((x) => x.homework === hw).sort((a, b) => a.position - b.position)) {
      const { total, answered, right } = progress(set);
      const meta = answered === 0 ? `${total} questions`
        : answered >= total ? `Finished: ${right} of ${total} right`
        : `${answered} of ${total} answered, ${right} right`;
      const a = document.createElement("a");
      a.className = "set-row";
      a.href = "#" + encodeURIComponent(set.id);
      a.innerHTML = `
        <span class="set-icon">${ICONS[set.kind] || ICONS.subject_verb}</span>
        <span class="set-text"><span class="set-name">${esc(set.title)}</span>
          ${set.blurb ? `<span class="set-blurb">${esc(set.blurb)}</span>` : ""}
          <span class="set-meta${answered && answered >= total ? " done" : ""}">${meta}</span></span>
        ${ring(answered, total)}
        <svg class="chev" viewBox="0 0 14 14" aria-hidden="true"><path d="m5 2.5 4.5 4.5L5 11.5"/></svg>`;
      group.appendChild(a);
    }
    list.appendChild(sec);
  });
  // Up next: the first unfinished set in the newest homework, then older ones
  const next = weeks.flatMap((hw) => sets.filter((x) => x.homework === hw).sort((a, b) => a.position - b.position))
    .find((set) => { const p = progress(set); return p.answered < p.total; });
  const btn = $("up-next");
  btn.hidden = false;
  if (next) {
    const p = progress(next);
    btn.classList.remove("caught-up");
    btn.href = "#" + encodeURIComponent(next.id);
    btn.innerHTML = `${p.answered ? "Continue" : "Start"} ${esc(next.title)} <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M7.5 4.5 13 10l-5.5 5.5"/></svg>`;
  } else {
    btn.classList.add("caught-up");
    btn.removeAttribute("href");
    btn.textContent = "All caught up. Nice work.";
  }
  btn.classList.add("rise");
  show("menu");
  window.LiquidGlassRefraction?.refresh();
}

async function openSubjectVerb() {
  if (!state.loaded) {
    const [questions, results] = await Promise.all([api.loadQuestions(), api.myResults()]);
    state.questions = questions;
    for (const r of results) state.results[r.question_id] = r;
    buildStrip();
    state.loaded = true;
  }
  const next = firstUnanswered();
  if (next === -1) return showDone();
  show("practice");
  goTo(next);
}

function askName(userId) {
  show("profile");
  return new Promise((resolve) => {
    $("profile-form").onsubmit = async (e) => {
      e.preventDefault();
      const name = $("profile-name").value.trim();
      const err = $("profile-error");
      if (!name) { err.textContent = "Enter your full name."; err.hidden = false; return; }
      try {
        await api.createProfile(userId, name);
        resolve(name);
      } catch (e2) {
        err.textContent = e2.message;
        err.hidden = false;
      }
    };
  });
}

// ---------- rendering ----------

function buildStrip() {
  const strip = $("strip");
  strip.innerHTML = "";
  state.questions.forEach((q, i) => {
    const b = document.createElement("button");
    b.className = "seg";
    b.title = `Question ${i + 1}`;
    b.setAttribute("aria-label", `Question ${i + 1}`);
    b.onclick = () => goTo(i);
    strip.appendChild(b);
  });
}

function paintStrip() {
  [...$("strip").children].forEach((b, i) => {
    const r = state.results[state.questions[i].id];
    b.className = "seg" +
      (r ? (r.subject_correct && r.predicate_correct ? " right" : r.subject_correct || r.predicate_correct ? " half" : " wrong") : "") +
      (i === state.idx ? " here" : "");
    b.setAttribute("aria-current", i === state.idx ? "step" : "false");
  });
}

function goTo(i) {
  state.idx = Math.max(0, Math.min(state.questions.length - 1, i));
  render();
}

function render() {
  const q = current();
  const d = draft(q);
  const r = state.results[q.id];

  $("q-count").textContent = `Question ${state.idx + 1} of ${state.questions.length}`;
  $("q-set").textContent = "Subject & Verb";

  // Step chips
  const sPick = r ? r.subject_sel : [...d.s];
  const pPick = r ? r.predicate_sel : [...d.p];
  $("pick-s").textContent = sPick.length ? wordsText(q, sPick) : "Click a word";
  $("pick-p").textContent = pPick.length ? wordsText(q, pPick) : "Click a word";
  $("step-s").classList.toggle("active", !r && d.step === "subject");
  $("step-p").classList.toggle("active", !r && d.step === "predicate");
  $("step-s").classList.toggle("filled", sPick.length > 0);
  $("step-p").classList.toggle("filled", pPick.length > 0);
  $("step-s").disabled = $("step-p").disabled = !!r;

  // Prompt
  $("prompt").textContent = r ? "" :
    d.step === "subject"
      ? (d.s.size ? "If the subject is compound, click each part. Otherwise, continue to the verb."
                  : "Click the simple subject: the core noun or pronoun the sentence is about.")
      : (d.p.size ? "Include every helping verb, then submit. To change the subject, click step 1."
                  : "Now click the verb. Include any helping verbs, like has, been, or will.");

  renderSentence(q, d, r);
  renderFeedback(q, r);

  // Controls
  $("continue").hidden = !!r || d.step !== "subject" || d.s.size === 0;
  $("submit").hidden = !!r || !$("continue").hidden;
  $("submit").disabled = state.busy || d.s.size === 0 || d.p.size === 0;
  $("back").disabled = state.idx === 0;
  $("next").classList.toggle("primary", !!r);
  $("next").textContent = state.idx === state.questions.length - 1 ? "Finish" : "Next";

  paintStrip();
  fitSentence();
}

function renderSentence(q, d, r) {
  const box = $("sentence");
  box.innerHTML = "";
  box.dataset.mode = r ? "graded" : d.step;

  const keyS = new Set(r?.subject_idx ?? []), keyP = new Set(r?.predicate_idx ?? []);
  const selS = new Set(r ? r.subject_sel : d.s), selP = new Set(r ? r.predicate_sel : d.p);

  q.words.forEach((w, i) => {
    const [lead, text, trail] = splitWord(w);
    if (i > 0) box.append(" ");
    const span = document.createElement("span");
    span.className = "token";
    if (lead) span.append(lead);

    const b = document.createElement("button");
    b.className = "w";
    b.textContent = text;
    b.type = "button";

    if (!r) {
      if (selS.has(i)) b.classList.add("sel-s");
      if (selP.has(i)) b.classList.add("sel-p");
      b.setAttribute("aria-pressed", String(selS.has(i) || selP.has(i)));
      b.onclick = () => pick(i);
    } else {
      b.tabIndex = -1;
      b.disabled = true;
      const mark = (sel, key, tag) => {
        if (sel.has(i) && key.has(i)) { b.classList.add("ok"); b.dataset.tag = tag; }
        else if (sel.has(i)) { b.classList.add("bad"); b.dataset.tag = tag; }
        else if (key.has(i)) { b.classList.add("miss"); b.dataset.tag = tag; }
      };
      mark(selS, keyS, "S");
      if (!b.dataset.tag) mark(selP, keyP, "V");
    }
    span.append(b);
    if (trail) span.append(trail);
    box.append(span);
  });
}

// Start from a size suited to the sentence length and screen width, then shrink
// until the whole question (sentence + feedback) fits without scrolling.
function fitSentence() {
  const q = current();
  if (!q || $("practice").hidden) return;
  const box = $("sentence"), sheet = box.closest(".sheet");
  const len = q.sentence.length;
  const ideal = len <= 60 ? 42 : len <= 110 ? 35 : len <= 145 ? 31 : 28;
  let fs = Math.min(ideal, Math.max(18, window.innerWidth * 0.062));
  box.style.setProperty("--fs", fs + "px");
  while (fs > 16 && sheet.scrollHeight > sheet.clientHeight) {
    fs -= 1;
    box.style.setProperty("--fs", fs + "px");
  }
}
window.addEventListener("resize", fitSentence);
document.fonts?.ready.then(fitSentence);

function renderFeedback(q, r) {
  const fb = $("feedback");
  if (!r) { fb.hidden = true; fb.innerHTML = ""; return; }
  const row = (label, ok, sel, key) => `
    <div class="fb-row ${ok ? "is-ok" : "is-bad"}">
      <span class="fb-icon" aria-hidden="true">${ok ? "✓" : "✗"}</span>
      <span class="fb-label">${label}</span>
      <span class="fb-text">${ok
        ? `Correct: <b>${esc(wordsText(q, key))}</b>`
        : `You chose <b class="strike">${esc(wordsText(q, sel))}</b>. Answer: <b>${esc(wordsText(q, key))}</b>`}</span>
    </div>`;
  fb.innerHTML =
    row("Subject", r.subject_correct, r.subject_sel, r.subject_idx) +
    row("Verb", r.predicate_correct, r.predicate_sel, r.predicate_idx) +
    `<p class="fb-why">${esc(r.explanation)}</p>`;
  fb.hidden = false;
}

// ---------- interaction ----------

function pick(i) {
  const q = current(), d = draft(q);
  if (state.results[q.id]) return;
  const mine = d.step === "subject" ? d.s : d.p;
  const other = d.step === "subject" ? d.p : d.s;
  other.delete(i);
  mine.has(i) ? mine.delete(i) : mine.add(i);
  render();
}

function setStep(step) {
  const q = current();
  if (state.results[q.id]) return;
  draft(q).step = step;
  render();
}

async function submit() {
  const q = current(), d = draft(q);
  if (state.busy || state.results[q.id] || !d.s.size || !d.p.size) return;
  state.busy = true;
  $("submit").disabled = true;
  $("submit").textContent = "Checking…";
  try {
    state.results[q.id] = await api.submitAnswer(q.id, [...d.s].sort((a, b) => a - b), [...d.p].sort((a, b) => a - b));
  } catch (e) {
    const fb = $("feedback");
    fb.innerHTML = `<p class="error">Your answer wasn't saved: ${esc(e.message)}. Check your connection and press Submit again.</p>`;
    fb.hidden = false;
  } finally {
    state.busy = false;
    $("submit").textContent = "Submit";
  }
  if (state.results[q.id]) render();
  else $("submit").disabled = false;
}

function next() {
  if (state.idx < state.questions.length - 1) return goTo(state.idx + 1);
  const open = firstUnanswered();
  if (open === -1) return showDone();
  goTo(open);
}

function showDone() {
  const rs = state.questions.map((q) => state.results[q.id]).filter(Boolean);
  const both = rs.filter((r) => r.subject_correct && r.predicate_correct).length;
  const subj = rs.filter((r) => r.subject_correct).length;
  const verb = rs.filter((r) => r.predicate_correct).length;
  const n = state.questions.length;
  showDoneScreen({
    title: "Subject & Verb: all " + n + " answered",
    score: `${both} of ${n} fully correct`,
    detail: `Subjects: ${subj} of ${n}. Verbs: ${verb} of ${n}.`,
    onReview: () => { show("practice"); goTo(0); },
  });
}

$("step-s").onclick = () => setStep("subject");
$("step-p").onclick = () => setStep("predicate");
$("continue").onclick = () => setStep("predicate");
$("submit").onclick = submit;
$("back").onclick = () => goTo(state.idx - 1);
$("next").onclick = next;
document.querySelectorAll(".sign-out").forEach((b) => (b.onclick = async () => { await api.signOut(); location.hash = ""; location.reload(); }));
document.querySelectorAll(".back-menu").forEach((b) => (b.onclick = () => {
  if (location.hash) location.hash = ""; else showMenu();
}));

document.addEventListener("keydown", (e) => {
  if ($("practice").hidden || e.target.closest("input, textarea")) return;
  if (e.key === "ArrowRight") next();
  else if (e.key === "ArrowLeft" && state.idx > 0) goTo(state.idx - 1);
  else if (e.key === "Enter" && !e.target.closest("button")) {
    if (state.results[current().id]) { e.preventDefault(); next(); }
    else if (!$("continue").hidden) setStep("predicate");
    else if (!$("submit").hidden && !$("submit").disabled) submit();
  }
});

start().catch((e) => {
  $("loading").innerHTML = `<p class="error">Something went wrong loading the practice: ${esc(e.message)}. Refresh the page to try again.</p>`;
  show("loading");
});
