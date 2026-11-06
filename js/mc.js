// Multiple-choice practice (question-bank sets), one question at a time.
import * as api from "./api.js";
import { $, show, esc, richText, showDone } from "./ui.js";

const LETTERS = ["A", "B", "C", "D"];
const st = {
  set: null,
  questions: [],
  results: {},   // question id -> graded result
  picks: {},     // question id -> letter chosen but not yet submitted
  idx: 0,
  busy: false,
};

const cur = () => st.questions[st.idx];
const firstOpen = () => st.questions.findIndex((q) => !st.results[q.id]);

export async function openChoiceSet(set) {
  if (st.set?.id !== set.id) {
    const [questions, results] = await Promise.all([api.loadChoiceQuestions(set.id), api.myChoiceResults()]);
    st.set = set;
    st.questions = questions;
    st.results = {};
    st.picks = {};
    const ids = new Set(questions.map((q) => q.id));
    for (const r of results) if (ids.has(r.question_id)) st.results[r.question_id] = r;
    buildStrip();
  }
  $("mc-title").textContent = set.title;
  const open = firstOpen();
  if (open === -1) return finish();
  show("mc");
  goTo(open);
}

function buildStrip() {
  const strip = $("mc-strip");
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
  [...$("mc-strip").children].forEach((b, i) => {
    const r = st.results[st.questions[i].id];
    b.className = "seg" + (r ? (r.correct ? " right" : " wrong") : "") + (i === st.idx ? " here" : "");
    b.setAttribute("aria-current", i === st.idx ? "step" : "false");
  });
}

function goTo(i) {
  st.idx = Math.max(0, Math.min(st.questions.length - 1, i));
  render();
  $("mc-passage").scrollTop = 0;
  document.querySelector(".mc-right").scrollTop = 0;
}

function render() {
  const q = cur();
  const r = st.results[q.id];
  const pick = r ? r.choice : st.picks[q.id];

  $("mc-count").textContent = `Question ${st.idx + 1} of ${st.questions.length}`;
  $("mc-passage").innerHTML = q.passage
    .map((p) => `<p class="${/^©/.test(p) ? "credit" : ""}">${richText(p)}</p>`).join("");
  $("mc-stem").innerHTML = richText(q.stem);

  const box = $("mc-choices");
  box.innerHTML = "";
  for (const L of LETTERS) {
    if (!(L in q.choices)) continue;
    const b = document.createElement("button");
    b.type = "button";
    b.className = "choice";
    b.setAttribute("role", "radio");
    b.setAttribute("aria-checked", String(pick === L));
    b.innerHTML = `<span class="choice-letter">${L}</span><span class="choice-text">${richText(q.choices[L])}</span>`;
    if (r) {
      b.disabled = true;
      if (L === r.answer) b.classList.add("ok");
      else if (L === r.choice) b.classList.add("bad");
    } else {
      if (pick === L) b.classList.add("picked");
      b.onclick = () => { st.picks[q.id] = L; render(); };
    }
    box.appendChild(b);
  }

  const fb = $("mc-feedback");
  if (r) {
    fb.innerHTML = feedbackHtml(q, r);
    fb.hidden = false;
  } else {
    fb.hidden = true;
    fb.innerHTML = "";
  }

  $("mc-submit").hidden = !!r;
  $("mc-submit").disabled = st.busy || !pick;
  $("mc-back").disabled = st.idx === 0;
  $("mc-next").classList.toggle("primary", !!r);
  $("mc-next").textContent = st.idx === st.questions.length - 1 ? "Finish" : "Next";
  paintStrip();
}

