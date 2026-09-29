/* ============================================================================
   motion.js — the app's motion primitives, hand-ported from the techniques
   motion-primitives.com / Framer Motion use, without React or a build step.

   Everything here is the real Web Animations API (WAAPI) — no dependency,
   nothing fetched. A CSS `linear()` easing string is sampled from a damped
   spring simulation (the same trick Motion uses to run "real" springs on the
   compositor thread); browsers without `linear()` support fall back to the
   app's existing --pop cubic-bezier, so nothing breaks on an older browser.

   Every primitive here funnels through MOTION.enabled, which mirrors
   `prefers-reduced-motion: reduce` and updates live if the OS setting
   changes mid-session. Infinite loops (float/drift/parallax) register a
   stop handle so they can be torn down instantly; one-shot transitions
   (spring/pop/wiggle/reveal/morph) collapse to a near-instant state change
   instead of skipping outright, so the UI still ends up correct.
   ========================================================================== */

// --------------------------------------------------------------------------
// the global motion gate
// --------------------------------------------------------------------------
const _mq = window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)') : null;
const _liveHandles = new Set();   // every running float/drift/parallax, so a live
                                   // OS-setting change can stop them immediately

export const MOTION = {
  enabled: !(_mq && _mq.matches),
};

function _setEnabled(v) {
  MOTION.enabled = v;
  if (!v) for (const h of _liveHandles) h.stop();
}
if (_mq) {
  const onChange = e => _setEnabled(!e.matches);
  if (_mq.addEventListener) _mq.addEventListener('change', onChange);
  else if (_mq.addListener) _mq.addListener(onChange);   // older Safari
}

const _linearSupported = (() => {
  try { return CSS.supports('animation-timing-function', 'linear(0, 1)'); }
  catch { return false; }
})();

// --------------------------------------------------------------------------
// spring easing — sample a damped harmonic oscillator into a linear()
// easing string. Same parameterisation as Motion's spring(): duration is
// roughly time-to-settle, bounce 0..1 (0 = no overshoot, ~0.3 = a gentle
// pop, close to 1 = very springy).
// --------------------------------------------------------------------------
const _springCache = new Map();

function springEasing(duration = 0.5, bounce = 0.22) {
  if (!_linearSupported) return 'var(--pop)';
  const key = duration + ':' + bounce;
  const cached = _springCache.get(key);
  if (cached) return cached;

  // Convert duration/bounce into a damping ratio + natural frequency, the
  // same shape react-spring/Motion use under the hood.
  const zeta = Math.max(0.001, 1 - bounce);           // damping ratio
  const omega = (2 * Math.PI) / Math.max(0.05, duration);

  const SAMPLES = 24;
  const points = [];
  for (let i = 0; i <= SAMPLES; i++) {
    const t = (i / SAMPLES) * duration;
    let x;
    if (zeta < 1) {
      const omegaD = omega * Math.sqrt(1 - zeta * zeta);
      x = 1 - Math.exp(-zeta * omega * t) *
        (Math.cos(omegaD * t) + (zeta * omega / omegaD) * Math.sin(omegaD * t));
    } else {
      x = 1 - Math.exp(-omega * t) * (1 + omega * t);   // critically damped
    }
    points.push(Math.round(x * 1000) / 1000);
  }
  points[points.length - 1] = 1;   // land exactly on 1, floating point insurance
  const str = `linear(${points.join(', ')})`;
  _springCache.set(key, str);
  return str;
}

// --------------------------------------------------------------------------
// spring — the base primitive everything else builds on
// --------------------------------------------------------------------------
/**
 * Animate `el` through WAAPI keyframes on a spring easing.
 * opts: { duration=0.5 (s), bounce=0.22, delay=0, fill='both', ...standard
 * KeyframeAnimationOptions }. Returns the Animation.
 */
export function spring(el, keyframes, opts = {}) {
  if (!el) return null;
  const { duration = 0.5, bounce = 0.22, delay = 0, fill = 'both', ...rest } = opts;
  if (!MOTION.enabled) {
    // Collapse to the resting state instantly rather than skip — callers
    // rely on the final keyframe having actually applied.
    return el.animate(keyframes, { duration: 1, delay: 0, fill: 'forwards' });
  }
  return el.animate(keyframes, {
    duration: duration * 1000,
    delay: delay * 1000,
    easing: springEasing(duration, bounce),
    fill,
    ...rest,
  });
}

// --------------------------------------------------------------------------
// stagger — the same keyframes across a list, offset in time
// --------------------------------------------------------------------------
/**
 * opts: everything spring() takes, plus { each=0.06 } (seconds between
 * successive elements). Returns a Promise that resolves once every
 * animation has finished.
 */
