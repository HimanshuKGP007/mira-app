"""mira_app/cli.py - run Mira from a terminal.

    python -m mira_app check                     what this install can do
    python -m mira_app words                     the protocol
    python -m mira_app demo                      end to end, no model, no network
    python -m mira_app score sun.wav --word sun  one recording
    python -m mira_app session recordings/       a folder of <word>.wav
    python -m mira_app serve                     the browser interface

`demo` is the one to run first. It uses the synthetic decoder, so it needs no
model download, no GPU and no network, and it exercises the entire chain from
audio conditioning through to the HTML report. If it works, every part of Mira
except the acoustic model itself is working on this machine.
"""

import argparse
import json
import pathlib
import sys

import numpy as np

from . import protocol as proto
from . import report as rpt
from . import session as sess
from .acoustics import SyntheticDecoder, default_vocab_symbols
from .score import MiraEngine


def _load_audio(path):
    try:
        import librosa
    except ImportError:
        raise SystemExit("reading audio needs librosa: pip install librosa soundfile")
    a, sr = librosa.load(str(path), sr=16000, mono=True)
    return a, sr


def _real_engine(bundle_dir=None, correlates=False):
    from .acoustics import Wav2Vec2Decoder
    bundle = None
    if bundle_dir:
        sys.path.insert(0, str(pathlib.Path(bundle_dir).parent))
        from .bundle_loader import load_bundle
        bundle = load_bundle(bundle_dir)
    return MiraEngine(Wav2Vec2Decoder(), bundle=bundle,
                      correlates_enabled=correlates)


def _synthetic_engine():
    return MiraEngine(SyntheticDecoder(default_vocab_symbols()))


# =============================================================================


def cmd_check(args):
    eng = _synthetic_engine()
    r = eng.readiness()
    print(json.dumps(r, indent=2))
    print()
    if r["mode"] == "preview":
        print("MODE: preview. There is no trained scorer, so scores come from a")
        print("crude map over goodness of pronunciation and confidence is")
        print("uncalibrated. Good enough to demonstrate the product. Not good")
        print("enough to show a clinician.")
        print()
        print("To leave preview mode, run Stage 2 of the Module 1 notebook, then")
        print("pass its output folder with --bundle.")
    from . import mira_core, mira_module2a, mira_module2b
    from . import contracts
    print("\nself tests")
    for name, mod in [("mira_core", mira_core), ("contracts", contracts),
                      ("module 2A", mira_module2a), ("module 2B", mira_module2b)]:
        print(f"  {name:12s} {mod.self_test(False)} assertions")


def cmd_words(args):
    print(f"{proto.PROTOCOL_ID} {proto.PROTOCOL_VERSION}, "
          f"{len(proto.WORDS)} items\n")
    for w, phones, focus in proto.WORDS:
        pos = proto.position_tags(phones)
        tagged = " ".join(f"{p}" + (f"[{x[0]}]" if x else "")
                          for p, x in zip(phones, pos))
        print(f"  {w:10s} {focus:14s} {tagged}")
    print("\nconsonant coverage by position")
    grid = proto.coverage()
    for ph in sorted(grid):
        cells = " ".join(f"{p}:{grid[ph].get(p, 0)}"
                         for p in ("initial", "medial", "final"))
        gaps = [p for p in ("initial", "medial", "final") if not grid[ph].get(p)]
        print(f"  {ph:4s} {cells:42s}"
              + (f"  MISSING {', '.join(gaps)}" if gaps else ""))
    print("\nA sound with a missing position cannot be reported on in that")
    print("position, and the report must not imply otherwise. Filling these gaps")
    print("is linguistic work and needs no model.")


def cmd_demo(args):
    """The whole chain, with no model and no network."""
    eng = _synthetic_engine()
    dec = eng.decoder
    rng = np.random.default_rng(args.seed)

    # A speaker who stops fricatives and glides liquids: the textbook pattern,
    # and the one every phonological process table is built to detect.
    substitutions = {"s": "t", "z": "d", "ʃ": "s", "θ": "t", "ð": "d", "ɹ": "w"}
    if args.clean:
        substitutions = {}

    words = args.words or [w for w, _, _ in proto.WORDS][:args.n]
    responses = []
    print(f"scoring {len(words)} items with the synthetic decoder"
          + ("" if args.clean else ", simulating stopping and gliding"))
    for w in words:
        item = proto.get_item(w)
        ipas = [eng.arp_to_ipa[a] for a in item["phones"]]
        dec.set_production([substitutions.get(i, i) for i in ipas])
        # The audio is noise: the synthetic decoder ignores it and fabricates
        # frames from the phone sequence above. Everything downstream of the
        # forward pass is real.
        audio = rng.normal(0, 0.1, 16000).astype(np.float32)
        r = eng.score(audio, 16000, w)
        responses.append(r)
        n_err = sum(1 for p in r["phones"]
                    if p.get("error_type") not in (None, "correct"))
        print(f"  {w:10s} {r['status']:7s} {len(r['phones'])} sounds, "
              f"{n_err} not correct")

    _finish(responses, args)


