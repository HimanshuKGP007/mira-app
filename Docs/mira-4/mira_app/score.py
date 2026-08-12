"""mira_app/score.py - one recording in, one set of phone results out.

This is Module 1's whole job, in the order the order matters.

    1. condition        trim, measure noise. A dirty clip never reaches the model
    2. forward pass     one pass; every reading comes from identical frames
    3. align            where did each target sound happen
    4. alignment gate   if the boundaries are guesses, stop. Everything after
                        this point sits on top of them
    5. free decode      what did the model actually hear
    6. word identity    did they say the word we asked for at all
    7. score            the trained scorer, then the calibrator
    8. correlates       optional, off by default, ranges unvalidated
    9. excuse and type  the allow-list, then fixed-order error typing
   10. per-phone gates  confidence and the withholding policy
   11. build response   every phone gets a score or a reason

Steps 1 and 4 are there so the expensive parts only run on recordings worth
spending them on. That is a cost argument as much as a safety one.

ON RUNNING WITHOUT A TRAINED SCORER
-----------------------------------
The trained scorer comes out of a Stage 2 run. Until one exists this module runs
in PREVIEW mode, where the score is a monotone function of goodness of
pronunciation and the confidence is uncalibrated.

Preview mode is roughly the published binary baseline: it ranks bad sounds above
good ones about 65% of the time where the trained scorer manages 84%. It is good
enough to demonstrate the product and it is not good enough to show a clinician.

The important part is that it says so. `uncalibrated` is True on every phone
result, on the response, on the analysis and in the report header, and it cannot
be switched off by a flag. A preview number that looks like a validated number is
the single most dangerous artefact this codebase could produce.
"""

import uuid

import numpy as np

from . import mira_core
from . import protocol as proto
from .contracts import (PhoneResult, check_recording_gates, check_word_identity,
                        build_response, GATE_DEFAULTS)


