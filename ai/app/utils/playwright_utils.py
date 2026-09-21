"""Playwright helpers shared by interaction/scan services."""
import os
from typing import Any, Dict


def chromium_launch_kwargs(**overrides: Any) -> Dict[str, Any]:
    """
    Build kwargs for chromium.launch().

    If PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH is set, use that Chromium binary
    instead of Playwright's bundled browser.
    """
    kwargs: Dict[str, Any] = {
        "args": [
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
        ],
    }
    executable = os.getenv("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH")
    if executable:
        kwargs["executable_path"] = executable
    kwargs.update(overrides)
    return kwargs
