// "Cross out, then find": step 1 cross out the extra information, step 2 pick the
// simple subject, step 3 pick the verb. Graded on the server when the student submits.
import * as api from "./api.js?v=20261113114913";
import { $, show, esc, showDone } from "./ui.js?v=20261113114913";

const STEPS = ["cut", "subject", "predicate"];
const st = {
  set: null,
  questions: [],
  results: {},   // question id -> graded result
  drafts: {},    // question id -> { cut: Set, s: Set, p: Set, step }
  idx: 0,
  busy: false,
  drag: null,    // { on: boolean } while dragging across words in step 1
};

const cur = () => st.questions[st.idx];
const firstOpen = () => st.questions.findIndex((q) => !st.results[q.id]);
const allRight = (r) => r.removal_correct && r.subject_correct && r.predicate_correct;

function splitWord(w) {
  const m = w.match(/^([^\p{L}\p{N}]*)(.*?)([^\p{L}\p{N}]*)$/u);
  return m && m[2] ? [m[1], m[2], m[3]] : ["", w, ""];
}
const core = (q, i) => splitWord(q.words[i])[1];
const wordsText = (q, idxs) => [...idxs].sort((a, b) => a - b).map((i) => core(q, i)).join(" ");

function draft(q) {
  if (!st.drafts[q.id]) st.drafts[q.id] = { cut: new Set(), s: new Set(), p: new Set(), step: "cut" };
  return st.drafts[q.id];
}

// The whole extra phrases (contiguous runs of the key) that still had a word left in.
function missedPhrases(q, extra, removed) {
  const runs = [];
  for (const i of [...extra].sort((a, b) => a - b)) {
    const last = runs[runs.length - 1];
    if (last && i === last[last.length - 1] + 1) last.push(i); else runs.push([i]);
  }
  return runs.filter((run) => run.some((i) => !removed.has(i)))
    .map((run) => run.map((i) => q.words[i]).join(" ").replace(/[,.;:]+$/, ""));
}

export async function openTrimSet(set) {
  if (st.set?.id !== set.id) {
    const [questions, results] = await Promise.all([api.loadTrimQuestions(set.id), api.myTrimResults()]);
    st.set = set;
    st.questions = questions;
    st.results = {};
    st.drafts = {};
    const ids = new Set(questions.map((q) => q.id));
    for (const r of results) if (ids.has(r.question_id)) st.results[r.question_id] = r;
    buildStrip();
  }
  $("trim-title").textContent = set.title;
  const open = firstOpen();
  if (open === -1) return finish();
  show("trim");
  goTo(open);
}

function buildStrip() {
  const strip = $("trim-strip");
  strip.innerHTML = "";
  st.questions.forEach((q, i) => {
    const b = document.createElement("button");
    b.className = "seg";
    b.setAttribute("aria-label", `Question ${i + 1}`);
    b.title = `Question ${i + 1}`;
    b.onclick = () => goTo(i);
    strip.appendChild(b);
  });
}

function paintStrip() {
  [...$("trim-strip").children].forEach((b, i) => {
    const r = st.results[st.questions[i].id];
    const n = r ? [r.removal_correct, r.subject_correct, r.predicate_correct].filter(Boolean).length : 0;
    b.className = "seg" + (r ? (n === 3 ? " right" : n === 0 ? " wrong" : " half") : "") + (i === st.idx ? " here" : "");
    b.setAttribute("aria-current", i === st.idx ? "step" : "false");
  });
}

function goTo(i) {
  st.idx = Math.max(0, Math.min(st.questions.length - 1, i));
  render();
}

