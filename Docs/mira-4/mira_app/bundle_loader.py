"""mira_app/bundle_loader.py - turn a Stage 2 output folder into a live scorer.

This is what ends preview mode. Point it at the folder Stage 2 wrote and Mira
starts using the model that was validated, through the calibrator that was fitted,
on the features that were selected.

IT VERIFIES BEFORE IT SERVES. A process that starts successfully with half a model
loaded is worse than one that refuses to start, because the failure then surfaces
as quietly wrong scores rather than as an error at boot.

THE FAILURE THIS FILE EXISTS TO PREVENT
---------------------------------------
An earlier version of the serving path loaded the trained scorer, the calibrator,
the feature list and the projection, and then used none of them. It scored with
raw goodness of pronunciation and a bare sigmoid, which is roughly the baseline
Stage 2 exists to beat, behind a manifest advertising Stage 2's thresholds.

Nothing failed. Every test passed. Every piece was correct and none of them was
connected. So `score_one` below is the single place a score is produced, and
`verify_wiring` asserts the artifacts are reachable from it.
"""

import hashlib
import json
import pathlib

import numpy as np

REQUIRED = ["manifest.json", "mira_scorer.joblib", "calibrator.json",
            "phone_token_map.json"]
OPTIONAL = ["mira_core.py", "hidden_projection.npz", "withholding_policy.json",
            "error_by_phoneme.csv", "accent_allowlist.json"]


