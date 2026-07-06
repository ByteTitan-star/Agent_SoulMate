"""Pytest bootstrap: configure Django before any test module imports it.

We configure Django manually (rather than via pytest-django) so the test suite
stays dependency-light. ``pythonpath = ["backend"]`` (see pyproject.toml) makes
``config``, ``core`` and ``skills`` importable.
"""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()