function render() {
  const q = cur();
  const d = draft(q);
  const r = st.results[q.id];
  const cut = r ? new Set(r.removed_sel) : d.cut;
  const sPick = r ? r.subject_sel : [...d.s];
  const pPick = r ? r.predicate_sel : [...d.p];

  $("trim-count").textContent = `Question ${st.idx + 1} of ${st.questions.length}`;

  // Step chips
  const chip = (id, step, picked, text, empty) => {
    $(id).classList.toggle("active", !r && d.step === step);
    $(id).classList.toggle("filled", picked);
    $(id).disabled = !!r;
    $(id).querySelector(".step-pick").textContent = picked ? text : empty;
  };
  chip("trim-step-x", "cut", cut.size > 0, `${cut.size} word${cut.size === 1 ? "" : "s"} crossed out`, "Click or drag across words");
  chip("trim-step-s", "subject", sPick.length > 0, wordsText(q, sPick), "Click a word");
  chip("trim-step-p", "predicate", pPick.length > 0, wordsText(q, pPick), "Click a word");

  $("trim-prompt").textContent = r ? "" : {
    cut: d.cut.size
      ? "Keep going until only the core of the sentence is left. Click a crossed-out word to bring it back."
      : "Cross out the extra information: prepositional phrases, interrupters, and describing phrases. Click a word, or drag across a phrase.",
    subject: d.s.size ? "Compound subject? Click each part. Otherwise, continue to the verb."
      : "Now click the simple subject in what's left.",
    predicate: d.p.size ? "Include every helping verb, then submit."
      : "Now click the verb. Include helping verbs like has, was, or will.",
  }[d.step];

  renderSentence(q, d, r);
  renderFeedback(q, r);

  $("trim-continue").hidden = !!r || d.step === "predicate" || (d.step === "cut" ? d.cut.size === 0 : d.s.size === 0);
  $("trim-continue").textContent = d.step === "cut" ? "Done crossing out" : "Continue to verb";
  $("trim-submit").hidden = !!r || !$("trim-continue").hidden;
  $("trim-submit").disabled = st.busy || d.s.size === 0 || d.p.size === 0;
  $("trim-back").disabled = st.idx === 0;
  $("trim-next").classList.toggle("primary", !!r);
  $("trim-next").textContent = st.idx === st.questions.length - 1 ? "Finish" : "Next";
  paintStrip();
  fit();
}

function renderSentence(q, d, r) {
  const box = $("trim-sentence");
  box.innerHTML = "";
  box.dataset.mode = r ? "graded" : d.step;
  const collapse = !r && d.step !== "cut";

  const key = r ? {
    extra: new Set(r.extra_idx), s: new Set(r.subject_idx), p: new Set(r.predicate_idx),
  } : null;
  const cut = r ? new Set(r.removed_sel) : d.cut;
  const selS = new Set(r ? r.subject_sel : d.s), selP = new Set(r ? r.predicate_sel : d.p);

  let prevGone = false;
  q.words.forEach((w, i) => {
    const gone = collapse && cut.has(i);
    if (gone) {
      if (!prevGone) { const g = document.createElement("span"); g.className = "gap"; g.textContent = "…"; box.append(" ", g); }
      prevGone = true;
      return;
    }
    prevGone = false;
    const [lead, text, trail] = splitWord(w);
    if (box.childNodes.length) box.append(" ");
    const span = document.createElement("span");
    span.className = "token";
    if (lead) span.append(lead);
    const b = document.createElement("button");
    b.className = "w";
    b.type = "button";
    b.textContent = text;
    b.dataset.i = i;

    if (!r) {
      if (d.step === "cut") {
        if (cut.has(i)) b.classList.add("cut");
        b.setAttribute("aria-pressed", String(cut.has(i)));
        b.setAttribute("aria-label", `${text}${cut.has(i) ? ", crossed out" : ""}`);
      } else {
        if (selS.has(i)) b.classList.add("sel-s");
        if (selP.has(i)) b.classList.add("sel-p");
        b.setAttribute("aria-pressed", String(selS.has(i) || selP.has(i)));
        b.onclick = () => pick(i);
      }
    } else {
      b.tabIndex = -1;
      b.disabled = true;
      // Crossing out first, then subject/verb marks on top
      if (key.extra.has(i)) b.classList.add(cut.has(i) ? "cut-ok" : "cut-missed");
      else if (cut.has(i)) b.classList.add(key.s.has(i) || key.p.has(i) ? "bad" : "cut-ok");
      const mark = (sel, k, tag) => {
        if (sel.has(i) && k.has(i)) { b.classList.add("ok"); b.dataset.tag = tag; }
        else if (sel.has(i)) { b.classList.add("bad"); b.dataset.tag = tag; }
        else if (k.has(i)) { b.classList.add("miss"); b.dataset.tag = tag; }
      };
      mark(selS, key.s, "S");
      if (!b.dataset.tag) mark(selP, key.p, "V");
    }
    span.append(b);
    if (trail) span.append(trail);
    box.append(span);
  });
}

