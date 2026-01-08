"""
Checkpoint Service.
Handles LoRA checkpoint management for ComfyUI nodes.
"""

from __future__ import annotations

import json
import logging
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

from sqlalchemy import select, func, update
from sqlalchemy.orm import Session

from .models import Checkpoint

logger = logging.getLogger(__name__)


@dataclass
class ScanResult:
    scanned: int
    imported: int
    skipped: int
    errors: List[str]


@dataclass
class EliminationResult:
    eliminated: int
    moved: int
    errors: List[str]


def _load_config() -> dict:
    """Load config from data/config.json."""
    config_path = Path(__file__).resolve().parent.parent / "data" / "config.json"
    default = {
        "battle_royale_enabled": False,
        "battle_royale_threshold": 10,
        "battle_royale_win_rate": 0.3,
        "lora_directory": "",
    }
    if config_path.exists():
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
            default.update(data)
        except Exception:
            pass
    return default


class CheckpointService:
    """Service for managing LoRA checkpoints."""

    LORA_EXTENSIONS = {".safetensors", ".pt", ".ckpt", ".bin"}

    def _get_comfyui_loras(self) -> List[str]:
        try:
            import folder_paths

            return list(folder_paths.get_filename_list("loras"))
        except Exception as exc:
            logger.debug("ComfyUI folder_paths unavailable: %s", exc)
            return []

    def _get_comfyui_lora_dirs(self) -> List[str]:
        try:
            import folder_paths

            return list(folder_paths.get_folder_paths("loras"))
        except Exception as exc:
            logger.debug("ComfyUI folder_paths unavailable: %s", exc)
            return []

    def _resolve_lora_path(self, lora_name: str) -> Optional[str]:
        try:
            import folder_paths

            resolved = folder_paths.get_full_path("loras", lora_name)
            return str(resolved) if resolved else None
        except Exception:
            return None

    @staticmethod
    def _matches_directory(lora_name: str, directory: str) -> bool:
        normalized_lora = lora_name.replace("\\", "/").lower()
        normalized_dir = directory.replace("\\", "/").lower().rstrip("/")

        if not normalized_dir:
            return True

        # Handle absolute paths - extract just the relative part
        # If directory contains drive letter or starts with /, try to extract meaningful suffix
        if ":" in normalized_dir or normalized_dir.startswith("/"):
            # Try common patterns like "models/Lora/..." or just take last 2-3 parts
            parts = normalized_dir.split("/")
            # Find "lora" folder and take everything after it
            for i, part in enumerate(parts):
                if part.lower() in ("lora", "loras"):
                    normalized_dir = "/".join(parts[i+1:])
                    break
            else:
                # No lora folder found, use last 2 parts as fallback
                if len(parts) >= 2:
                    normalized_dir = "/".join(parts[-2:])
                elif len(parts) >= 1:
                    normalized_dir = parts[-1]

        if not normalized_dir:
            return True
        if normalized_lora == normalized_dir:
            return True
        if normalized_lora.startswith(normalized_dir + "/"):
            return True
        if "/" + normalized_dir + "/" in "/" + normalized_lora:
            return True

        dir_parts = normalized_dir.split("/")
        for i in range(len(dir_parts)):
            partial = "/".join(dir_parts[i:])
            if partial and normalized_lora.startswith(partial + "/"):
                return True
        return False

    def scan_directory(
        self,
        db: Session,
        directory: Optional[str] = None,
    ) -> ScanResult:
        """
        Scan LoRA sources and import new checkpoints.

        If ComfyUI is available, use its LoRA index; otherwise fall back
        to local filesystem scanning.
        """
        available_loras = self._get_comfyui_loras()
        if available_loras:
            return self._scan_comfyui_loras(db, available_loras, directory)

        directories = []
        if directory:
            directories = [directory]
        else:
            directories = self._get_comfyui_lora_dirs()

        if not directories:
            return ScanResult(
                scanned=0,
                imported=0,
                skipped=0,
                errors=["No LoRA directories found"],
            )

        return self._scan_filesystem(db, directories)

    def _scan_comfyui_loras(
        self,
        db: Session,
        available_loras: Iterable[str],
        directory: Optional[str],
    ) -> ScanResult:
        scanned = 0
        imported = 0
        skipped = 0
        errors: List[str] = []

        existing = db.execute(select(Checkpoint.filename))
        existing_filenames = set(row[0] for row in existing.fetchall())
        # Build a set of existing stems for deduplication
        existing_stems = set(Path(fn).stem.lower() for fn in existing_filenames)

        for lora_name in available_loras:
            if directory and not self._matches_directory(lora_name, directory):
                continue

            scanned += 1
            stem = Path(lora_name).stem.lower()
            # Skip if filename already exists or if stem already exists (dedup by stem)
            if lora_name in existing_filenames or stem in existing_stems:
                skipped += 1
                continue

            try:
                resolved_path = self._resolve_lora_path(lora_name) or lora_name
                checkpoint = Checkpoint(
                    name=Path(lora_name).stem,
                    filename=lora_name,
                    file_path=resolved_path,
                    elo_rating=1500.0,
                    is_active=True,
                )
                db.add(checkpoint)
                existing_stems.add(stem)  # Track new stem to prevent duplicates in same scan
                imported += 1
            except Exception as exc:
                errors.append(f"Error importing {lora_name}: {exc}")

        db.commit()
        return ScanResult(scanned=scanned, imported=imported, skipped=skipped, errors=errors)

    def _scan_filesystem(
        self,
        db: Session,
        directories: Iterable[str],
    ) -> ScanResult:
        scanned = 0
        imported = 0
        skipped = 0
        errors: List[str] = []

        existing = db.execute(select(Checkpoint.filename))
        existing_filenames = set(row[0] for row in existing.fetchall())

        for directory in directories:
            dir_path = Path(directory)
            if not dir_path.exists() or not dir_path.is_dir():
                errors.append(f"Directory not found: {directory}")
                continue

            for file_path in dir_path.rglob("*"):
                if file_path.suffix.lower() not in self.LORA_EXTENSIONS:
                    continue

                scanned += 1
                lora_name = file_path.name
                if lora_name in existing_filenames:
                    skipped += 1
                    continue

                try:
                    checkpoint = Checkpoint(
                        name=file_path.stem,
                        filename=lora_name,
                        file_path=str(file_path),
                        elo_rating=1500.0,
                        is_active=True,
                    )
                    db.add(checkpoint)
                    imported += 1
                except Exception as exc:
                    errors.append(f"Error importing {file_path}: {exc}")

        db.commit()
        return ScanResult(scanned=scanned, imported=imported, skipped=skipped, errors=errors)

    def list_checkpoints(
        self,
        db: Session,
        page: int = 1,
        limit: int = 50,
        sort_by: str = "elo_rating",
        sort_order: str = "desc",
        active_only: bool = False,
    ) -> tuple[List[Checkpoint], int]:
        query = select(Checkpoint)
        count_query = select(func.count(Checkpoint.id))

        if active_only:
            query = query.where(Checkpoint.is_active == True)
            count_query = count_query.where(Checkpoint.is_active == True)

        total = db.execute(count_query).scalar() or 0

        sort_column = getattr(Checkpoint, sort_by, Checkpoint.elo_rating)
        query = query.order_by(sort_column.desc() if sort_order == "desc" else sort_column.asc())

        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit)

        checkpoints = list(db.execute(query).scalars().all())
        return checkpoints, total

    def get_checkpoint(self, db: Session, checkpoint_id: int) -> Optional[Checkpoint]:
        result = db.execute(select(Checkpoint).where(Checkpoint.id == checkpoint_id))
        return result.scalar_one_or_none()

    def update_checkpoint(
        self,
        db: Session,
        checkpoint_id: int,
        data: dict,
    ) -> Optional[Checkpoint]:
        checkpoint = self.get_checkpoint(db, checkpoint_id)
        if not checkpoint:
            return None

        for key, value in data.items():
            setattr(checkpoint, key, value)
        db.commit()
        db.refresh(checkpoint)
        return checkpoint

    def toggle_active(self, db: Session, checkpoint_id: int) -> Optional[Checkpoint]:
        checkpoint = self.get_checkpoint(db, checkpoint_id)
        if not checkpoint:
            return None
        checkpoint.is_active = not checkpoint.is_active
        db.commit()
        db.refresh(checkpoint)
        return checkpoint

    def delete_checkpoint(self, db: Session, checkpoint_id: int) -> bool:
        checkpoint = self.get_checkpoint(db, checkpoint_id)
        if not checkpoint:
            return False
        db.delete(checkpoint)
        db.commit()
        return True

    def batch_delete_checkpoints(self, db: Session, checkpoint_ids: List[int]) -> int:
        from sqlalchemy import delete

        stmt = delete(Checkpoint).where(Checkpoint.id.in_(checkpoint_ids))
        result = db.execute(stmt)
        db.commit()
        return result.rowcount

    def get_active_count(self, db: Session) -> int:
        result = db.execute(select(func.count(Checkpoint.id)).where(Checkpoint.is_active == True))
        return result.scalar() or 0

    def batch_update_status(self, db: Session, checkpoint_ids: List[int], is_active: bool) -> int:
        stmt = update(Checkpoint).where(Checkpoint.id.in_(checkpoint_ids)).values(is_active=is_active)
        result = db.execute(stmt)
        db.commit()
        return result.rowcount

    def reset_all_checkpoints(self, db: Session, lora_directory: Optional[str] = None) -> int:
        """Reset all checkpoints to initial state (ELO=1500, stats=0).

        Args:
            db: Database session
            lora_directory: Optional directory filter. If provided, only reset
                checkpoints matching this directory.

        Returns:
            Number of checkpoints reset
        """
        if lora_directory:
            # Get all checkpoints and filter by directory
            all_checkpoints = db.execute(select(Checkpoint)).scalars().all()
            matching_ids = [
                cp.id for cp in all_checkpoints
                if self._matches_directory(cp.filename, lora_directory)
            ]
            if not matching_ids:
                return 0
            stmt = (
                update(Checkpoint)
                .where(Checkpoint.id.in_(matching_ids))
                .values(
                    elo_rating=1500.0,
                    total_battles=0,
                    wins=0,
                    losses=0,
                    ties=0,
                )
            )
        else:
            stmt = update(Checkpoint).values(
                elo_rating=1500.0,
                total_battles=0,
                wins=0,
                losses=0,
                ties=0,
            )

        result = db.execute(stmt)
        db.commit()
        return result.rowcount

    def eliminate_checkpoints(
        self,
        db: Session,
        lora_directory: Optional[str] = None,
    ) -> EliminationResult:
        """Eliminate checkpoints that meet Battle Royale criteria.

        Moves eliminated LoRA files to parent directory and deactivates them.

        Args:
            db: Database session
            lora_directory: Optional directory filter

        Returns:
            EliminationResult with counts and any errors
        """
        config = _load_config()
        if not config.get("battle_royale_enabled", False):
            return EliminationResult(eliminated=0, moved=0, errors=["Battle Royale not enabled"])

        threshold = config.get("battle_royale_threshold", 10)
        min_win_rate = config.get("battle_royale_win_rate", 0.3)

        # Get all active checkpoints
        query = select(Checkpoint).where(Checkpoint.is_active == True)
        all_checkpoints = list(db.execute(query).scalars().all())

        # Filter by directory if specified
        if lora_directory:
            all_checkpoints = [
                cp for cp in all_checkpoints
                if self._matches_directory(cp.filename, lora_directory)
            ]

        if len(all_checkpoints) <= 2:
            return EliminationResult(
                eliminated=0, moved=0,
                errors=["Need more than 2 checkpoints for elimination"]
            )

        # Check if all checkpoints have reached threshold
        all_reached = all(c.total_battles >= threshold for c in all_checkpoints)
        if not all_reached:
            return EliminationResult(
                eliminated=0, moved=0,
                errors=["Not all checkpoints have reached battle threshold"]
            )

        # Find checkpoints to eliminate
        to_eliminate = [
            c for c in all_checkpoints
            if c.win_rate < min_win_rate
        ]

        # Ensure we keep at least 2
        max_to_eliminate = len(all_checkpoints) - 2
        to_eliminate = to_eliminate[:max_to_eliminate]

        if not to_eliminate:
            return EliminationResult(eliminated=0, moved=0, errors=[])

        eliminated = 0
        moved = 0
        errors: List[str] = []

        for checkpoint in to_eliminate:
            try:
                # Move the file to parent directory
                if checkpoint.file_path:
                    file_path = Path(checkpoint.file_path)
                    if file_path.exists():
                        parent_dir = file_path.parent.parent
                        if parent_dir.exists():
                            new_path = parent_dir / file_path.name
                            # Handle name collision
                            if new_path.exists():
                                stem = file_path.stem
                                suffix = file_path.suffix
                                counter = 1
                                while new_path.exists():
                                    new_path = parent_dir / f"{stem}_{counter}{suffix}"
                                    counter += 1
                            shutil.move(str(file_path), str(new_path))
                            moved += 1
                            logger.info(f"Moved eliminated LoRA: {file_path} -> {new_path}")

                # Deactivate checkpoint
                checkpoint.is_active = False
                eliminated += 1

            except Exception as exc:
                errors.append(f"Error eliminating {checkpoint.name}: {exc}")
                logger.error(f"Error eliminating {checkpoint.name}: {exc}")

        db.commit()
        return EliminationResult(eliminated=eliminated, moved=moved, errors=errors)

    def refresh_checkpoints(
        self,
        db: Session,
        lora_directory: Optional[str] = None,
    ) -> dict:
        """Refresh checkpoint data by checking if files still exist.

        Deactivates checkpoints whose files no longer exist at the recorded path.

        Args:
            db: Database session
            lora_directory: Optional directory filter

        Returns:
            Dict with updated, deactivated, and reactivated counts
        """
        query = select(Checkpoint)
        all_checkpoints = list(db.execute(query).scalars().all())

        if lora_directory:
            all_checkpoints = [
                cp for cp in all_checkpoints
                if self._matches_directory(cp.filename, lora_directory)
            ]

        updated = 0
        deactivated = 0
        reactivated = 0

        # Get current ComfyUI lora list for validation
        available_loras = set(self._get_comfyui_loras())

        for checkpoint in all_checkpoints:
            file_exists = False

            # Check by filename in ComfyUI's lora list
            if checkpoint.filename in available_loras:
                file_exists = True
            # Also check by absolute path
            elif checkpoint.file_path:
                file_path = Path(checkpoint.file_path)
                if file_path.exists():
                    file_exists = True

            if file_exists and not checkpoint.is_active:
                # File exists but checkpoint is deactivated - check if user intentionally disabled
                # Don't auto-reactivate - user may have disabled it manually
                pass
            elif not file_exists and checkpoint.is_active:
                # File doesn't exist but checkpoint is active - deactivate
                checkpoint.is_active = False
                deactivated += 1
                updated += 1
                logger.info(f"Deactivated missing checkpoint: {checkpoint.name}")

        if updated > 0:
            db.commit()

        return {
            "updated": updated,
            "deactivated": deactivated,
            "reactivated": reactivated,
        }


checkpoint_service = CheckpointService()
