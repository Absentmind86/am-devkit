"""AM-DevKit Python core package."""

from __future__ import annotations

import sys
from pathlib import Path

# Repo root is the parent of this package directory.
REPO_ROOT: Path = Path(__file__).resolve().parent.parent


def ensure_repo_on_sys_path() -> Path:
    """Insert repo root into sys.path if absent; return REPO_ROOT.

    Call this at the top of any module that may run as a standalone script
    (e.g. ``python core/system_scan.py``) so that ``from scripts.* import …``
    and other cross-package imports resolve correctly.
    """
    s = str(REPO_ROOT)
    if s not in sys.path:
        sys.path.insert(0, s)
    return REPO_ROOT
