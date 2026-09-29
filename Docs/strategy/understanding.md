# Mira: Understanding

**Version:** v1.1
**Confirmed:** 29 September 2026
**Rule:** This is one living file. It is updated, never replaced. On each update, a change log entry says what changed. If a discussion changed direction, the entry records the first understanding and the gap Claude found.

---

## 0. Team
- 4 founders. They met in the Lean Launch Lab program.
- Roles are not defined yet.

## 1. The problem
- Kids with speech sound problems need practice every day.
- Therapy is 1 to 4 hours a week. The kid is awake 100+ hours a week at home.
- At home, nothing checks if a sound came out right. Kids copy YouTube or other videos.
- A parent must sit with the kid to judge each sound. Without the parent, practice has no feedback.
- Kids cannot hear their own errors. Parents cannot judge each sound reliably.

**Therapist gap (sourced):**
- US: 193,400 speech-language pathologists in 2025.
- India: 2,866 registered audiologists and speech-language pathologists in February 2022. The real number may be higher.

$$\text{US: } \frac{340{,}000{,}000}{193{,}400} \approx 1 \text{ per } 1{,}760 \text{ people}$$

$$\text{India: } \frac{1{,}450{,}000{,}000}{2{,}866} \approx 1 \text{ per } 506{,}000 \text{ people}$$

- India has about 290 times fewer therapists per person.
- Population figures are approximate.

**Relapse (checked, deck number corrected):**
- No source found for "60% of patients relapse after speech therapy."
- Stuttering, adults: 70% said they felt they relapsed. Most also said they got fluency back later (Craig and Hancock, 1995).
- Stuttering, kids aged 9 to 14: 3 in 10 relapsed at 12 months (Craig et al., 1998, 77 kids).
- No relapse number found for speech sound problems in kids aged 4 to 8. That is Mira's group.
- The 40 to 60% figure online is for addiction treatment.

## 2. Customer and positioning
- **Current first customer: kids aged 4 to 8, through parents.** Not final.
- **Planned price: ₹299 per month.** Not final.
- **Freemium plan:** some sounds free. Full library, dashboard, adaptive difficulty, and multi-child accounts are paid.
- **Positioning: wellness app first.** A therapist-guided clinical product needs medical approval. Approval (CDSCO SaMD, meaning "software as a medical device") takes 12 to 18 months and ₹15 to 40 lakh.
- **The wellness rule is strict.** India's 2026 guidance says wellness software must not refer to diseases or disorders. Software that screens, monitors, or manages a disorder is a medical device.

## 3. The product
- Daily loop: speak, score, feedback, record. About 10 minutes a day.
- Kid game: "Snake Sound Trail." One sound at a time. Stars can only go up.
- Kid sees 3 results: got it, needs work, or could not tell. No numbers.
- Parent report shows which sounds were flagged and which words to repeat.
- Next practice targets the kid's exact mix-up.

**Two code versions:**
- `HimanshuKGP007/mira-app`: stronger backend (scoring engine).
- `satvik-7772/mira-v4`: stronger UI (game, parent view, accounts).
- Plan: keep them as separate modules.

## 4. The tech: today and final state

| Part | Job | Today | Final state |
|---|---|---|---|
| Module 1, "the ear" | Scores each sound, names what came out instead | Runs on a server | On the phone, about 0.1 seconds, no cloud |
| Module 2A | Counts: percent correct, error patterns | Plain code | Same |
| Module 2B, "the coach" | Writes readable feedback | Fixed templates | Small language model (SLM), works offline |

- **Hard rule: Mira measures. It never decides.** No diagnosis, severity, or therapy plan.
- **It stays quiet when unsure.** Bad audio gets "record again." Weak sounds get "could not tell."
- A checker blocks any sentence with a number the code did not compute.
- Mira owns its model. No per-use AI fee. Recordings stay in-house.

## 5. The big problem: kids' voices and age-typical errors
**This is the largest open technical problem.**
- The model learned from adults only. It has zero child recordings.
- Adult voices stay stable over time. Kids' voices do not.
- Kids have higher pitch and higher resonances ("formants," meaning the sound peaks that shape each vowel and consonant). Kids' values can be up to 50% higher than adults'.
- These values change as the kid grows. They reach adult levels around age 15.
- So a model tuned on adults can mark a normal kid sound as wrong.
- Some errors are normal at some ages. Example: "wabbit" for "rabbit" is normal in young kids. Mira does not handle this yet.
- The only age norms are US norms (Crowe and McLeod, 2020). They may be wrong for Indian English.
- No public dataset of Indian child speech was found.
- Voice colour (timbre) is a separate topic the team is looking into.

## 6. Evidence so far
- **Model test:** ranks a wrong sound above a right sound 84 times in 100 (AUC 0.843). 5,000 recordings of Mandarin-speaking adults.
- **Indian accent test:** 6,607 recordings of fluent Indian adults. Flag rate 11.2%, below its own 16.0% error floor.
- **Therapists (Apollo SLPs):** confirmed the sound, word, sentence ladder; the scoring method; the home-practice gap; record-and-review fits their work.
- **Therapists also said:** getting families to practise is the real problem. Churn comes from motivation, not accuracy.
- **Parents:** see the problem, like the practice framing, like the character, willing to try at home.
- **Not tested with real kids.**
- **No payment yet.** This needs much more work.

## 7. Market and money (deck numbers, estimates)
- TAM: 9.5 million kids aged 4 to 8 (10% prevalence). ₹3,409 Cr per year.
- SAM: 1.43 million families. ₹511 Cr per year.
- SOM: 28,500 families. ₹10.2 Cr per year.
- Breakeven: about 5,500 paying families.
- At 20,000 families: 62% margin, ₹105 cost per user.

## 8. Competitors
- Constant Therapy (adults), Expressable (human teletherapy), ELSA Speak (accent), Stamurai (stuttering), SpeechLP/Sara (kids, English only, US pricing).
- Claim: nobody combines India, kids, and accent-aware sound feedback.

## 9. Out of scope
- Diagnosis, severity, therapy choice, clinical notes.
- Language delay, autism, speech after a stroke.
- Stuttering, voice, fluency: declined and referred.

## 10. Next steps
- Not decided. Candidates from the build plan: show a report to 3 therapists, consent draft, scoring service, word list with a therapist, thin app, 20-person trial, first payment.

## 11. Vision
- Indian kids aged 4 to 8, then adults with leftover speech issues, then global English learners, then more Indian languages, then a speech layer for other products.

## 12. Open issues
1. **Kids' voices and age norms** (section 5). No child data.
2. **Live app model is weaker.** Notebook: 0.843. Live app: 0.734.
3. **Wellness wording.** "Speech therapy," "disorder," and "screen and refer" in the deck can make Mira a medical device under the 2026 rule.
4. **TAM prevalence.** The 10% likely includes language delay and autism, which are out of scope.
5. **Deck fixes:** remove "tested with real children." Remove or replace "60% relapse."

---

## Change log
- **v1 (29 Sep 2026):** First confirmed version. Built from the 4 project files, both GitHub repos, 3 project chats, and the team pitch deck. Sources are in `sources.md`.
- **v1.1 (29 Sep 2026):** Removed founder names, backgrounds, and role assignments from section 0. Reason: roles are not defined yet.
