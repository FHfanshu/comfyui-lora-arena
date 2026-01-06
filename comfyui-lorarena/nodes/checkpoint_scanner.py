from __future__ import annotations

import json
from pathlib import Path

from ..services import checkpoint_service, db_manager


class LoRArenaCheckpointScanner:
    """Scan LoRA directories and import new checkpoints."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "scan_mode": (["auto", "custom"],),
                "custom_directory": ("STRING", {"default": ""}),
            }
        }

    RETURN_TYPES = ("INT", "INT", "STRING")
    RETURN_NAMES = ("imported_count", "total_count", "scan_report")
    FUNCTION = "scan"
    CATEGORY = "LoRArena"

    def scan(self, scan_mode: str, custom_directory: str):
        directory = None
        if scan_mode == "custom":
            directory = custom_directory.strip()
        else:
            directory = self._load_config_lora_directory() or None
        with db_manager.session_scope() as db:
            result = checkpoint_service.scan_directory(db, directory or None)

        report = json.dumps(
            {
                "scanned": result.scanned,
                "imported": result.imported,
                "skipped": result.skipped,
                "errors": result.errors,
            },
            ensure_ascii=False,
        )
        return (int(result.imported), int(result.scanned), report)

    def _load_config_lora_directory(self) -> str:
        try:
            base_dir = Path(__file__).resolve().parent.parent
            config_path = base_dir / "data" / "config.json"
            if config_path.exists():
                data = json.loads(config_path.read_text(encoding="utf-8"))
                return str(data.get("lora_directory", "")).strip()
        except Exception:
            pass
        return ""
