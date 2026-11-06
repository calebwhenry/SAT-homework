// Teacher dashboard: class totals, per-student scores, most-missed questions.
import * as api from "./api.js";
import { showAuth } from "./auth.js";

const $ = (id) => document.getElementById(id);
const SCREENS = ["loading", "auth", "denied", "dash"];
const show = (s) => SCREENS.forEach((x) => ($(x).hidden = x !== s));

let data = null;
let openStudent = null;

const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const pct = (n, d) => (d ? Math.round((100 * n) / d) + "%" : "–");
const both = (a) => a.subject_correct && a.predicate_correct;

async function start() {
  show("loading");
  let user = await api.currentUser();
  if (!user) {
    show("auth");
    ({ user } = await showAuth());
    show("loading");
  }
  if (!(await api.isTeacher())) {
    $("denied-email").textContent = user.email;
    return show("denied");
  }
  await load();
  show("dash");
}

async function load() {
  $("refresh").disabled = true;
  try {
    data = await api.teacherData();
    render();
    $("updated").textContent = "Updated " + new Date().toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  } finally {
    $("refresh").disabled = false;
  }
}

function render() {
  const { students, attempts, keys } = data;
  const total = keys.length;
  const byStudent = new Map(students.map((s) => [s.user_id, []]));
  for (const a of attempts) if (byStudent.has(a.user_id)) byStudent.get(a.user_id).push(a);
  const studentAttempts = attempts.filter((a) => byStudent.has(a.user_id));

  // Totals
  const finished = students.filter((s) => byStudent.get(s.user_id).length === total).length;
  $("totals").innerHTML = [
    [students.length, "students signed up"],
    [finished, "finished all " + total],
    [studentAttempts.length, "answers submitted"],
    [pct(studentAttempts.filter(both).length, studentAttempts.length), "fully correct"],
  ].map(([n, l]) => `<div class="total"><span class="total-n">${n}</span><span class="total-l">${l}</span></div>`).join("");

  // Students
  const rows = students.map((s) => {
    const as = byStudent.get(s.user_id);
    const last = as.reduce((m, a) => (a.created_at > m ? a.created_at : m), "");
    return { s, as, last,
      subj: as.filter((a) => a.subject_correct).length,
      verb: as.filter((a) => a.predicate_correct).length,
      full: as.filter(both).length };
  });
  $("students").innerHTML = `
    <thead><tr><th>Student</th><th class="num">Answered</th><th class="num">Subject</th><th class="num">Verb</th><th class="num">Both right</th><th>Last active</th></tr></thead>
    <tbody>${rows.length ? rows.map((r) => `
      <tr class="clickable${openStudent === r.s.user_id ? " open" : ""}" data-id="${r.s.user_id}" tabindex="0">
        <td><div class="name">${esc(r.s.full_name)}</div><div class="muted-sm">${esc(r.s.email)}</div></td>
        <td class="num">${r.as.length} / ${total}</td>
        <td class="num">${pct(r.subj, r.as.length)}</td>
        <td class="num">${pct(r.verb, r.as.length)}</td>
        <td class="num"><b>${pct(r.full, r.as.length)}</b></td>
        <td>${r.last ? new Date(r.last).toLocaleString([], { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }) : "Not started"}</td>
      </tr>`).join("") : `<tr><td colspan="6" class="empty">No students yet. Share the practice page link so they can create accounts.</td></tr>`}
    </tbody>`;
  $("students").querySelectorAll("tr.clickable").forEach((tr) => {
    const open = () => { openStudent = openStudent === tr.dataset.id ? null : tr.dataset.id; render(); };
    tr.onclick = open;
    tr.onkeydown = (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); open(); } };
  });
  renderStudentDetail(rows.find((r) => r.s.user_id === openStudent), keys);

  // Questions
  const qrows = keys.map((k) => {
    const as = studentAttempts.filter((a) => a.question_id === k.question_id);
    const wrongS = topPick(as.filter((a) => !a.subject_correct).map((a) => a.subject_words));
    const wrongV = topPick(as.filter((a) => !a.predicate_correct).map((a) => a.predicate_words));
    return { k, n: as.length,
      sOk: as.filter((a) => a.subject_correct).length,
      vOk: as.filter((a) => a.predicate_correct).length,
      full: as.filter(both).length, wrongS, wrongV };
  }).sort((a, b) => (a.n ? a.full / a.n : 2) - (b.n ? b.full / b.n : 2) || b.n - a.n || a.k.q_position - b.k.q_position);

  $("questions").innerHTML = `
    <thead><tr><th class="num">#</th><th>Sentence and answer</th><th class="num">Answers</th><th class="num">Both right</th><th class="num">Subject</th><th class="num">Verb</th><th>Top wrong pick</th></tr></thead>
    <tbody>${qrows.map((r) => `
      <tr>
        <td class="num qnum">${r.k.q_position}</td>
        <td class="sent"><div>${esc(r.k.sentence)}</div>
          <div class="key"><span class="tag s">S</span> ${esc(r.k.subject_words)} <span class="tag v">V</span> ${esc(r.k.predicate_words)}</div></td>
        <td class="num">${r.n}</td>
        <td class="num">${bar(r.full, r.n)}</td>
        <td class="num">${pct(r.sOk, r.n)}</td>
        <td class="num">${pct(r.vOk, r.n)}</td>
        <td class="picks">${r.wrongS ? `<div><span class="tag s">S</span> ${esc(r.wrongS.word)} <span class="muted-sm">×${r.wrongS.count}</span></div>` : ""}
          ${r.wrongV ? `<div><span class="tag v">V</span> ${esc(r.wrongV.word)} <span class="muted-sm">×${r.wrongV.count}</span></div>` : ""}
          ${!r.wrongS && !r.wrongV ? `<span class="muted-sm">–</span>` : ""}</td>
      </tr>`).join("")}
    </tbody>`;
}