// Wrong answer: why your choice is wrong, then why the answer is right, then the other two (folded).
// Right answer: why it's right, then the three wrong choices (folded).
function feedbackHtml(q, r) {
  const label = (L) => `${L} (${richText(q.choices[L] || "")})`;
  const head = `
    <div class="fb-row ${r.correct ? "is-ok" : "is-bad"}">
      <span class="fb-icon" aria-hidden="true">${r.correct ? "✓" : "✗"}</span>
      <span class="fb-text">${r.correct ? `Correct. The answer is <b>${r.answer}</b>.`
        : `You chose <b class="strike">${r.choice}</b>. The answer is <b>${r.answer}</b>.`}</span>
    </div>`;
  const wrong = r.why_wrong || {};
  if (!r.why_right || !Object.keys(wrong).length) {
    // Older format: show the explanation paragraphs as they are.
    const [why, ...others] = r.rationale || [];
    return head + (why ? `<p class="fb-why">${richText(why)}</p>` : "") +
      (others.length ? `<details class="fb-more"><summary>Why the other choices are wrong</summary>${others.map((p) => `<p class="fb-why">${richText(p)}</p>`).join("")}</details>` : "");
  }
  const section = (title, text, cls) => `<div class="fb-part ${cls}"><h4>${title}</h4><p class="fb-why">${richText(text)}</p></div>`;
  let html = head;
  if (!r.correct && wrong[r.choice]) html += section(`Why ${label(r.choice)} is wrong`, wrong[r.choice], "part-bad");
  html += section(`Why ${label(r.answer)} is right`, r.why_right, "part-ok");
  const rest = Object.keys(wrong).sort().filter((L) => L !== r.choice);
  if (rest.length) {
    html += `<details class="fb-more"><summary>Why ${rest.length === 3 ? "the other choices are" : rest.join(" and ") + " are"} wrong</summary>` +
      rest.map((L) => section(`Choice ${label(L)}`, wrong[L], "")).join("") + `</details>`;
  }
  return html;
}

async function submit() {
  const q = cur();
  const pick = st.picks[q.id];
  if (st.busy || st.results[q.id] || !pick) return;
  st.busy = true;
  $("mc-submit").disabled = true;
  $("mc-submit").textContent = "Checking…";
  try {
    st.results[q.id] = await api.submitChoice(q.id, pick);
  } catch (e) {
    const fb = $("mc-feedback");
    fb.innerHTML = `<p class="error">Your answer wasn't saved: ${esc(e.message)}. Check your connection and press Submit again.</p>`;
    fb.hidden = false;
  } finally {
    st.busy = false;
    $("mc-submit").textContent = "Submit";
  }
  if (st.results[q.id]) {
    render();
    if (window.matchMedia("(max-width: 860px)").matches) $("mc-feedback").scrollIntoView({ behavior: "smooth", block: "start" });
  } else $("mc-submit").disabled = false;
}

function next() {
  if (st.idx < st.questions.length - 1) return goTo(st.idx + 1);
  const open = firstOpen();
  if (open === -1) return finish();
  goTo(open);
}

function finish() {
  const rs = Object.values(st.results);
  const right = rs.filter((r) => r.correct).length;
  const n = st.questions.length;
  showDone({
    title: `${st.set.title}: all ${n} answered`,
    score: `${right} of ${n} correct`,
    detail: right === n ? "A perfect set." : `Review the ${n - right} you missed to see why the right answer works.`,
    onReview: () => { show("mc"); goTo(0); },
  });
}

$("mc-submit").onclick = submit;
$("mc-back").onclick = () => goTo(st.idx - 1);
$("mc-next").onclick = next;

document.addEventListener("keydown", (e) => {
  if ($("mc").hidden || e.target.closest("input, textarea, summary")) return;
  const q = cur();
  if (!q) return;
  const key = e.key.toUpperCase();
  if (LETTERS.includes(key) && !e.ctrlKey && !e.metaKey && !st.results[q.id] && key in q.choices) {
    st.picks[q.id] = key;
    render();
  } else if (e.key === "ArrowRight") next();
  else if (e.key === "ArrowLeft" && st.idx > 0) goTo(st.idx - 1);
  else if (e.key === "Enter" && !e.target.closest("button")) {
    e.preventDefault();
    if (st.results[q.id]) next();
    else if (st.picks[q.id]) submit();
  }
});
