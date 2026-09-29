/* ============================================================================
   onboarding.js — first-run spotlight walkthrough.

   Frontend-only by design this session (no server changes): "seen" state is
   plain localStorage, per screen, keyed per child via account.childId so two
   children sharing a browser each get their own first run. There is no
   server sync — a child who onboards on one device sees it again on
   another. That's an acceptable gap for a client-side-only feature; a real
   cross-device flag would need a server column, which is out of scope here.

   Each tour is SCREEN-LOCAL and runs once, the first time that screen is
   shown for this child: it spotlights one real element already on screen
   and says one line about it, never drives navigation itself. If the
   element it wants to point at isn't there (a layout change, a locked
   feature), the step is skipped rather than blocking the child from
   playing — onboarding must never be a wall between a kid and the mic.
   ========================================================================== */

const LS_PREFIX = 'mira_onboard_';

function scopeKey(key) {
  const childId = localStorage.getItem('mira_child_id') || 'anon';
  return `${LS_PREFIX}${childId}_${key}`;
}

export function hasSeen(key) {
  return localStorage.getItem(scopeKey(key)) === '1';
}

export function markSeen(key) {
  localStorage.setItem(scopeKey(key), '1');
}

/** For the settings screen: "Show the tour again" resets every tour's flag. */
export function resetAll() {
  const childId = localStorage.getItem('mira_child_id') || 'anon';
  const prefix = `${LS_PREFIX}${childId}_`;
  Object.keys(localStorage).filter(k => k.startsWith(prefix)).forEach(k => localStorage.removeItem(k));
}

let activeOverlay = null;

/**
 * runTour(key, steps, opts) — no-ops instantly if `key` was already seen.
 * steps: [{ anchor: '#selector', title, body, say? }]
 * opts: { say(text), sfx(name), onDone() }
 */
export function runTour(key, steps, opts = {}) {
  if (hasSeen(key) || !steps || !steps.length) return;
  markSeen(key);   // mark immediately: a refresh mid-tour must not re-trigger it forever

  let i = 0;
  showStep();

  function showStep() {
    const step = steps[i];
    const anchor = step.anchor ? document.querySelector(step.anchor) : null;
    if (step.anchor && !anchor) { finish(); return; }   // missing target -> bail quietly
    paint(anchor, step);
  }

  function paint(anchor, step) {
    teardown();
    const rect = anchor ? anchor.getBoundingClientRect() : null;

    const overlay = document.createElement('div');
    overlay.className = 'onboard-overlay';
    if (rect) {
      const hole = document.createElement('div');
      hole.className = 'onboard-hole';
      hole.style.left = `${rect.left - 7}px`;
      hole.style.top = `${rect.top - 7}px`;
      hole.style.width = `${rect.width + 14}px`;
      hole.style.height = `${rect.height + 14}px`;
      overlay.appendChild(hole);
    } else {
      overlay.classList.add('no-hole');
    }

    const card = document.createElement('div');
    card.className = 'onboard-card';
    card.innerHTML = `
      <div class="onboard-step">${i + 1} of ${steps.length}</div>
      <div class="onboard-title">${step.title}</div>
      <div class="onboard-body">${step.body}</div>
      <div class="onboard-foot">
        <button class="quiet onboard-skip">Skip</button>
        <button class="btn btn-primary onboard-next" style="font-size:15px;padding:10px 22px">
          ${i === steps.length - 1 ? "Got it!" : 'Next'}
        </button>
      </div>`;
    overlay.appendChild(card);
    document.body.appendChild(overlay);
    activeOverlay = overlay;

    positionCard(card, rect);

    card.querySelector('.onboard-next').addEventListener('click', () => {
      opts.sfx?.('tap');
      i += 1;
      if (i >= steps.length) finish(); else showStep();
    });
    card.querySelector('.onboard-skip').addEventListener('click', finish);

    if (opts.say && step.say) opts.say(step.say);
  }

  function positionCard(card, rect) {
    const vw = window.innerWidth, vh = window.innerHeight;
    // Measure after paint so card.offsetHeight is real.
    requestAnimationFrame(() => {
      const cw = card.offsetWidth, ch = card.offsetHeight;
      let top, left = Math.max(14, Math.min(vw - cw - 14, (rect ? rect.left + rect.width / 2 : vw / 2) - cw / 2));
      if (!rect) {
        top = (vh - ch) / 2;
      } else if (rect.top + rect.height + ch + 28 < vh) {
        top = rect.top + rect.height + 18;         // below the target
      } else if (rect.top - ch - 18 > 0) {
        top = rect.top - ch - 18;                   // above the target
      } else {
        top = Math.max(14, (vh - ch) / 2);           // fallback: centered
      }
      card.style.left = `${left}px`;
      card.style.top = `${top}px`;
    });
  }

  function teardown() {
    if (activeOverlay) { activeOverlay.remove(); activeOverlay = null; }
  }

  function finish() {
    teardown();
    opts.onDone?.();
  }
}