function renderFeedback(q, r) {
  const fb = $("trim-feedback");
  if (!r) { fb.hidden = true; fb.innerHTML = ""; return; }
  const removed = new Set(r.removed_sel);
  const missed = r.extra_idx.filter((i) => !removed.has(i));
  const cutCore = [...r.subject_idx, ...r.predicate_idx].filter((i) => removed.has(i));
  const cutText = r.removal_correct ? "You removed all the extra information."
    : [missed.length ? `Still needed crossing out: ${missedPhrases(q, r.extra_idx, removed).map((p) => `<b>“${esc(p)}”</b>`).join(", ")}.` : "",
       cutCore.length ? `Keep the core words: you crossed out <b class="strike">${esc(wordsText(q, cutCore))}</b>.` : ""].join(" ");
  const row = (label, ok, text) => `
    <div class="fb-row ${ok ? "is-ok" : "is-bad"}">
      <span class="fb-icon" aria-hidden="true">${ok ? "✓" : "✗"}</span>
      <span class="fb-label">${label}</span>
      <span class="fb-text">${text}</span>
    </div>`;
  const pickText = (ok, sel, key) => ok ? `Correct: <b>${esc(wordsText(q, key))}</b>`
    : `You chose <b class="strike">${esc(wordsText(q, sel))}</b>. Answer: <b>${esc(wordsText(q, key))}</b>`;
  fb.innerHTML =
    row("Cross out", r.removal_correct, cutText) +
    row("Subject", r.subject_correct, pickText(r.subject_correct, r.subject_sel, r.subject_idx)) +
    row("Verb", r.predicate_correct, pickText(r.predicate_correct, r.predicate_sel, r.predicate_idx)) +
    `<p class="fb-trimmed"><span>Trimmed:</span>${esc(r.trimmed)}</p>` +
    `<p class="fb-why">${esc(r.explanation)}</p>`;
  fb.hidden = false;
}

// ---------- interaction ----------

function setCut(i, on) {
  const d = draft(cur());
  const had = d.cut.has(i);
  if (on === had) return;
  on ? d.cut.add(i) : d.cut.delete(i);
  d.s.delete(i); d.p.delete(i);
  const b = $("trim-sentence").querySelector(`.w[data-i="${i}"]`);
  if (b) {
    b.classList.toggle("cut", on);
    b.classList.toggle("fresh", on);
    b.setAttribute("aria-pressed", String(on));
  }
}

// Click a word to cross it out (or bring it back); drag to do a whole phrase.
const sentenceEl = $("trim-sentence");
sentenceEl.addEventListener("pointerdown", (e) => {
  const b = e.target.closest(".w");
  const q = cur();
  if (!b || !q || st.results[q.id] || draft(q).step !== "cut") return;
  e.preventDefault();
  const i = +b.dataset.i;
  st.drag = { on: !draft(q).cut.has(i) };
  setCut(i, st.drag.on);
  sentenceEl.setPointerCapture?.(e.pointerId);
});
sentenceEl.addEventListener("pointermove", (e) => {
  if (!st.drag) return;
  const el = document.elementFromPoint(e.clientX, e.clientY);
  const b = el && el.closest && el.closest("#trim-sentence .w");
  if (b) setCut(+b.dataset.i, st.drag.on);
});
const endDrag = () => { if (st.drag) { st.drag = null; render(); } };
sentenceEl.addEventListener("pointerup", endDrag);
sentenceEl.addEventListener("pointercancel", endDrag);
// Keyboard: Space/Enter on a focused word toggles it in step 1
sentenceEl.addEventListener("keydown", (e) => {
  const b = e.target.closest(".w");
  const q = cur();
  if (!b || st.results[q.id] || draft(q).step !== "cut" || (e.key !== " " && e.key !== "Enter")) return;
  e.preventDefault(); e.stopPropagation();
  const i = +b.dataset.i;
  setCut(i, !draft(q).cut.has(i));
  render();
  $("trim-sentence").querySelector(`.w[data-i="${i}"]`)?.focus();
});

