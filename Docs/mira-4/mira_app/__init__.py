"""Mira: phoneme-level speech scoring (Module 1) and clinical analytics (Module 2).

    from mira_app import MiraEngine, SyntheticDecoder, protocol, session

Nothing here imports torch at package level, so importing mira_app on a laptop
with no GPU and no model download costs nothing.
"""
from . import protocol, session, mira_core
from .score import MiraEngine
from .acoustics import SyntheticDecoder, default_vocab_symbols

__all__ = ["MiraEngine", "SyntheticDecoder", "default_vocab_symbols",
           "protocol", "session", "mira_core"]
__version__ = "0.1.0"
