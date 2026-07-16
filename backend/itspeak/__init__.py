"""it'sPEAK — AI-powered public speaking coach.

Core analysis and coaching package.

Modules
-------
- ``models``   : Shared Pydantic contracts that decouple the layers.
- ``config``   : Archetype presets + raw-metric -> 0-100 normalization.
- ``api``      : FastAPI upload and polling endpoints.
- ``jobs``     : Celery orchestration for combined reports.
- ``pipeline`` : ffmpeg frame extraction and MediaPipe analysis loops.
- ``audio``    : Librosa metrics and OpenAI transcription.
- ``coaching`` : LLM communication layer + structured system prompts.
"""

__version__ = "0.1.0"
