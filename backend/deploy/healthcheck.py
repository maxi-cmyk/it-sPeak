"""Container liveness probe for the FastAPI process."""

from __future__ import annotations

import json
import os
from urllib.request import urlopen


def main() -> None:
    port = os.getenv("PORT", "8000")
    with urlopen(f"http://127.0.0.1:{port}/healthz", timeout=3) as response:
        payload = json.load(response)
        if response.status != 200 or payload.get("status") != "ok":
            raise SystemExit(1)


if __name__ == "__main__":
    main()
