"""Source registry helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import yaml
except ModuleNotFoundError:
    yaml = None


def load_source_registry(path: Path) -> dict[str, Any]:
    """Load the source registry from YAML."""
    if yaml is None:
        return _load_simple_registry(path)
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in {path}")
    return data


def _load_simple_registry(path: Path) -> dict[str, Any]:
    """Fallback parser for the source registry before dependencies are installed."""
    sources: dict[str, dict[str, str]] = {}
    current_id = ""
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()
        if line.startswith("  ") and line.endswith(":") and not line.startswith("    "):
            current_id = line.strip().removesuffix(":")
            sources[current_id] = {}
        elif current_id and line.startswith("    ") and ":" in line:
            key, value = line.strip().split(":", 1)
            sources[current_id][key] = value.strip().strip('"')
    return {"sources": sources}


def source_status_rows(registry: dict[str, Any]) -> list[dict[str, str]]:
    """Convert source registry entries into report rows."""
    rows: list[dict[str, str]] = []
    for source_id, source in registry.get("sources", {}).items():
        rows.append(
            {
                "source_id": source_id,
                "title": str(source.get("title", "")),
                "reference": str(source.get("reference", "")),
                "status": str(source.get("status", "")),
                "evidence_type": str(source.get("evidence_type", "")),
            }
        )
    return rows