def cmd_score(args):
    eng = _real_engine(args.bundle, args.correlates)
    audio, sr = _load_audio(args.audio)
    r = eng.score(audio, sr, args.word, capture_context=args.context)
    print(json.dumps(r, indent=2, default=str))


def cmd_session(args):
    eng = _real_engine(args.bundle, args.correlates)
    folder = pathlib.Path(args.folder)
    files = sorted(p for p in folder.iterdir()
                   if p.suffix.lower() in (".wav", ".flac", ".mp3", ".m4a"))
    if not files:
        raise SystemExit(f"no audio files in {folder}")
    responses = []
    for p in files:
        word = p.stem.split("_")[0].lower()
        try:
            proto.get_item(word)
        except KeyError as e:
            print(f"  skipping {p.name}: {e}")
            continue
        audio, sr = _load_audio(p)
        r = eng.score(audio, sr, word, capture_context=args.context)
        responses.append(r)
        print(f"  {word:10s} {r['status']}")
    _finish(responses, args)


def _finish(responses, args):
    speaker = {"sex": args.sex, "age_months": args.age_months,
               "hearing_status": "not_assessed"}
    analysis = sess.analyse(responses, speaker=speaker,
                            uncalibrated=not getattr(args, "bundle", None))
    narration = sess.narrate(analysis, register=args.register)

    acc = analysis["accuracy"]
    print("\n" + "=" * 62)
    print(f"  consonants correct  {acc['pcc']['pct'] or 0:.1f}%  "
          f"({acc['pcc']['n']} of {acc['pcc']['d']})")
    print(f"  vowels correct      {acc['pvc']['pct'] or 0:.1f}%")
    print(f"  coverage            {acc['coverage']['pct'] or 0:.1f}%  "
          f"({acc['n_held']} held)")
    applied = {k: v for k, v in analysis["processes"].items()
               if isinstance(v, dict) and (v.get("n") or 0) > 0}
    if applied:
        print("  patterns")
        for k, v in sorted(applied.items(), key=lambda kv: -kv[1]["n"]):
            print(f"      {k.replace('_', ' '):26s} {v['n']} of {v['d']}")
    print("=" * 62)
    if narration["use_narrative"]:
        print("\n" + narration["text"])
    else:
        print("\nnarration failed verification and was dropped; the tables stand "
              "on their own")

    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    rpt.save(analysis, out, narration)
    rpt.save_json(analysis, out.with_suffix(".json"), narration)
    print(f"\nreport  {out}")
    print(f"data    {out.with_suffix('.json')}")


def cmd_serve(args):
    from .server import run
    run(host=args.host, port=args.port, bundle=args.bundle,
        synthetic=args.synthetic)


# =============================================================================


def main(argv=None):
    ap = argparse.ArgumentParser(prog="mira_app", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p, with_bundle=True):
        if with_bundle:
            p.add_argument("--bundle", help="a Stage 2 output folder. Without it, "
                                            "Mira runs in uncalibrated preview mode")
        p.add_argument("--out", default="mira_report.html")
        p.add_argument("--register", default="clinician",
                       choices=["clinician", "caregiver"])
        p.add_argument("--sex", default="m", choices=["m", "f"])
        p.add_argument("--age-months", type=int, default=None, dest="age_months",
                       help="needed before any age norm can be applied. Without "
                            "it the correlate path refuses to normalise")
        p.add_argument("--context", default="home", choices=["home", "clinic"])
        p.add_argument("--correlates", action="store_true",
                       help="measure formants, spectral moments and voice onset "
                            "time. Reference ranges are UNVALIDATED")

    p = sub.add_parser("check", help="what this install can do")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("words", help="the protocol and its coverage")
    p.set_defaults(func=cmd_words)

    p = sub.add_parser("demo", help="end to end with no model and no network")
    common(p, with_bundle=False)
    p.add_argument("--bundle", default=None, help=argparse.SUPPRESS)
    p.add_argument("-n", type=int, default=14, help="how many protocol items")
    p.add_argument("--words", nargs="*", help="specific words instead")
    p.add_argument("--clean", action="store_true",
                   help="simulate a speaker with no errors, as a control")
    p.add_argument("--seed", type=int, default=0)
    p.set_defaults(func=cmd_demo)

    p = sub.add_parser("score", help="one recording")
    p.add_argument("audio")
    p.add_argument("--word", required=True)
    common(p)
    p.set_defaults(func=cmd_score)

    p = sub.add_parser("session", help="a folder of <word>.wav files")
    p.add_argument("folder")
    common(p)
    p.set_defaults(func=cmd_session)

    p = sub.add_parser("serve", help="the browser interface")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--bundle", default=None)
    p.add_argument("--synthetic", action="store_true",
                   help="run without the acoustic model, for a UI demo")
    p.set_defaults(func=cmd_serve)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    main()
