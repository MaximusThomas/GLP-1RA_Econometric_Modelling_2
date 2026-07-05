"""
Shared helpers for the data-pulling scripts (01-03).

Kept separate from config.py because this is behaviour (HTTP + caching),
not constants. All three pull scripts hit flaky-but-legitimate government
endpoints, so retry-with-backoff lives here once instead of being
copy-pasted three times.
"""

import time
from pathlib import Path

import requests


def get_with_retry(url: str, params: dict | None = None, retries: int = 4, timeout: int = 30) -> requests.Response:
    """GET a URL, retrying on timeouts/connection errors with exponential backoff.

    Government data endpoints in this project (census.gov especially) were
    observed to intermittently hang or drop connections during development;
    a single retry attempt was not always enough.
    """
    last_exc = None
    for attempt in range(retries):
        try:
            resp = requests.get(url, params=params, timeout=timeout)
            resp.raise_for_status()
            return resp
        except (requests.exceptions.RequestException,) as exc:
            last_exc = exc
            if attempt < retries - 1:
                wait = 2 ** (attempt + 1)
                time.sleep(wait)
    raise last_exc


def cached_get_text(cache_path: Path, url: str, params: dict | None = None) -> str:
    """Return cached text if present on disk, otherwise fetch and cache it."""
    if cache_path.exists():
        return cache_path.read_text()
    resp = get_with_retry(url, params=params)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(resp.text)
    return resp.text