class MiraEngine:
    """Holds the decoder and the optional bundle so neither is reloaded per call."""

    def __init__(self, decoder, bundle=None, allow_list=None,
                 correlates_enabled=False, thresholds=None):
        self.decoder = decoder
        self.bundle = bundle
        self.allow_list = allow_list or mira_core.AccentAllowList()
        self.correlates_enabled = correlates_enabled
        self.thresholds = dict(GATE_DEFAULTS)
        if thresholds:
            self.thresholds.update(thresholds)

        # Resolve the protocol's ARPABET inventory to token ids ONCE. A phone that
        # cannot be resolved is reported here, at startup, rather than silently
        # producing a wrong goodness figure on every recording that contains it.
        arps = sorted({p for _, ph, _ in proto.WORDS for p in ph})
        ipa = {a: mira_core.canonical_ipa(a) for a in arps}
        self.phone_map, self.unmapped, self.map_report = mira_core.build_phone_token_map(
            decoder.vocab, [v for v in ipa.values() if v])
        self.arp_to_ipa = ipa
        self.arp_to_token = {a: self.phone_map.get(i) for a, i in ipa.items() if i}
        self.phone_ids = sorted({t for t in self.arp_to_token.values()
                                 if t is not None})

    # -- diagnostics ---------------------------------------------------------

    def readiness(self):
        """What this engine can and cannot do right now, as data.

        Called by the CLI and printed at the top of every report. It is the
        honest answer to 'can I show this to someone', and it is computed rather
        than remembered.
        """
        missing = sorted(a for a, t in self.arp_to_token.items() if t is None)
        return {
            "decoder": getattr(self.decoder, "model_id", type(self.decoder).__name__),
            "synthetic_decoder": type(self.decoder).__name__ == "SyntheticDecoder",
            "trained_scorer": self.bundle is not None,
            "calibrated": bool(self.bundle and getattr(self.bundle, "calibrated", False)),
            "uncalibrated": self.bundle is None or not getattr(
                self.bundle, "calibrated", False),
            "correlates_enabled": self.correlates_enabled,
            "allow_list_rules": len(self.allow_list.rules),
            "protocol": f"{proto.PROTOCOL_ID} {proto.PROTOCOL_VERSION}",
            "protocol_words": len(proto.WORDS),
            "phones_resolved": len(self.arp_to_token) - len(missing),
            "phones_unresolved": missing,
            "mode": "validated" if self.bundle else "preview",
        }

    def provenance(self):
        if self.bundle is not None:
            return self.bundle.provenance()
        return {
            "model_version": getattr(self.decoder, "model_id", "unknown"),
            "aligner_version": f"mira_core.ctc_forced_align {mira_core.CORE_VERSION}",
            "protocol_version": f"{proto.PROTOCOL_ID}:{proto.PROTOCOL_VERSION}",
            "threshold_set_version": "PREVIEW_UNCALIBRATED",
            "core_sha256": "not_bundled",
            "bundle_version": "none_preview_mode",
        }

    # -- scoring -------------------------------------------------------------

    def _preview_score(self, gop, lp, a, b):
        """Preview mode: a score and a confidence, kept strictly separate.

        SCORE answers "was the sound we asked for produced". It is a monotone map
        from goodness of pronunciation onto the 0 to 2 scale the corpus uses.

        CONFIDENCE answers "how certain are we of that measurement". It is the
        model's peak posterior in the window, over the whole vocabulary.

        THESE MUST NOT BE THE SAME NUMBER. Deriving confidence from the target
        posterior means a confident error reads as low confidence, the per-phone
        gate holds it, and Mira declines to score exactly the sounds that were
        wrong. The result is a report claiming near-perfect accuracy because
        every error was quietly withheld. It is the same failure as gating
        alignment on goodness, one level down.

        A window that is confidently [t] when we asked for /s/ is a HIGH
        confidence measurement of a LOW score, and both halves of that sentence
        have to survive into the record.

        The constants are chosen so the demo behaves sensibly. They are fitted to
        nothing and no threshold in this codebase is calibrated against them.
        """
        if gop is None:
            return None, None
        score = float(np.clip(2.0 * float(np.exp(min(gop, 0.0))), 0.0, 2.0))
        seg = lp[int(a):int(b)]
        conf = (float(np.mean(np.exp(np.max(seg, axis=1)))) if seg.size
                else 0.0)
        return score, conf

    def score(self, audio, sr, word, capture_context="home", speaker=None):
        item = proto.get_item(word)
        return self.score_item(audio, sr, item, capture_context, speaker)

    def score_item(self, audio, sr, item, capture_context="home", speaker=None):
        utt_id = str(uuid.uuid4())
        speaker = speaker or {}
        th = self.thresholds
        prov = self.provenance()
        uncal = self.bundle is None or not getattr(self.bundle, "calibrated", False)

        arps = item["phones"]
        ipas = [self.arp_to_ipa.get(a) for a in arps]
        tokens = [self.arp_to_token.get(a) for a in arps]

        def held_response(reason, gate, extra=None):
            return build_response(utt_id, item["word"], [], gate, prov,
                                  {"reason": reason, "uncalibrated": uncal,
                                   **(extra or {})})

        # --- 1. condition ---------------------------------------------------
        audio, cond = mira_core.condition_audio(audio, sr, do_trim=True,
                                                min_snr_db=None)
        snr = cond["snr_db"]
        floor = th["min_snr_db"] * (th["home_capture_multiplier"]
                                    if capture_context == "home" else 1.0)
        if snr is None or snr < floor:
            gate = check_recording_gates(snr, None, capture_context, th)
            return held_response("recording too noisy to measure", gate,
                                 {"conditioning": cond})

        # --- 2. forward pass ------------------------------------------------
        lp = self.decoder.logprobs(audio, sr)
        n_frames = lp.shape[0]
        sec_per_frame = (len(audio) / sr) / max(n_frames, 1)

        # --- 3/4. align and gate --------------------------------------------
        usable = [t for t in tokens if t is not None]
        if not usable:
            gate = check_recording_gates(snr, 0.0, capture_context, th)
            return held_response(
                "no sound in this word is in the model's phone inventory", gate,
                {"conditioning": cond})

        # ctc_forced_align returns (path, score). Unpacking it as one value gives
        # a two-element tuple that spans_from_path will happily iterate, producing
        # spans that are silently wrong. Worth stating because it already happened.
        path, path_score = mira_core.ctc_forced_align(lp, usable, self.decoder.blank_id)
        if path is None:
            gate = check_recording_gates(snr, 0.0, capture_context, th)
            return held_response(
                "the recording is too short to contain all the sounds in this word",
                gate, {"conditioning": cond})

        usable_spans = mira_core.spans_from_path(path, len(usable))
        spans, k = [], 0
        for t in tokens:
            if t is None:
                spans.append((None, None))
            else:
                spans.append(usable_spans[k])
                k += 1

        # Alignment quality asks whether the SEGMENTATION fits the audio, which is
        # a different question from whether the speaker said the right thing.
        #
        # The obvious implementation, the mean posterior on each target inside its
        # own window, is goodness of pronunciation, and using it here gates the
        # score on the score. The consequence is not subtle: a speaker who says
        # [t] for /s/ fails the gate and the whole item is held, so Mira refuses
        # to score exactly the recordings that contain errors and then reports
        # near-perfect accuracy on what survives. See mira_core.alignment_confidence.
        align_q, align_detail = mira_core.alignment_confidence(
            lp, spans, target_ids=tokens)
        align_q = 0.0 if align_q is None else align_q

        gate = check_recording_gates(snr, align_q, capture_context, th)
        if not gate.passed:
            return held_response("boundaries could not be trusted", gate,
                                 {"conditioning": cond,
                                  "alignment_quality": round(align_q, 4),
                                  "alignment_detail": align_detail})

        # --- 5/6. free decode and word identity ------------------------------
        inv = {v: k for k, v in self.decoder.vocab.items()}
        fd = mira_core.free_decode(lp, self.decoder.blank_id, inv)
        target_string = "".join(i for i in ipas if i)
        # The word-identity gate exists for the case where someone names the
        # picture with a completely different word, which would otherwise align
        # to the wrong target and score every sound in the item as an error.
        #
        # It cannot do that job on a short word. "shoe" is two sounds, so a single
        # substitution drops the similarity to 0.25 and the gate holds a perfectly
        # good recording of a real error. On a two or three sound target there is
        # no information that separates "said a different word" from "made one
        # mistake", so the honest move is to skip the gate and let the per-sound
        # error typing do its job.
        MIN_PHONES_FOR_WORD_GATE = 4
        if len(target_string) >= MIN_PHONES_FOR_WORD_GATE:
            wg = check_word_identity(fd["string"], target_string)
        else:
            wg = check_word_identity(None, target_string)   # passes, by contract
        if not wg.passed:
            gate.passed = False
            gate.failures.extend(wg.failures)
            return held_response(
                f"this does not sound like {item['word']!r}; it was heard as "
                f"{fd['string'][:24]!r}",
                gate, {"conditioning": cond, "free_decode": fd["string"][:64],
                       **wg.measurements})

        produced, insertions = mira_core.attribute_produced_phones(
            [i for i in ipas if i], fd["segments"])
        # re-expand to the full target list, since unmapped phones were dropped
        pfull, k = [], 0
        for i in ipas:
            if i is None:
                pfull.append({})
            else:
                pfull.append(produced[k] if k < len(produced) else {})
                k += 1

        # --- 7 to 11. per-phone ----------------------------------------------
        phones = []
        for idx, arp in enumerate(arps):
            tok = tokens[idx]
            p = pfull[idx]
            a, b = spans[idx]
            common = dict(target=arp, position=item["positions"][idx],
                          produced=p.get("produced"),
                          produced_confident=bool(p.get("produced_confident", True)))

            if tok is None or a is None:
                phones.append(PhoneResult(
                    flag="not_scored", error_type="held",
                    reason=("this sound is not in the model's phone inventory"
                            if tok is None else
                            "the aligner gave this sound no frames"),
                    error_why="gate", **common))
                continue

            b = min(int(b), n_frames)
            t0, t1 = int(a) * sec_per_frame, b * sec_per_frame

            g = mira_core.gop_variants(lp, int(a), b, tok, self.decoder.blank_id)
            gop = g.get("gop_mean")

            if self.bundle is not None:
                raw = float(self.bundle.score_one(g, lp, int(a), b, tok))
                conf = float(self.bundle.calibrate([raw])[0])
                score = float(np.clip(raw, 0.0, 2.0))
            else:
                score, conf = self._preview_score(gop, lp, a, b)

            if score is None:
                phones.append(PhoneResult(
                    flag="not_scored", error_type="held",
                    reason="no goodness figure could be computed for this window",
                    start_s=round(t0, 4), end_s=round(t1, 4), **common))
                continue

            correlates, corr_flag = {}, None
            if self.correlates_enabled:
                correlates = mira_core.measure_correlates(
                    audio, sr, arp, t0, t1, sex=speaker.get("sex", "m"),
                    age_months=speaker.get("age_months"))
                corr_flag = correlates.get("flag")

            rule = self.allow_list.excuse(
                self.arp_to_ipa.get(arp), p.get("produced"),
                item["positions"][idx], utterance_id=utt_id)

            policy = getattr(self.bundle, "policy", None)
            if policy is not None:
                ok, why = policy.decide(arp, conf, th["min_confidence"])
            else:
                ok = conf >= th["min_confidence"]
                why = (None if ok else
                       f"confidence {conf:.2f} is below the {th['min_confidence']:.2f} floor")
            if not ok:
                phones.append(PhoneResult(
                    flag="not_scored", error_type="held", reason=why, error_why=why,
                    start_s=round(t0, 4), end_s=round(t1, 4),
                    correlates=correlates, **common))
                continue

            fused, fuse_detail = mira_core.fuse_broad_and_correlate(
                score, correlates.get("z"), correlate_weight=0.0)
            etype, ewhy = mira_core.classify_error_type(
                target=self.arp_to_ipa.get(arp), produced=p.get("produced"),
                role=p.get("role"), correlate_flag=corr_flag, excused_rule=rule,
                neighbours=(ipas[idx - 1] if idx else None,
                            ipas[idx + 1] if idx + 1 < len(ipas) else None),
                produced_confident=bool(p.get("produced_confident", True)))

            flag_th = getattr(self.bundle, "flag_threshold", 0.5)
            phones.append(PhoneResult(
                score=round(fused, 4), confidence=round(conf, 3),
                flag=("excused" if rule else
                      ("review" if conf < flag_th else "ok")),
                start_s=round(t0, 4), end_s=round(t1, 4),
                correlates=correlates, error_type=etype, error_why=ewhy,
                excused_by=rule, fusion=fuse_detail, **common))

        resp = build_response(
            utt_id, item["word"], phones, gate, prov,
            {"conditioning": cond, "free_decode": fd["string"][:64],
             "n_insertions": len(insertions),
             "alignment_quality": round(align_q, 4),
             "alignment_detail": align_detail,
             "uncalibrated": uncal,
             "scorer": "trained bundle" if self.bundle else "PREVIEW, uncalibrated",
             "correlates_enabled": self.correlates_enabled})
        resp["item"] = {k: item[k] for k in
                        ("word", "focus", "positions", "in_cluster",
                         "protocol_id", "protocol_version")}
        return resp
