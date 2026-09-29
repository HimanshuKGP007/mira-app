import { useEffect, useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { api, enterApp } from '../lib/api.js';
import Mira from './Mira.jsx';

/* Sign up / sign in / pick-a-child, ported field-for-field from the old
   landing.js overlay. Same endpoints, same required fields — server/auth.py
   is not touched, so the contract here must match it exactly:
     signup: { email, password, consent_service (required), consent_training }
     login:  { email, password }
     children: GET list / POST { name, age_years } */
export default function AuthOverlay({ open, initialTab = 'signup', onClose }) {
  const [tab, setTab] = useState(initialTab);
  const [step, setStep] = useState('auth'); // 'auth' | 'children'
  const [children, setChildren] = useState([]);
  const [busy, setBusy] = useState(false);

  const [signupForm, setSignupForm] = useState({ email: '', password: '', consentService: false, consentTraining: false });
  const [signinForm, setSigninForm] = useState({ email: '', password: '' });
  const [addChildForm, setAddChildForm] = useState({ name: '', age: '' });
  const [err, setErr] = useState('');

  useEffect(() => {
    if (!open) return;
    setTab(initialTab);
    setErr('');
    api.me().then((me) => { if (me.signed_in) afterSignedIn(me); }).catch(() => {});
  }, [open, initialTab]);

  async function afterSignedIn(me) {
    const info = me || await api.me();
    setChildren(info.children || []);
    setStep('children');
  }

  async function handleSignup(e) {
    e.preventDefault();
    setErr(''); setBusy(true);
    try {
      await api.signup(signupForm.email, signupForm.password, signupForm.consentService, signupForm.consentTraining);
      await afterSignedIn();
    } catch (ex) { setErr(ex.message); } finally { setBusy(false); }
  }

  async function handleSignin(e) {
    e.preventDefault();
    setErr(''); setBusy(true);
    try {
      await api.login(signinForm.email, signinForm.password);
      await afterSignedIn();
    } catch (ex) { setErr(ex.message); } finally { setBusy(false); }
  }

  async function handleAddChild(e) {
    e.preventDefault();
    const name = addChildForm.name.trim();
    if (!name) return;
    const age = addChildForm.age ? Number(addChildForm.age) : null;
    try {
      const child = await api.addChild(name, age);
      setAddChildForm({ name: '', age: '' });
      const me = await api.me();
      setChildren(me.children || []);
      enterApp(child.id, child.name);
    } catch (ex) { setErr(ex.message); }
  }

  async function handleSignOut() {
    try { await api.logout(); } catch { /* still reset locally */ }
    setStep('auth'); setTab('signin'); setChildren([]);
  }

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 grid place-items-center bg-ink/40 px-4"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.9, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        transition={{ type: 'spring', bounce: 0.35, duration: 0.4 }}
        className="relative w-full max-w-sm rounded-3xl bg-paper p-6 shadow-2xl"
      >
        <button
          onClick={onClose}
          aria-label="Close"
          className="absolute right-4 top-4 grid size-8 place-items-center rounded-full bg-bone text-ink-soft"
        >
          ✕
        </button>

        <div className="mb-4 flex flex-col items-center gap-1 text-center">
          <Mira size={54} />
          <span className="font-kid text-xl text-grape">Mira</span>
        </div>

        <AnimatePresence mode="wait">
          {step === 'auth' ? (
            <motion.div key="auth" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
              <div className="mb-4 flex rounded-full bg-bone p-1">
                <button
                  onClick={() => setTab('signup')}
                  className={`flex-1 rounded-full py-2 font-ui text-sm font-extrabold transition-colors ${tab === 'signup' ? 'bg-paper text-ink shadow-sm' : 'text-ink-soft'}`}
                >
                  Create account
                </button>
                <button
                  onClick={() => setTab('signin')}
                  className={`flex-1 rounded-full py-2 font-ui text-sm font-extrabold transition-colors ${tab === 'signin' ? 'bg-paper text-ink shadow-sm' : 'text-ink-soft'}`}
                >
                  Sign in
                </button>
              </div>

              {tab === 'signup' ? (
                <form onSubmit={handleSignup} className="flex flex-col gap-3">
                  <input
                    type="email" required placeholder="you@example.com" autoComplete="email"
                    value={signupForm.email}
                    onChange={(e) => setSignupForm((f) => ({ ...f, email: e.target.value }))}
                    className="rounded-2xl bg-bone px-4 py-3 font-ui text-sm outline-none focus:ring-2 focus:ring-grape/40"
                  />
                  <input
                    type="password" required minLength={8} placeholder="Password (min 8 characters)" autoComplete="new-password"
                    value={signupForm.password}
                    onChange={(e) => setSignupForm((f) => ({ ...f, password: e.target.value }))}
                    className="rounded-2xl bg-bone px-4 py-3 font-ui text-sm outline-none focus:ring-2 focus:ring-grape/40"
                  />
                  <label className="flex items-start gap-2 font-ui text-xs text-ink-soft">
                    <input
                      type="checkbox" required
                      checked={signupForm.consentService}
                      onChange={(e) => setSignupForm((f) => ({ ...f, consentService: e.target.checked }))}
                      className="mt-0.5"
                    />
                    I agree to Mira storing my child&apos;s practice data to run the app (required).
                  </label>
                  <label className="flex items-start gap-2 font-ui text-xs text-ink-soft">
                    <input
                      type="checkbox"
                      checked={signupForm.consentTraining}
                      onChange={(e) => setSignupForm((f) => ({ ...f, consentTraining: e.target.checked }))}
                      className="mt-0.5"
                    />
                    Also let anonymised recordings help improve the model (optional, off by default).
                  </label>
                  {err && <div className="font-ui text-xs font-bold text-mark-flagged">{err}</div>}
                  <button
                    disabled={busy} type="submit"
                    className="mt-1 rounded-full bg-sky py-3 font-kid text-lg text-white shadow-[0_5px_0_var(--sky-d)] disabled:opacity-60"
                  >
                    {busy ? 'Creating…' : 'Create account'}
                  </button>
                </form>
              ) : (
                <form onSubmit={handleSignin} className="flex flex-col gap-3">
                  <input
                    type="email" required placeholder="you@example.com" autoComplete="email"
                    value={signinForm.email}
                    onChange={(e) => setSigninForm((f) => ({ ...f, email: e.target.value }))}
                    className="rounded-2xl bg-bone px-4 py-3 font-ui text-sm outline-none focus:ring-2 focus:ring-grape/40"
                  />
                  <input
                    type="password" required placeholder="Password" autoComplete="current-password"
                    value={signinForm.password}
                    onChange={(e) => setSigninForm((f) => ({ ...f, password: e.target.value }))}
                    className="rounded-2xl bg-bone px-4 py-3 font-ui text-sm outline-none focus:ring-2 focus:ring-grape/40"
                  />
                  {err && <div className="font-ui text-xs font-bold text-mark-flagged">{err}</div>}
                  <button
                    disabled={busy} type="submit"
                    className="mt-1 rounded-full bg-sky py-3 font-kid text-lg text-white shadow-[0_5px_0_var(--sky-d)] disabled:opacity-60"
                  >
                    {busy ? 'Signing in…' : 'Sign in'}
                  </button>
                </form>
              )}
            </motion.div>
          ) : (
            <motion.div key="children" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
              <div className="mb-3 flex flex-col gap-2">
                {children.length === 0 && (
                  <p className="font-ui text-sm text-ink-soft">No child profiles yet — add one below to start.</p>
                )}
                {children.map((c) => (
                  <button
                    key={c.id}
                    onClick={() => enterApp(c.id, c.name)}
                    className="flex items-center gap-2 rounded-2xl bg-bone px-4 py-3 text-left font-ui font-bold text-ink hover:bg-sky-soft"
                  >
                    <span className="text-grape">▶</span>
                    <span>{c.name}</span>
                    {c.age_years ? <span className="ml-auto text-xs font-normal text-ink-soft">age {c.age_years}</span> : null}
                  </button>
                ))}
              </div>
              <form onSubmit={handleAddChild} className="flex flex-col gap-2 border-t border-bone-d pt-3">
                <div className="flex gap-2">
                  <input
                    placeholder="Child's name" required
                    value={addChildForm.name}
                    onChange={(e) => setAddChildForm((f) => ({ ...f, name: e.target.value }))}
                    className="flex-1 rounded-2xl bg-bone px-4 py-3 font-ui text-sm outline-none focus:ring-2 focus:ring-grape/40"
                  />
                  <input
                    type="number" min={1} max={17} placeholder="Age" style={{ width: 72 }}
                    value={addChildForm.age}
                    onChange={(e) => setAddChildForm((f) => ({ ...f, age: e.target.value }))}
                    className="rounded-2xl bg-bone px-3 py-3 font-ui text-sm outline-none focus:ring-2 focus:ring-grape/40"
                  />
                </div>
                {err && <div className="font-ui text-xs font-bold text-mark-flagged">{err}</div>}
                <button type="submit" className="rounded-full bg-sun py-3 font-kid text-lg text-ink shadow-[0_5px_0_var(--sun-d)]">
                  + Add a child
                </button>
              </form>
              <button onClick={handleSignOut} className="mt-4 w-full font-ui text-xs font-bold text-ink-faint">
                Sign out
              </button>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  );
}