function renderStudentDetail(row, keys) {
  const box = $("student-detail");
  if (!row) { box.hidden = true; return; }
  const byQ = new Map(row.as.map((a) => [a.question_id, a]));
  const strip = keys.map((k) => {
    const a = byQ.get(k.question_id);
    const cls = !a ? "" : both(a) ? "right" : a.subject_correct || a.predicate_correct ? "half" : "wrong";
    return `<span class="seg ${cls}" title="Question ${k.q_position}"></span>`;
  }).join("");
  const misses = keys.filter((k) => byQ.has(k.question_id) && !both(byQ.get(k.question_id)));
  box.innerHTML = `
    <h3>${esc(row.s.full_name)}</h3>
    <div class="strip mini">${strip}</div>
    ${misses.length ? `<table class="misses">
      <thead><tr><th class="num">#</th><th>Sentence</th><th>Their pick</th><th>Answer</th></tr></thead>
      <tbody>${misses.map((k) => {
        const a = byQ.get(k.question_id);
        return `<tr><td class="num qnum">${k.q_position}</td><td class="sent">${esc(k.sentence)}</td>
          <td><div class="${a.subject_correct ? "" : "wrong-pick"}"><span class="tag s">S</span> ${esc(a.subject_words)}</div>
              <div class="${a.predicate_correct ? "" : "wrong-pick"}"><span class="tag v">V</span> ${esc(a.predicate_words)}</div></td>
          <td><div><span class="tag s">S</span> ${esc(k.subject_words)}</div><div><span class="tag v">V</span> ${esc(k.predicate_words)}</div></td></tr>`;
      }).join("")}</tbody></table>`
    : `<p class="muted-sm">${row.as.length ? "No misses so far." : "This student hasn't answered any questions yet."}</p>`}`;
  box.hidden = false;
}

function topPick(words) {
  const counts = new Map();
  for (const w of words) counts.set(w, (counts.get(w) || 0) + 1);
  let best = null;
  for (const [word, count] of counts) if (!best || count > best.count) best = { word, count };
  return best;
}

function bar(n, d) {
  if (!d) return `<span class="muted-sm">–</span>`;
  const p = Math.round((100 * n) / d);
  const color = p >= 80 ? "var(--ok)" : p >= 50 ? "var(--half)" : "var(--bad)";
  return `<span class="bar"><span style="width:${p}%;background:${color}"></span></span> ${p}%`;
}

$("refresh").onclick = load;
const out = async () => { await api.signOut(); location.reload(); };
$("dash-out").onclick = out;
$("denied-out").onclick = out;

start().catch((e) => {
  $("loading").innerHTML = `<p class="error">The dashboard couldn't load: ${esc(e.message)}. Refresh the page to try again.</p>`;
  show("loading");
});
