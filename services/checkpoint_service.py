"""
Checkpoint Service.
Handles LoRA checkpoint management for ComfyUI nodes.
"""

from __future__ import annotations

import logging
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


checkpoint_service = CheckpointService()