export function stagger(els, keyframes, opts = {}) {
  const { each = 0.06, ...rest } = opts;
  const list = Array.from(els || []);
  const anims = list.map((el, i) =>
    spring(el, keyframes, { ...rest, delay: (rest.delay || 0) + i * each }));
  return Promise.all(anims.filter(Boolean).map(a => a.finished.catch(() => {})));
}

// --------------------------------------------------------------------------
// reveal — fade/rise-in the first time an element crosses into view
// --------------------------------------------------------------------------
const _revealFrom = { opacity: [0, 1], transform: ['translateY(16px)', 'translateY(0)'] };

/**
 * Observes `els` and springs each one in the first time it enters the
 * viewport, then stops watching it. No-ops (elements start visible) when
 * MOTION is disabled.
 */
export function reveal(els, opts = {}) {
  const list = Array.from(els || []);
  if (!list.length) return;
  if (!('IntersectionObserver' in window) || !MOTION.enabled) {
    list.forEach(el => { el.style.opacity = ''; el.style.transform = ''; });
    return;
  }
  const io = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      spring(entry.target, _revealFrom, { duration: 0.5, bounce: 0.18, ...opts });
      io.unobserve(entry.target);
    }
  }, { threshold: 0.2 });
  list.forEach(el => { el.style.opacity = '0'; io.observe(el); });
}

// --------------------------------------------------------------------------
// morph — FLIP shared-element transition (e.g. a tapped map node expanding
// into the exercise card)
// --------------------------------------------------------------------------
/**
 * `fromEl` is the element in its OLD position/size (may already be removed
 * from the layout — only its measured rect is used). `toEl` must already be
 * in the DOM at its final position when this is called. Inverts toEl to
 * fromEl's rect, then springs it back to identity.
 */
export function morph(fromRect, toEl, opts = {}) {
  if (!toEl || !fromRect) return null;
  const to = toEl.getBoundingClientRect();
  if (!to.width || !to.height) return null;

  const dx = fromRect.left + fromRect.width / 2 - (to.left + to.width / 2);
  const dy = fromRect.top + fromRect.height / 2 - (to.top + to.height / 2);
  const sx = fromRect.width / to.width;
  const sy = fromRect.height / to.height;

  if (!MOTION.enabled) return null;   // straight cut, no invert-and-play needed

  return toEl.animate([
    { transform: `translate(${dx}px, ${dy}px) scale(${sx}, ${sy})`, opacity: 0.85 },
    { transform: 'translate(0, 0) scale(1, 1)', opacity: 1 },
  ], {
    duration: 420,
    easing: springEasing(0.42, 0.2),
    fill: 'both',
  });
}

// --------------------------------------------------------------------------
// press — delegated pointer-press feedback for anything tappable
// --------------------------------------------------------------------------
const PRESS_SELECTOR = '.btn, .node, .dock-item, .icon-btn, .key, [data-press]';

/**
 * Wires pointerdown/up/cancel/leave delegation once on `root` (default:
 * document.body). Any element matching PRESS_SELECTOR (or carrying
 * data-press) gets a small spring squash on press and release. Call once
 * at boot; safe to call more than once on different roots.
 */
export function press(root = document.body, selector = PRESS_SELECTOR) {
  let current = null;
  const down = (e) => {
    const el = e.target.closest(selector);
    if (!el || el.disabled) return;
    current = el;
    spring(el, { transform: ['scale(1)', 'scale(0.94)'] }, { duration: 0.14, bounce: 0.1 });
  };
  const up = () => {
    if (!current) return;
    const el = current; current = null;
    spring(el, { transform: ['scale(0.94)', 'scale(1)'] }, { duration: 0.32, bounce: 0.45 });
  };
  root.addEventListener('pointerdown', down);
  root.addEventListener('pointerup', up);
  root.addEventListener('pointercancel', up);
  root.addEventListener('pointerleave', up, true);
  return () => {
    root.removeEventListener('pointerdown', down);
    root.removeEventListener('pointerup', up);
    root.removeEventListener('pointercancel', up);
    root.removeEventListener('pointerleave', up, true);
  };
}

// --------------------------------------------------------------------------
// one-shots
// --------------------------------------------------------------------------
/** Bounce an element in from nothing — badge pops, star gains, unlocks. */
export function pop(el, opts = {}) {
  return spring(el, {
    transform: ['scale(0.3)', 'scale(1.12)', 'scale(1)'],
    opacity: [0, 1, 1],
  }, { duration: 0.5, bounce: 0.55, ...opts });
}

