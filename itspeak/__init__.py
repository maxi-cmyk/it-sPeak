"""it'sPEAK — AI-powered public speaking coach.

Core analysis and coaching package.

Modules
-------
- ``models``   : Shared Pydantic contracts that decouple the layers.
- ``config``   : Archetype presets + raw-metric -> 0-100 normalization.
- ``pipeline`` : FastAPI endpoints, Celery task, MediaPipe analysis loops.
- ``coaching`` : LLM communication layer + structured system prompts.
"""

__version__ = "0.1.0"
