# Copyright 2023-2026 The GAIA project contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
from urllib.parse import urlsplit

import requests


def _callback_headers(callback_url: str) -> dict:
    """The backend requires its API key on every request, including this
    callback. Engine modules run inside the backend container and inherit
    GAIA_API_KEY; it is only ever sent to the backend on the same machine."""
    key = os.environ.get("GAIA_API_KEY", "")
    host = (urlsplit(callback_url).hostname or "").lower()
    if key and host in ("localhost", "127.0.0.1", "::1"):
        return {"X-API-Key": key}
    return {}


def report_back(callback_url: str, success: bool, json_data) -> bool:
    """Post the terminal status to the backend. Returns True if it was delivered."""
    if callback_url is None:
        print("No callback URL provided. Skipping callback.")
        return True
    try:
        result = requests.post(
            callback_url,
            headers=_callback_headers(callback_url),
            json={
                "success": success,
                "error": {} if success else json_data,
                "additional_info": json_data if success else {},
            },
            timeout=15,
        )
        result.raise_for_status()
        print(f"Request successful. Status code: {result.status_code}")
        return True
    except requests.RequestException as e:
        print(f"Callback failed: {e}")
        return False