function pick(i) {
  const q = cur(), d = draft(q);
  if (st.results[q.id] || d.step === "cut") return;
  const mine = d.step === "subject" ? d.s : d.p;
  const other = d.step === "subject" ? d.p : d.s;
  other.delete(i);
  mine.has(i) ? mine.delete(i) : mine.add(i);
  render();
}

function setStep(step) {
  const q = cur();
  if (st.results[q.id]) return;
  const d = draft(q);
  if (d.step === "cut" && step !== "cut" && d.cut.size) {
    // Let the crossed-out words fade out before they leave the sentence
    $("trim-sentence").querySelectorAll(".w.cut").forEach((b) => b.classList.add("leaving"));
    d.step = step;
    setTimeout(render, window.matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : 200);
    return;
  }
  d.step = step;
  render();
}

function advance() {
  const d = draft(cur());
  setStep(STEPS[Math.min(STEPS.indexOf(d.step) + 1, 2)]);
}

async function submit() {
  const q = cur(), d = draft(q);
  if (st.busy || st.results[q.id] || !d.s.size || !d.p.size) return;
  st.busy = true;
  $("trim-submit").disabled = true;
  $("trim-submit").textContent = "Checking…";
  const sort = (x) => [...x].sort((a, b) => a - b);
  try {
    st.results[q.id] = await api.submitTrim(q.id, sort(d.cut), sort(d.s), sort(d.p));
  } catch (e) {
    const fb = $("trim-feedback");
    fb.innerHTML = `<p class="error">Your answer wasn't saved: ${esc(e.message)}. Check your connection and press Submit again.</p>`;
    fb.hidden = false;
  } finally {
    st.busy = false;
    $("trim-submit").textContent = "Submit";
  }
  if (st.results[q.id]) render();
  else $("trim-submit").disabled = false;
}

function next() {
  if (st.idx < st.questions.length - 1) return goTo(st.idx + 1);
  const open = firstOpen();
  if (open === -1) return finish();
  goTo(open);
}

function finish() {
  const rs = Object.values(st.results);
  const n = st.questions.length;
  const count = (f) => rs.filter(f).length;
  showDone({
    title: `${st.set.title}: all ${n} answered`,
    score: `${count(allRight)} of ${n} fully correct`,
    detail: `Crossing out: ${count((r) => r.removal_correct)} of ${n}. Subjects: ${count((r) => r.subject_correct)} of ${n}. Verbs: ${count((r) => r.predicate_correct)} of ${n}.`,
    onReview: () => { show("trim"); goTo(0); },
  });
}

// Start large, then shrink until the question (sentence + feedback) fits without scrolling.
function fit() {
  const q = cur();
  if (!q || $("trim").hidden) return;
  const box = $("trim-sentence"), sheet = box.closest(".sheet");
  const len = q.sentence.length;
  const ideal = len <= 60 ? 42 : len <= 110 ? 35 : len <= 145 ? 31 : 28;
  let fs = Math.min(ideal, Math.max(18, window.innerWidth * 0.062));
  box.style.setProperty("--fs", fs + "px");
  while (fs > 16 && sheet.scrollHeight > sheet.clientHeight) {
    fs -= 1;
    box.style.setProperty("--fs", fs + "px");
  }
}
window.addEventListener("resize", fit);
document.fonts?.ready.then(fit);

$("trim-step-x").onclick = () => setStep("cut");
$("trim-step-s").onclick = () => setStep("subject");
$("trim-step-p").onclick = () => setStep("predicate");
$("trim-continue").onclick = advance;
$("trim-submit").onclick = submit;
$("trim-back").onclick = () => goTo(st.idx - 1);
$("trim-next").onclick = next;

document.addEventListener("keydown", (e) => {
  if ($("trim").hidden || e.target.closest("input, textarea")) return;
  const q = cur();
  if (!q) return;
  if (e.key === "ArrowRight") next();
  else if (e.key === "ArrowLeft" && st.idx > 0) goTo(st.idx - 1);
  else if (e.key === "Enter" && !e.target.closest("button")) {
    e.preventDefault();
    if (st.results[q.id]) next();
    else if (!$("trim-continue").hidden) advance();
    else if (!$("trim-submit").hidden && !$("trim-submit").disabled) submit();
  }
});
