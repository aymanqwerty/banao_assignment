"""Load config.yaml and resolve paths relative to the repo root."""
from __future__ import annotations
from pathlib import Path
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]


def load_config(path: str | Path | None = None) -> dict:
    cfg_path = Path(path) if path else REPO_ROOT / "config.yaml"
    with open(cfg_path, "r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    cfg["_data_dir"] = REPO_ROOT / cfg["paths"]["data_dir"]
    cfg["_out_dir"] = REPO_ROOT / cfg["paths"]["out_dir"]
    cfg["_out_dir"].mkdir(parents=True, exist_ok=True)
    return cfg
