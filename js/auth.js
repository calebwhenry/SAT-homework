// Sign-in / create-account form shared by the student page and the teacher dashboard.
import * as api from "./api.js?v=20261106033338";

const $ = (id) => document.getElementById(id);

const MESSAGES = [
  [/invalid login credentials/i, "That email and password don't match. Check both, or create an account if you're new."],
  [/already registered|already exists/i, "That email already has an account. Use Sign in instead."],
  [/password should be at least/i, "Use a password with at least 6 characters."],
  [/rate limit/i, "Too many attempts in a short time. Wait a few minutes, then try again."],
  [/failed to fetch|network/i, "Can't reach the server. Check your internet connection and try again."],
];

function friendly(err) {
  const msg = err?.message || String(err);
  for (const [re, text] of MESSAGES) if (re.test(msg)) return text;
  return msg;
}

// Shows the form and resolves with { user, fullName } once someone is signed in.
// fullName is set only when they just created an account.
export function showAuth() {
  return new Promise((resolve) => {
    const form = $("auth-form"), err = $("auth-error"), btn = $("auth-submit");
    let mode = "signin";

    const setMode = (m) => {
      mode = m;
      document.querySelectorAll("#auth .tab").forEach((t) => t.setAttribute("aria-selected", String(t.dataset.mode === m)));
      $("name-field").hidden = m !== "signup";
      $("password").autocomplete = m === "signup" ? "new-password" : "current-password";
      btn.textContent = m === "signup" ? "Create account" : "Sign in";
      err.hidden = true;
    };
    document.querySelectorAll("#auth .tab").forEach((t) => (t.onclick = () => setMode(t.dataset.mode)));
    setMode("signin");

    form.onsubmit = async (e) => {
      e.preventDefault();
      err.hidden = true;
      const email = $("email").value.trim();
      const password = $("password").value;
      const fullName = $("name").value.trim();
      if (!email || !password) return show("Enter your email and password.");
      if (mode === "signup" && !fullName) return show("Enter your full name so your teacher knows who you are.");
      if (mode === "signup" && password.length < 6) return show("Use a password with at least 6 characters.");

      btn.disabled = true;
      try {
        if (mode === "signin") {
          resolve({ user: await api.signIn(email, password), fullName: null });
        } else {
          const user = await api.signUp(email, password);
          if (!user) return show("Your account was created, but it needs email confirmation before you can sign in. Ask your teacher to turn off email confirmation in Supabase.");
          resolve({ user, fullName });
        }
      } catch (e2) {
        show(friendly(e2));
      } finally {
        btn.disabled = false;
      }
    };

    function show(text) {
      err.textContent = text;
      err.hidden = false;
    }
  });
}
