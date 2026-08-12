"""mira_app/protocol.py - the words Mira asks for, and what they should sound like.

WHY A FIXED WORD LIST RATHER THAN A DICTIONARY LOOKUP
-----------------------------------------------------
Mira only listens to words it already asked you to say. That is the whole design:
because the target is known in advance, the question stops being "which word was
that" and becomes "how well was this sound produced", which is the only question
that can be answered per sound.

A general grapheme-to-phoneme model would let a user type any word. It would also
introduce a second source of error nobody can see: when the pronunciation guess is
wrong, every sound in the word scores as an error and the recording looks like a
severe articulation problem. A fixed protocol removes that failure mode entirely,
and it is what a clinical instrument uses anyway.

WHAT MAKES A PROTOCOL GOOD
--------------------------
Phoneme balanced: every consonant appears. Position balanced: every consonant
appears initially, medially and finally where the language allows it. This one is
neither, yet. It is a starter set built for the adult intelligibility use case,
weighted toward the sounds that carry that: sibilants, rhotics, stop voicing and
the clusters that break down first.

Building a properly balanced protocol with pictures and accepted alternates is
linguistic work rather than machine learning, and it can be done today by a person
with no model. It is the highest-value non-code task on the list.

ARPABET, NOT IPA
----------------
Targets are stored in ARPABET because that is what the clinical literature and the
phonological process tables use, and because Module 2A consumes it directly. The
acoustic layer converts to IPA on the way in, via mira_core.canonical_ipa.
Stress digits are kept: AH0 is schwa and AH1 is not, and that distinction is the
single most common vowel decision in English.
"""

# (word, [ARPABET phones], focus)
# `focus` is the sound the item was chosen to probe. It is used to order the
# report, never to weight the score: a word that was chosen for /s/ still scores
# every sound in it.
WORDS = [
    ("sun",      ["S", "AH1", "N"],                       "S"),
    ("bus",      ["B", "AH1", "S"],                       "S"),
    ("whistle",  ["W", "IH1", "S", "AH0", "L"],           "S"),
    ("zoo",      ["Z", "UW1"],                            "Z"),
    ("nose",     ["N", "OW1", "Z"],                       "Z"),
    ("shoe",     ["SH", "UW1"],                           "SH"),
    ("fish",     ["F", "IH1", "SH"],                      "SH"),
    ("measure",  ["M", "EH1", "ZH", "ER0"],               "ZH"),
    ("chair",    ["CH", "EH1", "R"],                      "CH"),
    ("watch",    ["W", "AA1", "CH"],                      "CH"),
    ("jump",     ["JH", "AH1", "M", "P"],                 "JH"),
    ("bridge",   ["B", "R", "IH1", "JH"],                 "JH"),
    ("rabbit",   ["R", "AE1", "B", "IH0", "T"],           "R"),
    ("carrot",   ["K", "EH1", "R", "AH0", "T"],           "R"),
    ("water",    ["W", "AO1", "T", "ER0"],                "ER"),
    ("bird",     ["B", "ER1", "D"],                       "ER"),
    ("lamp",     ["L", "AE1", "M", "P"],                  "L"),
    ("yellow",   ["Y", "EH1", "L", "OW0"],                "L"),
    ("ball",     ["B", "AO1", "L"],                       "L"),
    ("think",    ["TH", "IH1", "NG", "K"],                "TH"),
    ("bath",     ["B", "AE1", "TH"],                      "TH"),
    ("this",     ["DH", "IH1", "S"],                      "DH"),
    ("feather",  ["F", "EH1", "DH", "ER0"],               "DH"),
    ("van",      ["V", "AE1", "N"],                       "V"),
    ("five",     ["F", "AY1", "V"],                       "V"),
    ("phone",    ["F", "OW1", "N"],                       "F"),
    ("pig",      ["P", "IH1", "G"],                       "P"),
    ("cup",      ["K", "AH1", "P"],                       "P"),
    ("boat",     ["B", "OW1", "T"],                       "B"),
    ("table",    ["T", "EY1", "B", "AH0", "L"],           "T"),
    ("dog",      ["D", "AO1", "G"],                       "D"),
    ("key",      ["K", "IY1"],                            "K"),
    ("book",     ["B", "UH1", "K"],                       "K"),
    ("goat",     ["G", "OW1", "T"],                       "G"),
    ("hat",      ["HH", "AE1", "T"],                      "HH"),
    ("mouse",    ["M", "AW1", "S"],                       "M"),
    ("ring",     ["R", "IH1", "NG"],                      "NG"),
    # clusters, which break down before singletons do and are where adult
    # residual errors concentrate
    ("spoon",    ["S", "P", "UW1", "N"],                  "S-cluster"),
    ("street",   ["S", "T", "R", "IY1", "T"],             "S-cluster"),
    ("school",   ["S", "K", "UW1", "L"],                  "S-cluster"),
    ("blue",     ["B", "L", "UW1"],                       "L-cluster"),
    ("green",    ["G", "R", "IY1", "N"],                  "R-cluster"),
    ("thread",   ["TH", "R", "EH1", "D"],                 "R-cluster"),
    ("clothes",  ["K", "L", "OW1", "Z"],                  "L-cluster"),
    ("desks",    ["D", "EH1", "S", "K", "S"],             "final-cluster"),
]

