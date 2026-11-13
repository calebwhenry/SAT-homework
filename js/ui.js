// Small helpers shared by the student page modules.
export const $ = (id) => document.getElementById(id);

const SCREENS = ["loading", "auth", "profile", "menu", "practice", "mc", "trim", "done"];
const SCENIC = new Set(["auth", "profile", "menu", "done"]);
const calm = matchMedia("(prefers-reduced-motion: reduce)");

export function show(screen) {
  for (const s of SCREENS) if ($(s)) $(s).hidden = s !== screen;
  document.body.dataset.screen = screen;
  scene(SCENIC.has(screen));
}

// The dusk video plays only behind the scenic screens, and never under Reduce Motion.
function scene(on) {
  const v = $("ambient-video");
  if (!v) return;
  if (!v.dataset.wired) {
    v.dataset.wired = "1";
    v.addEventListener("playing", () => document.body.classList.add("scene-live"), { once: true });
  }
  if (on && !calm.matches) v.play().catch(() => {});
  else v.pause();
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
