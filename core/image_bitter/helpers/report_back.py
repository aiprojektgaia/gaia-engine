import os
from urllib.parse import urlsplit

import requests
from requests import Timeout, HTTPError, RequestException

from helpers.logger import log


def _callback_headers(callback_url: str) -> dict:
    """The backend requires its API key on every request, including this
    callback. Engine modules run inside the backend container and inherit
    GAIA_API_KEY; it is only ever sent to the backend on the same machine."""
    key = os.environ.get("GAIA_API_KEY", "")
    host = (urlsplit(callback_url).hostname or "").lower()
    if key and host in ("localhost", "127.0.0.1", "::1"):
        return {"X-API-Key": key}
    return {}


def report_back(callback_url: str, success:bool, json_data) -> None:
    if callback_url is None:
        log("No callback URL provided. Skipping callback.")
        return
    try:
        result = requests.post(
            callback_url,
            headers=_callback_headers(callback_url),
            json={
                "success":success,
                "error": {} if success is True else json_data,
                "additional_info": json_data if success is True else {},
            },  # Use json parameter instead of manually dumping
            timeout=15,
        )
        result.raise_for_status()
        log(f"Request successful. Status code: {result.status_code}")
    except Timeout:
        log("Request timed out. The server might be slow or unresponsive.")
    except HTTPError as e:
        if e.response.status_code == 422:
            log(
                "HTTP 422 Unprocessable Entity: The server rejected the data due to validation errors."
            )
            log(f"Response content: {e.response.text}")
        else:
            log(f"HTTP error occurred: {e}")
    except RequestException as e:
        log(f"An error occurred while making the request: {e}")