PROTOCOL_ID = "mira-adult-intelligibility"
PROTOCOL_VERSION = "0.1.0"

VOWELS = {"AA", "AE", "AH", "AO", "AW", "AY", "EH", "ER", "EY",
          "IH", "IY", "OW", "OY", "UH", "UW"}


def _base(p):
    return "".join(c for c in str(p) if not c.isdigit())


def is_vowel(p):
    return _base(p) in VOWELS


def position_tags(phones):
    """initial / medial / final, per consonant, from the word structure.

    Carried from the lexicon rather than inferred from the audio, which is the
    only way it can be trusted. Vowels get None: word position is a consonant
    construct in every clinical table that uses it.

    'initial' means the first consonant of the word, including the first member
    of an initial cluster. 'final' means the last. Everything between is medial.
    """
    idx = [i for i, p in enumerate(phones) if not is_vowel(p)]
    out = [None] * len(phones)
    if not idx:
        return out
    first_vowel = next((i for i, p in enumerate(phones) if is_vowel(p)), len(phones))
    last_vowel = next((i for i in range(len(phones) - 1, -1, -1)
                       if is_vowel(phones[i])), -1)
    for i in idx:
        if i < first_vowel:
            out[i] = "initial"
        elif i > last_vowel:
            out[i] = "final"
        else:
            out[i] = "medial"
    return out


def cluster_flags(phones):
    """True when the consonant sits next to another consonant on the same side of
    a vowel. Cluster reduction is scored against cluster opportunities only, so
    without this the process rate has the wrong denominator."""
    out = []
    for i, p in enumerate(phones):
        if is_vowel(p):
            out.append(False)
            continue
        prev_c = i > 0 and not is_vowel(phones[i - 1])
        next_c = i + 1 < len(phones) and not is_vowel(phones[i + 1])
        out.append(bool(prev_c or next_c))
    return out


def get_item(word):
    """One protocol item, fully tagged. Raises on an unknown word rather than
    guessing a pronunciation, which is the whole point of a fixed protocol."""
    for w, phones, focus in WORDS:
        if w == word.lower().strip():
            return {"word": w, "phones": list(phones), "focus": focus,
                    "positions": position_tags(phones),
                    "in_cluster": cluster_flags(phones),
                    "protocol_id": PROTOCOL_ID,
                    "protocol_version": PROTOCOL_VERSION}
    raise KeyError(
        f"{word!r} is not in the {PROTOCOL_ID} protocol. Mira only scores words "
        f"it asked for, because a guessed pronunciation makes every sound in the "
        f"word look wrong. Add it to protocol.WORDS with its ARPABET form.")


def words():
    return [w for w, _, _ in WORDS]


def coverage():
    """Which consonants the protocol probes, and in which positions. Prints the
    holes, because a protocol that never elicits /ZH/ finally cannot report on
    it and the report must not imply otherwise."""
    grid = {}
    for w, phones, _ in WORDS:
        for p, pos in zip(phones, position_tags(phones)):
            if pos is None:
                continue
            grid.setdefault(_base(p), {}).setdefault(pos, 0)
            grid[_base(p)][pos] += 1
    return grid
