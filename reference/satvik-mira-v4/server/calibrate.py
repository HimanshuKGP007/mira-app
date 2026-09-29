"""
calibrate.py — manual threshold check, no model changes, no training.

Scores a folder of labeled .wav recordings and shows whether the current
FLAG_THRESHOLD in policy.py actually separates "correct" from "wrong" takes.
This is the entire calibration procedure this app uses: pick the one number
that draws a clean line through real recordings.

Usage:
    cd server
    python calibrate.py path/to/recordings/

File naming (case-insensitive), anything else is skipped with a warning:
    <word>__correct__<anything>.wav      e.g. sun__correct__1.wav
    <word>__wrong__<anything>.wav        e.g. sun__wrong__1.wav

Prints one row per file: word, label, marking, confidence, and whether the
marking matched the label. Ends with a summary and, if the current threshold
is misplaced, the confidence value that would fix it.
"""

import pathlib
import sys

import policy
import scorer


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        raise SystemExit(1)
    folder = pathlib.Path(sys.argv[1])
    if not folder.is_dir():
        raise SystemExit("not a directory: %s" % folder)

    files = sorted(folder.glob("*.wav"))
    if not files:
        raise SystemExit("no .wav files in %s" % folder)

    scorer.load()
    print("threshold in use: MIRA_FLAG_THRESHOLD = %.2f\n" % policy.FLAG_THRESHOLD)
    print("%-28s %-8s %-13s %-10s %s" % ("file", "label", "marking", "conf", "ok?"))
    print("-" * 70)

    rows = []
    for f in files:
        parts = f.stem.split("__")
        if len(parts) < 2 or parts[1].lower() not in ("correct", "wrong"):
            print("%-28s SKIPPED (name it <word>__correct__.. or <word>__wrong__..)" % f.name)
            continue
        word, label = parts[0], parts[1].lower()

        raw = f.read_bytes()
        result = scorer.score_utterance(raw, word)
        if result.get("status") == "retry":
            print("%-28s %-8s RETRY (%s)" % (f.name, label, result.get("reason")))
            continue

        target_phones = [p for p in result.get("phones", []) if p["target_arpabet"]]
        # the phone actually under test: the /s/-family target, first match
        target = next((p for p in target_phones if p["target"] in ("s", "z")), None)
        if target is None:
            print("%-28s %-8s no /s/ in this word's targets, skipping" % (f.name, label))
            continue

        marking = target["marking"]
        conf = target["confidence"]
        expect_correct = label == "correct"
        got_correct = marking == "correct"
        ok = "OK" if expect_correct == got_correct else "MISMATCH"
        print("%-28s %-8s %-13s %-10s %s" %
              (f.name, label, marking, "%.3f" % conf if conf is not None else "-", ok))
        if conf is not None:
            rows.append((label, conf))

    if not rows:
        print("\nNo usable rows scored.")
        return

    correct_confs = sorted(c for l, c in rows if l == "correct")
    wrong_confs = sorted(c for l, c in rows if l == "wrong")
    print("\n--- summary ---")
    if correct_confs:
        print("correct takes: min %.3f  max %.3f  (n=%d)" %
              (correct_confs[0], correct_confs[-1], len(correct_confs)))
    if wrong_confs:
        print("wrong takes:   min %.3f  max %.3f  (n=%d)" %
              (wrong_confs[0], wrong_confs[-1], len(wrong_confs)))

    if correct_confs and wrong_confs:
        gap_lo, gap_hi = wrong_confs[-1], correct_confs[0]
        if gap_lo < gap_hi:
            suggestion = (gap_lo + gap_hi) / 2
            print("\nThe two groups separate cleanly. A threshold anywhere between "
                  "%.3f and %.3f works; try MIRA_FLAG_THRESHOLD=%.3f" %
                  (gap_lo, gap_hi, suggestion))
        else:
            print("\nThe two groups OVERLAP (worst correct take scored %.3f, best wrong "
                  "take scored %.3f) — no single threshold separates them cleanly on "
                  "this sample. Re-record the ambiguous ones or accept some error at "
                  "the current threshold." % (correct_confs[0], wrong_confs[-1]))


if __name__ == "__main__":
    main()
