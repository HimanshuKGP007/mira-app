"""mira_app/acoustics.py - the only part of Mira that needs a GPU or a download.

It is isolated behind one small interface for a reason. Everything else in the
app, the whole of mira_core, the whole of Module 2, the gates and the report, can
then be tested on a laptop in under a second against a synthetic decoder. That is
what makes the loop fast: the expensive component is one swappable object rather
than a dependency threaded through every function.

    class PhoneDecoder:
        vocab      dict, phone symbol -> token id
        blank_id   int
        logprobs(audio, sr) -> np.ndarray of shape [frames, vocab]

Two implementations ship. Wav2Vec2Decoder is the real one. SyntheticDecoder
fabricates log-probabilities from a phone sequence you specify, which is how the
end-to-end tests run without a model, and how the demo runs on a machine with no
GPU and no network.

NO FORCED ALIGNER IS REQUIRED. The Montreal Forced Aligner is more accurate and it
needs a dictionary, a pronunciation model, a corpus directory layout and several
minutes per batch. mira_core.ctc_forced_align does the same job from the
log-probabilities that are already in memory, with no extra dependency. It is less
precise, and that imprecision is reported as alignment quality rather than hidden.
"""

import numpy as np

MODEL_ID = "facebook/wav2vec2-lv-60-espeak-cv-ft"
# Chosen because it outputs PHONES rather than letters. A normal speech recogniser
# is trained to work out which word you meant, so it corrects mispronunciations on
# the way and the error disappears. This one has no word-level notion at all.


class Wav2Vec2Decoder:
    """The real acoustic model. Downloads once, then runs offline.

    Loading is deferred to __init__ rather than import, so `import mira_app` costs
    nothing on a machine that only wants the protocol or the report layer.
    """

    def __init__(self, model_id=MODEL_ID, device=None):
        import torch
        from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor

        self.model_id = model_id
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.processor = Wav2Vec2Processor.from_pretrained(model_id)
        self.model = Wav2Vec2ForCTC.from_pretrained(model_id).to(self.device).eval()
        self.vocab = self.processor.tokenizer.get_vocab()
        self.blank_id = self.processor.tokenizer.pad_token_id
        self._torch = torch

    def logprobs(self, audio, sr):
        torch = self._torch
        inputs = self.processor([np.asarray(audio, dtype=np.float32)],
                                sampling_rate=sr, return_tensors="pt", padding=True)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        with torch.no_grad():
            logits = self.model(**inputs).logits
        return torch.log_softmax(logits[0].float(), dim=-1).cpu().numpy()


class SyntheticDecoder:
    """A decoder that fabricates a plausible frame sequence from phones you give it.

    This exists to test the wiring, not the acoustics. It cannot tell you whether
    the model is any good. It can tell you that a substitution travels correctly
    from the decode, through attribution, through error typing, through the
    alphabet conversion, into the phonological process table, and out into the
    report, which is the failure mode that actually bit this project.

    `produce` is what the speaker "said". Pass something different from the target
    and the whole chain should register a substitution.
    """

    def __init__(self, symbols, blank="<pad>", frames_per_phone=8, confidence=0.85,
                 seed=0):
        syms = [blank] + [s for s in symbols if s != blank]
        self.vocab = {s: i for i, s in enumerate(syms)}
        self.blank_id = 0
        self.frames_per_phone = frames_per_phone
        self.confidence = confidence
        self.rng = np.random.default_rng(seed)
        self.model_id = "synthetic"
        self._produce = None

    def set_production(self, produced_symbols):
        """What the next call to logprobs() should sound like."""
        self._produce = list(produced_symbols)
        return self

    def logprobs(self, audio, sr):
        if not self._produce:
            raise RuntimeError(
                "SyntheticDecoder needs set_production([...]) before it can decode. "
                "It fabricates frames from a phone sequence; it does not listen.")
        V = len(self.vocab)
        rows = []
        for sym in self._produce:
            tid = self.vocab.get(sym)
            for _ in range(self.frames_per_phone):
                p = np.full(V, (1.0 - self.confidence) / max(V - 1, 1))
                if tid is not None:
                    p[tid] = self.confidence
                else:
                    # A phone outside the vocabulary comes out as diffuse
                    # probability, which is exactly what an unrecognisable
                    # production looks like to a real model.
                    p = np.full(V, 1.0 / V)
                rows.append(p)
            # a blank between phones, as CTC produces
            b = np.full(V, (1.0 - self.confidence) / max(V - 1, 1))
            b[self.blank_id] = self.confidence
            rows.append(b)
        return np.log(np.clip(np.array(rows), 1e-9, 1.0))


def default_vocab_symbols():
    """The IPA symbols the espeak-based model emits for English, enough to build a
    synthetic decoder that covers the whole starter protocol."""
    return ["s", "z", "ʃ", "ʒ", "tʃ", "dʒ", "f", "v", "θ", "ð", "h",
            "p", "b", "t", "d", "k", "ɡ", "m", "n", "ŋ", "l", "ɹ", "w", "j",
            "i", "ɪ", "e", "ɛ", "æ", "ʌ", "ə", "ɑ", "ɔ", "o", "ʊ", "u", "ɚ",
            "aɪ", "aʊ", "ɔɪ", "eɪ", "oʊ"]
