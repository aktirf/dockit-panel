"""Lightweight localization (ru / en / uk) with zero external dependencies.

Translations live in `dockit/core/locales/<lang>.json` as flat snake_case keys so both
Python (`viewmodel`, `tray`, `backend`) and QML (`Theme.tr("key")`) share one source
of truth with O(1) dict lookup and instant live language switching.
"""

from __future__ import annotations

import functools
import json
import os
from pathlib import Path

SUPPORTED = ("ru", "en", "uk")
DEFAULT_LANG = "ru"
LOCALES_DIR = Path(__file__).resolve().parent / "locales"


def detect_system_lang(env: dict[str, str] | None = None) -> str:
    """Pick 'uk', 'ru', or 'en' from standard POSIX locale env vars."""
    source = os.environ if env is None else env
    for var in ("LC_ALL", "LC_MESSAGES", "LANG"):
        raw = (source.get(var) or "").strip().lower()
        if not raw or raw in ("c", "posix"):
            continue
        code = raw.split(".", 1)[0].split("_", 1)[0].split("-", 1)[0]
        if code == "uk":
            return "uk"
        if code == "ru":
            return "ru"
        return "en"
    return DEFAULT_LANG


def resolve_lang(setting: str | None, env: dict[str, str] | None = None) -> str:
    """Turn user setting ('auto' | 'ru' | 'en' | 'uk') into a concrete language code."""
    if setting in SUPPORTED:
        return setting
    return detect_system_lang(env)


@functools.lru_cache(maxsize=8)
def load_catalog(lang: str) -> dict[str, str]:
    """Load and cache one locale JSON file; falls back to Russian for missing keys."""
    base_path = LOCALES_DIR / f"{DEFAULT_LANG}.json"
    base: dict[str, str] = json.loads(base_path.read_text(encoding="utf-8"))
    if lang == DEFAULT_LANG or lang not in SUPPORTED:
        return base
    path = LOCALES_DIR / f"{lang}.json"
    if not path.is_file():
        return base
    merged = dict(base)
    merged.update(json.loads(path.read_text(encoding="utf-8")))
    return merged


def catalog(lang: str) -> dict[str, str]:
    """Plain dict copy for QML (Theme.t)."""
    return dict(load_catalog(lang))


def tr(key: str, lang: str = DEFAULT_LANG, **kwargs) -> str:
    """Translate `key` into `lang`, optionally formatting `{placeholders}`."""
    text = load_catalog(lang).get(key, key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, ValueError):
            return text
    return text