/** Small side-to-side shake — a locked node, a rejected action. */
export function wiggle(el, opts = {}) {
  if (!el) return null;
  if (!MOTION.enabled) return null;
  return el.animate([
    { transform: 'translateX(0) rotate(0)' },
    { transform: 'translateX(-6px) rotate(-4deg)' },
    { transform: 'translateX(5px) rotate(3deg)' },
    { transform: 'translateX(-4px) rotate(-2deg)' },
    { transform: 'translateX(0) rotate(0)' },
  ], { duration: 380, easing: 'ease-in-out', ...opts });
}

/** Animate a number in an element's textContent from `from` to `to`. */
export function countUp(el, { from = 0, to = 0, duration = 0.6, format = String } = {}) {
  if (!el) return;
  if (!MOTION.enabled || to === from) { el.textContent = format(to); return; }
  const t0 = performance.now();
  const dur = duration * 1000;
  function tick(now) {
    const p = Math.min(1, (now - t0) / dur);
    const eased = 1 - Math.pow(1 - p, 3);   // ease-out cubic — no WAAPI for text content
    el.textContent = format(Math.round(from + (to - from) * eased));
    if (p < 1) requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
}

// --------------------------------------------------------------------------
// float / drift — ambient, infinite, desynchronised idle motion
// --------------------------------------------------------------------------
function _registerLoop(anim) {
  const handle = { stop: () => { try { anim.cancel(); } catch {} _liveHandles.delete(handle); } };
  _liveHandles.add(handle);
  anim.finished.catch(() => {}).finally(() => _liveHandles.delete(handle));
  return handle;
}

/**
 * Endless gentle vertical (or horizontal) bob. `phase` (0..1, default
 * randomised) desyncs a group of elements so they never pulse in lockstep —
 * pass an explicit phase when you want two elements to move together.
 * Returns a stop handle ({stop()}); no-ops (returns null) when MOTION is
 * disabled.
 */
export function float(el, { amp = 6, period = 3.2, phase = Math.random(), axis = 'y' } = {}) {
  if (!el || !MOTION.enabled) return null;
  const prop = axis === 'x' ? 'translateX' : 'translateY';
  const anim = el.animate([
    { transform: `${prop}(0px)` },
    { transform: `${prop}(${-amp}px)` },
    { transform: `${prop}(0px)` },
  ], {
    duration: period * 1000,
    easing: 'ease-in-out',
    iterations: Infinity,
    delay: -phase * period * 1000,   // negative delay = starts mid-cycle, desynced
  });
  return _registerLoop(anim);
}

/**
 * Slow ambient wander — clouds, bubbles, fireflies. Two-segment loop so the
 * path isn't a simple back-and-forth.
 */
export function drift(el, { amp = 14, period = 7, axis = 'both' } = {}) {
  if (!el || !MOTION.enabled) return null;
  const dx = axis === 'y' ? 0 : amp;
  const dy = axis === 'x' ? 0 : amp * 0.6;
  const anim = el.animate([
    { transform: 'translate(0px, 0px)' },
    { transform: `translate(${dx}px, ${-dy}px)` },
    { transform: `translate(${-dx * 0.6}px, ${dy * 0.4}px)` },
    { transform: 'translate(0px, 0px)' },
  ], {
    duration: period * 1000,
    easing: 'ease-in-out',
    iterations: Infinity,
    delay: -Math.random() * period * 1000,
  });
  return _registerLoop(anim);
}

// --------------------------------------------------------------------------
// parallax — pointer-depth movement across background layers
// --------------------------------------------------------------------------
/**
 * `layers`: [{ el, depth }] — depth is how many px the layer travels at
 * full pointer excursion (small depth = far away = barely moves). Attaches
 * a single pointermove listener on `root`. Returns a stop handle.
 */
export function parallax(layers, { root = document, max = 10 } = {}) {
  const list = (layers || []).filter(l => l && l.el);
  if (!list.length || !MOTION.enabled) return null;
  let raf = null, tx = 0, ty = 0;
  const onMove = (e) => {
    const w = window.innerWidth || 1, h = window.innerHeight || 1;
    tx = (e.clientX / w - 0.5) * 2;   // -1..1
    ty = (e.clientY / h - 0.5) * 2;
    if (raf) return;
    raf = requestAnimationFrame(() => {
      raf = null;
      for (const { el, depth } of list) {
        el.style.transform = `translate(${(tx * depth).toFixed(1)}px, ${(ty * depth * 0.6).toFixed(1)}px)`;
      }
    });
  };
  root.addEventListener('pointermove', onMove, { passive: true });
  const handle = {
    stop: () => {
      root.removeEventListener('pointermove', onMove);
      if (raf) cancelAnimationFrame(raf);
      list.forEach(({ el }) => { el.style.transform = ''; });
      _liveHandles.delete(handle);
    },
  };
  _liveHandles.add(handle);
  void max;   // reserved for future clamping; pointer excursion is already normalised
  return handle;
}
