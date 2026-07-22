"""Script-driven local media mixer.

The package plans edits from narration text and a local media catalog.
External software and model locations are discovered at runtime.
"""

from .pipeline import ScriptMixerPipeline

__all__ = ["ScriptMixerPipeline"]
