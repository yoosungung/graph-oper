"""Backend settings."""

from __future__ import annotations

import os
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_DB = _REPO_ROOT / "police-case-kuzu" / "sample.db"


def db_path() -> Path:
    override = os.environ.get("KUZU_DB_PATH")
    return Path(override) if override else _DEFAULT_DB


def langchain_model() -> str:
    return os.environ.get("LANGCHAIN_MODEL", "google_genai:gemma-4-31b-it")


def google_api_key() -> str | None:
    key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    return key if key else None