class Bundle:
    def __init__(self, root, verify_core_hash=True):
        self.root = pathlib.Path(root)
        missing = [f for f in REQUIRED if not (self.root / f).exists()]
        if missing:
            raise FileNotFoundError(
                f"{self.root} is not a complete Stage 2 output. Missing: {missing}. "
                f"Run Stage 2 of the Module 1 notebook and point at its OUT folder.")

        self.manifest = json.loads((self.root / "manifest.json").read_text())
        self.present_optional = [f for f in OPTIONAL if (self.root / f).exists()]

        # The hash check that carries the comparability argument into production.
        # If the measurement code differs from the code the manifest was written
        # against, every threshold in it was calibrated for a different
        # measurement and none of them applies.
        self.core_sha256 = None
        core = self.root / "mira_core.py"
        if core.exists():
            self.core_sha256 = hashlib.sha256(core.read_bytes()).hexdigest()
            expected = self.manifest.get("mira_core_sha256")
            if verify_core_hash and expected and expected != self.core_sha256:
                raise ValueError(
                    f"mira_core.py in this bundle hashes to {self.core_sha256[:16]} "
                    f"and the manifest expects {str(expected)[:16]}. The thresholds "
                    f"in it were calibrated against different measurement code. "
                    f"Rebuild the bundle rather than overriding this.")

        import joblib
        self.scorer = joblib.load(self.root / "mira_scorer.joblib")
        cal = json.loads((self.root / "calibrator.json").read_text())
        self.phone_token_map = json.loads(
            (self.root / "phone_token_map.json").read_text())

        s3 = self.manifest.get("stage3_instructions", {})
        self.feature_cols = s3.get("feature_columns", [])
        self.flag_threshold = s3.get("flag_threshold",
                                     self.manifest.get("flag_threshold", 0.5))
        self.model_id = self.manifest.get("decode_model_id")

        self._a, self._b = cal.get("a"), cal.get("b")
        self.calibrated = self._a is not None and self._b is not None

        pm = self.phone_token_map.get("map", {}) or {}
        self.phone_ids = self.manifest.get("phone_ids") or sorted(
            {int(v) for v in pm.values() if v is not None})
        self.hidden_layer = self.manifest.get("hidden_layer", -1)

        self.projection = None
        proj = self.root / "hidden_projection.npz"
        if proj.exists():
            with np.load(proj) as z:
                key = "proj" if "proj" in z.files else z.files[0]
                self.projection = z[key]

        from .contracts import WithholdingPolicy
        pol = self.root / "withholding_policy.json"
        if pol.exists():
            p = json.loads(pol.read_text())
            self.policy = WithholdingPolicy(withheld_phonemes=p.get("withheld", []),
                                            mae_by_phoneme=p.get("mae", {}))
        else:
            self.policy = WithholdingPolicy()

        self.allow_list = None
        al = self.root / "accent_allowlist.json"
        if al.exists():
            from .mira_core import AccentAllowList
            self.allow_list = AccentAllowList.from_json(json.loads(al.read_text()))

        self.verify_wiring()

    # -- the one place a score is produced -----------------------------------

    def feature_row(self, gop, logprobs, lo, hi, target_id, hidden=None):
        """Exactly the columns Stage 2 built, from identical frames."""
        from . import mira_core

        row = {k: gop[k] for k in mira_core.GOP_VARIANTS if k in gop}
        row["n_frames"] = gop.get("n_frames")
        if self.phone_ids:
            lpp, lpr = mira_core.lpp_lpr_features(logprobs, lo, hi, target_id,
                                                  self.phone_ids)
            row["lpp"] = lpp
            if lpr is not None:
                cols = mira_core.lpr_column_names([str(p) for p in self.phone_ids])
                row.update(dict(zip(cols, lpr.tolist())))
        if hidden is not None and self.projection is not None:
            pooled = mira_core.pool_hidden(hidden, lo, hi)
            if pooled is not None:
                row.update({f"h_{i:03d}": float(v)
                            for i, v in enumerate((pooled @ self.projection).tolist())})
        return row

    def score_one(self, gop, logprobs, lo, hi, target_id, hidden=None,
                  strict=True):
        """The trained scorer. Refuses rather than imputing a missing feature.

        A model quietly fed a different feature set returns confident nonsense,
        and there is no symptom: the numbers look exactly like scores.
        """
        import pandas as pd

        row = self.feature_row(gop, logprobs, lo, hi, target_id, hidden)
        want = list(self.feature_cols)
        if not want:
            raise RuntimeError(
                "the manifest lists no feature columns, so there is no way to "
                "know what the scorer was trained on. Rebuild the bundle.")
        missing = [c for c in want if c not in row]
        if missing and strict:
            raise RuntimeError(
                f"cannot build {len(missing)} of the {len(want)} features the "
                f"scorer was trained on: {missing[:6]}"
                f"{' ...' if len(missing) > 6 else ''}. This usually means the "
                f"bundle came from a Stage 2 run with different USE_LPR / "
                f"USE_HIDDEN / USE_CONTEXT flags. Rebuild it; do not relax this.")
        for c in missing:
            row[c] = np.nan
        X = pd.DataFrame([row])[want]
        return float(np.asarray(self.scorer.predict(X), dtype=float)[0])

    def calibrate(self, raw):
        """Platt, with the parameters Stage 2 fitted."""
        r = np.asarray(raw, dtype=float)
        if not self.calibrated:
            return 1.0 / (1.0 + np.exp(-r))
        return 1.0 / (1.0 + np.exp(-(self._a * r + self._b)))

    def verify_wiring(self):
        """Assert the loaded artifacts are reachable from the scoring path.

        Crude, and it is the kind of check that catches this class of bug, which
        unit tests structurally cannot: every piece being individually correct is
        exactly the condition under which the connection is missing.
        """
        problems = []
        if not hasattr(self.scorer, "predict"):
            problems.append("the loaded scorer has no predict method")
        if not self.feature_cols:
            problems.append("the manifest lists no feature columns")
        if not self.calibrated:
            problems.append("no Platt parameters, so confidence will be a bare "
                            "sigmoid and every confidence threshold is meaningless")
        if not self.phone_ids:
            problems.append("no phone inventory, so the ratio features cannot "
                            "be built")
        if any(c.startswith("h_") for c in self.feature_cols) and self.projection is None:
            problems.append("the scorer was trained with projected hidden features "
                            "and hidden_projection.npz is absent")
        self.problems = problems
        if problems:
            raise ValueError(
                "this bundle cannot serve the model it contains:\n  - "
                + "\n  - ".join(problems))
        return True

    def provenance(self):
        return {
            "model_version": self.model_id,
            "aligner_version": self.manifest.get("mfa_version", "ctc_forced_align"),
            "protocol_version": self.manifest.get("notebook_version", "unknown"),
            "threshold_set_version": (f"platt_a{self._a:.4f}_b{self._b:.4f}"
                                      f"_flag{self.flag_threshold:.2f}"),
            "core_sha256": (self.core_sha256 or "not_in_bundle")[:16],
            "bundle_version": self.manifest.get("bundle_version", "stage2_output"),
        }

    def describe(self):
        return {"root": str(self.root), "model_id": self.model_id,
                "n_features": len(self.feature_cols), "calibrated": self.calibrated,
                "n_phone_ids": len(self.phone_ids),
                "projection": None if self.projection is None
                else list(self.projection.shape),
                "flag_threshold": self.flag_threshold,
                "n_withheld": len(self.policy.withheld),
                "optional_present": self.present_optional,
                "core_sha256": (self.core_sha256 or "absent")[:16]}


def load_bundle(root, verify_core_hash=True):
    b = Bundle(root, verify_core_hash=verify_core_hash)
    print("bundle loaded:", json.dumps(b.describe(), indent=2))
    return b
