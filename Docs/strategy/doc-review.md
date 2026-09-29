# Mira: Review of the CCS Proposals and Company Overview

**Reviewed:** 29 September 2026
**Reviewed by:** Claude, for Himanshu
**Documents reviewed:**
- `CCS Proposal — Mira: Market Validation & Launch` (29 Sep 2026)
- `CCS Proposal — Mira: Product & Technology` (29 Sep 2026)
- `Mira — Company Overview` (29 Sep 2026)

**Checked against:** `understanding.md`, `sources.md`, `status.md`, and the code in `HimanshuKGP007/mira-app` and `satvik-7772/mira-v4` (commit `f262624`).

**Why this file exists:** the proposals make claims about the product. This file records which claims match the code on 29 Sep 2026. Recheck it after the two repos merge, because the code will change.

---

## 1. Claims that do not match the code

| Claim in the documents | What is true on 29 Sep 2026 | Confidence the claim is wrong |
|---|---|---|
| "Current build covers /s/, /r/, /l/" | Both repos build /s/ only | 98% |
| "Developmental-norms safety gate that prevents the app from ever flagging normal speech" | No child norms exist. The accent allow-list is empty | 97% |
| "Indian-accent- and age-aware scoring model" | Accent: tested on adults (11.2% flag rate on 6,607 recordings). Age: zero child data | 95% |
| "Real children have interacted with an early build" / "tested informally with real children" | Not tested with real kids. At most, kids used the app. Scoring was not checked on child speech | 90% |
| "Defers to an in-person SLP whenever it isn't confident" | The app shows "could not tell." It does not refer anyone | 90% |
| "Reproduced and validated an initial model (GOPT-based)" | Reproduced: yes (0.6103 vs published 0.612). Validated on adults only. The live app runs the weaker scorer (AUC 0.734, not 0.843) | 80% partly wrong |
| "Outside CDSCO's scope by design" | The documents use "articulation difficulties," "disorder," and "defers to SLP." CDSCO guidance CDSCO/MD/GD/MDSW/01/2026 says wellness claims must not refer to disorders | 75% (not legal advice) |

## 2. Numbers checked

The math in the Company Overview is correct:

$$\text{TAM} = 9.5\text{M} \times ₹299 \times 12 \approx ₹3{,}409 \text{ Cr}$$

$$\text{SAM} = 15\% \times 9.5\text{M} \approx 1.43\text{M} \Rightarrow ₹511 \text{ Cr}$$

$$\text{SOM} = 2\% \times 1.43\text{M} \approx 28{,}500 \Rightarrow ₹10.2 \text{ Cr}$$

$$\text{Cost per user at 20,000} = \frac{₹15{,}00{,}000}{20{,}000} + ₹30 = ₹105$$

$$\text{Breakeven} = \frac{₹15{,}00{,}000}{₹299 - ₹30} \approx 5{,}576 \text{ users}$$

**Two costs look missing (70% confidence):**
- 18% GST, if ₹299 includes it.
- The 15% Play Store subscription fee.

With both, net revenue per user is about ₹215:

$$₹299 \div 1.18 \approx ₹253, \quad ₹253 \times 0.85 \approx ₹215$$

$$\text{Breakeven} = \frac{₹15{,}00{,}000}{₹215 - ₹30} \approx 8{,}100 \text{ users}$$

**The 10% prevalence** is "parent-reported speech difficulty" from international studies. It likely includes language delay and other out-of-scope cases. Published prevalence for speech sound disorders ranges from 2.3% to 24.6% by definition and age (see `sources.md`).

## 3. What is good

- **Market Validation CCS:** tests a clear hypothesis, onboards an SLP advisor, and measures which channels convert. Weak spot: interviews do not prove willingness to pay. Only a real payment does.
- **Two workstreams, each owned by a pair of founders.** This gives the team clear ownership.
- **Numbers are labelled "sourced" or "estimated."** Keep this.
- **The risk register names the right top risk:** the model misreading normal child speech.
- **DPDP Act consent from day one.** Satvik's code already has consent boxes, with training-data use off by default.

## 4. Is the direction correct?

| Part of the direction | Confidence it is right | Reason |
|---|---|---|
| The problem is real | 90% | About 1 therapist per 506,000 people in India (sourced) |
| Narrow practice tool that measures and never decides | 85% | Safe, testable, and enforced in code |
| Wellness first, clinical later | 70% | Right idea. The current wording breaks it |
| Scoring feedback as the core value | 60% | SLPs said motivation, not accuracy, drives churn. The planned 2-group trial answers this |
| Own model, on-device, SLM coach later | 60% | Good for cost and privacy. The current model is about 1.26 GB. A mid-range phone needs a much smaller one |
| Kids aged 4 to 8 first | 50% | Strongest parent pull. Biggest tech gap: no child data, no norms, ethics approval needed |
| ₹299 per month | 45% | Zero payments so far |
| Product CCS ships everything in one term | 25% | Child data, ethics approval, and an SLP-built norms table can each take a full term |

**Overall: about 60% confident the direction is right.** The strategy is sound. The main risk is the gap between what the documents claim and what the code does.

## 5. Recommended changes

1. Fix every claim in section 1 before anyone outside the team reads these documents.
2. Cut the Product CCS to 1 sound (/s/, already built) plus the child-data and norms work. Add /r/ and /l/ after the norms gate exists.
3. Add one real payment test (a paid pre-order) to the Market Validation CCS.
4. Add GST and store fees to the cost model.
5. Replace disorder language with practice language in all user-facing and external text.

## 6. Recheck after the repos merge

After Satvik's code merges, recheck these rows in section 1:
- Number of sounds built.
- Whether a developmental-norms gate exists.
- Which scorer the live app runs (0.734 or 0.843).
- Whether the app refers low-confidence cases to an SLP.

---

## Change log
- **v1 (29 Sep 2026):** First review.
