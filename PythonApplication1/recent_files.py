#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Small, dependency-free helper module to manage a persistent recent-files MRU list.

Usage (example):
    import configparser
    cfg = configparser.ConfigParser()
    cfg.read(ini_path)
    from PythonApplication1 import recent_files as rf
    rf.add_recent_file(cfg, ini_path, "/path/to/file", on_update=my_refresh_cb)

The module is GUI-agnostic and uses a simple JSON encoded list stored in the
ConfigParser under section "Recent", key "files".
"""
from __future__ import annotations

import json
import os
from typing import Callable, Iterable, List, Optional

RECENT_MAX = 10


def ensure_recent_section(config) -> None:
    """Ensure the 'Recent' section exists in the given ConfigParser."""
    if not config.has_section("Recent"):
        config.add_section("Recent")


def load_recent_files(config) -> List[str]:
    """Return list of recent absolute file paths (may be empty)."""
    ensure_recent_section(config)
    try:
        raw = config.get("Recent", "files", fallback="[]")
        return json.loads(raw)
    except Exception:
        return []


def save_recent_files(config, ini_path: str, lst: Iterable[str]) -> None:
    """Persist list (iterable) into config under Recent/files as JSON string."""
    ensure_recent_section(config)
    try:
        config.set("Recent", "files", json.dumps(list(lst)))
        with open(ini_path, "w", encoding="utf-8") as fh:
            config.write(fh)
    except Exception:
        # Best-effort: don't crash caller for IO/config errors
        pass


def add_recent_file(
    config,
    ini_path: str,
    path: str,
    on_update: Optional[Callable[[], None]] = None,
    max_items: Optional[int] = None,
) -> None:
    """
    Add given path to the MRU, pushing it to front and truncating to max_items.
    If on_update is given it will be called after save (safely).
    """
    try:
        path = os.path.abspath(path)
        lst = load_recent_files(config)
        if path in lst:
            lst.remove(path)
        lst.insert(0, path)
        limit = max_items if max_items is not None else RECENT_MAX
        lst = lst[:limit]
        save_recent_files(config, ini_path, lst)
        if on_update:
            try:
                on_update()
            except Exception:
                pass
    except Exception:
        pass


def clear_recent_files(config, ini_path: str, on_update: Optional[Callable[[], None]] = None) -> None:
    """Clear persisted recent list and optionally call on_update."""
    save_recent_files(config, ini_path, [])
    if on_update:
        try:
            on_update()
        except Exception:
            pass