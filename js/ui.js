// Small helpers shared by the student page modules.
export const $ = (id) => document.getElementById(id);

const SCREENS = ["loading", "auth", "profile", "menu", "practice", "mc", "done"];
export function show(screen) {
  for (const s of SCREENS) if ($(s)) $(s).hidden = s !== screen;
}

export function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

// Question text from the database may contain <i> for titles. Escape everything,
// then allow only <i>/</i> back, and draw "______" as a blank line.
export function richText(s) {
  return esc(s)
    .replace(/&lt;(\/?)i&gt;/g, "<$1i>")
    .replace(/_{3,}/g, '<span class="blank" aria-label="blank"></span>');
}

// Done screen shared by every set.
export function showDone({ title, score, detail, onReview }) {
  $("done-title").textContent = title;
  $("done-score").textContent = score;
  $("done-detail").textContent = detail;
  $("review").onclick = onReview;
  show("done");
}
