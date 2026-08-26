"""Pytest bootstrap for Django.

Prefer pytest-django's settings discovery via pyproject.toml
(`DJANGO_SETTINGS_MODULE`). Keep this module as a lightweight fallback for
local runs that still import Django early.
"""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
