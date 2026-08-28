from __future__ import annotations

import json
from pathlib import Path

DEFAULT_IGNORED = {".git", ".venv", "venv", "env", "__pycache__", "node_modules", "dist", "build", "dist_pimcord", ".dist_pimcord", "pimcord_dist"}


def load_ignored(root: Path) -> set[str]:
    """Carrega .pyinspect.json sem executar código do projeto analisado."""
    config = root / ".pyinspect.json"
    if not config.exists():
        return set(DEFAULT_IGNORED)
    try:
        data = json.loads(config.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set(DEFAULT_IGNORED)
    return set(DEFAULT_IGNORED) | {str(x) for x in data.get("ignore", [])}
