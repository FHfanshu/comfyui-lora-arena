"""
Checkpoint Service

Handles LoRA checkpoint management.
"""

import os
import logging
from pathlib import Path
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from sqlalchemy.orm import selectinload

from models.database import Checkpoint
from models.schemas import CheckpointUpdate, ScanResponse

logger = logging.getLogger(__name__)


class CheckpointService:
    """Service for managing LoRA checkpoints"""

    # Supported LoRA file extensions
    LORA_EXTENSIONS = {".safetensors", ".pt", ".ckpt", ".bin"}

    async def scan_directory(
        self,
        db: AsyncSession,
        directory: str,
        available_loras: List[str] = None,
        remote_mode: bool = False
    ) -> ScanResponse:
        """
        Scan a directory for LoRA files and import new ones.

        Args:
            db: Database session
            directory: Path to scan (or relative path filter for remote mode)
            available_loras: List of LoRA names known to ComfyUI
            remote_mode: If True, use directory as relative path filter for ComfyUI loras

        Returns:
            ScanResponse with counts
        """
        dir_path = Path(directory)

        logger.info(f"Scanning directory: {directory}")
        logger.info(f"Remote mode: {remote_mode}")
        logger.info(f"Available loras count: {len(available_loras) if available_loras else 0}")
        if available_loras and len(available_loras) > 0:
            logger.info(f"Sample lora names: {available_loras[:3]}")
        # Map normalized name (forward slashes, lower) to actual ComfyUI name
        lora_map = {}
        if available_loras:
            for name in available_loras:
                normalized = name.replace("\\", "/").lower()
                lora_map[normalized] = name

        # Remote mode: use directory as relative path filter for ComfyUI loras
        # Also fallback to remote mode if local directory doesn't exist
        use_remote_scan = remote_mode or not dir_path.exists()

        if use_remote_scan:
            # If directory doesn't exist locally, check if we can just use the available_loras list
            if available_loras:
                # If we have available loras from ComfyUI, we can still "import" them
                # even if the local directory doesn't match (e.g. remote server)
                scanned = 0
                imported = 0
                skipped = 0
                errors = []

                # Get existing filenames
                result = await db.execute(select(Checkpoint.filename))
                existing_filenames = set(row[0] for row in result.fetchall())

                # Normalize the search directory for matching
                normalized_dir = directory.replace("\\", "/").lower().rstrip("/")

                for lora_name in available_loras:
                    # Normalize both for comparison
                    normalized_lora = lora_name.replace("\\", "/").lower()
                    normalized_dir = directory.replace("\\", "/").lower().rstrip("/")

                    # If a directory was specified, only import loras that are inside it
                    match = False
                    if not normalized_dir:
                        match = True
                    elif normalized_lora.startswith(normalized_dir + "/"):
                        match = True
                    elif normalized_lora == normalized_dir:
                        match = True
                    elif "/" + normalized_dir + "/" in "/" + normalized_lora:
                        match = True
                    else:
                        # Extract last parts of directory path and check if lora starts with them
                        # e.g., dir="E:/AI/.../other-styles/748cm/v03" -> check "other-styles/748cm/v03"
                        dir_parts = normalized_dir.split("/")
                        for i in range(len(dir_parts)):
                            partial_dir = "/".join(dir_parts[i:])
                            if partial_dir and normalized_lora.startswith(partial_dir + "/"):
                                match = True
                                break

                    if not match:
                        continue

                    scanned += 1

                    if lora_name in existing_filenames:
                        skipped += 1
                        continue

                    try:
                        # For remote files, we use the filename as both name and filename
                        # since we don't have the local path
                        checkpoint = Checkpoint(
                            name=Path(lora_name).stem,
                            filename=lora_name,
                            file_path=lora_name, # Use lora_name as path indicator
                            elo_rating=1500.0,
                        )
                        db.add(checkpoint)
                        imported += 1
                    except Exception as e:
                        errors.append(f"Error importing {lora_name}: {str(e)}")

                await db.commit()
                return ScanResponse(
                    scanned=scanned,
                    imported=imported,
                    skipped=skipped,
                    errors=errors
                )

            return ScanResponse(
                scanned=0,
                imported=0,
                skipped=0,
                errors=[f"Directory not found: {directory}"]
            )

        if not dir_path.is_dir():
            return ScanResponse(
                scanned=0,
                imported=0,
                skipped=0,
                errors=[f"Path is not a directory: {directory}"]
            )

        # Get existing filenames
        result = await db.execute(select(Checkpoint.filename))
        existing_filenames = set(row[0] for row in result.fetchall())

        scanned = 0
        imported = 0
        skipped = 0
        errors = []

        # Scan for LoRA files
        for file_path in dir_path.rglob("*"):
            if file_path.suffix.lower() not in self.LORA_EXTENSIONS:
                continue

            scanned += 1

            # Determine the name ComfyUI expects
            # 1. Try to match by filename in ComfyUI's available list
            match_found = False
            lora_name = file_path.name # Default to just filename

            if lora_map:
                # Try to find a lora in ComfyUI that ends with this file's relative path
                # or just matches the filename
                file_name_lower = file_path.name.lower()

                # Sort keys by length descending to match most specific path first
                sorted_loras = sorted(lora_map.keys(), key=len, reverse=True)

                for normalized_name in sorted_loras:
                    if normalized_name.endswith(file_name_lower):
                        lora_name = lora_map[normalized_name]
                        match_found = True
                        break

            if not match_found:
                # Fallback to relative path from the scanned directory
                try:
                    relative_path = file_path.relative_to(dir_path)
                    lora_name = str(relative_path).replace("\\", "/")
                except ValueError:
                    lora_name = file_path.name

            if lora_name in existing_filenames:
                skipped += 1
                continue

            try:
                # Create new checkpoint
                checkpoint = Checkpoint(
                    name=file_path.stem,  # Filename without extension
                    filename=lora_name,  # The name ComfyUI needs
                    file_path=str(file_path),  # Full local path
                    elo_rating=1500.0,
                )
                db.add(checkpoint)
                imported += 1
            except Exception as e:
                errors.append(f"Error importing {lora_name}: {str(e)}")

        await db.commit()

        return ScanResponse(
            scanned=scanned,
            imported=imported,
            skipped=skipped,
            errors=errors
        )

    async def list_checkpoints(
        self,
        db: AsyncSession,
        page: int = 1,
        limit: int = 50,
        sort_by: str = "elo_rating",
        sort_order: str = "desc",
        active_only: bool = False
    ) -> Tuple[List[Checkpoint], int]:
        """
        Get paginated list of checkpoints.

        Args:
            db: Database session
            page: Page number (1-based)
            limit: Items per page
            sort_by: Field to sort by
            sort_order: "asc" or "desc"
            active_only: Only return active checkpoints

        Returns:
            Tuple of (checkpoints list, total count)
        """
        # Build base query
        query = select(Checkpoint)
        count_query = select(func.count(Checkpoint.id))

        if active_only:
            query = query.where(Checkpoint.is_active == True)
            count_query = count_query.where(Checkpoint.is_active == True)

        # Get total count
        result = await db.execute(count_query)
        total = result.scalar()

        # Apply sorting
        sort_column = getattr(Checkpoint, sort_by, Checkpoint.elo_rating)
        if sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        # Apply pagination
        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit)

        result = await db.execute(query)
        checkpoints = list(result.scalars().all())

        return checkpoints, total

    async def get_checkpoint(
        self,
        db: AsyncSession,
        checkpoint_id: int
    ) -> Optional[Checkpoint]:
        """Get a single checkpoint by ID"""
        result = await db.execute(
            select(Checkpoint).where(Checkpoint.id == checkpoint_id)
        )
        return result.scalar_one_or_none()

    async def update_checkpoint(
        self,
        db: AsyncSession,
        checkpoint_id: int,
        data: CheckpointUpdate
    ) -> Optional[Checkpoint]:
        """Update checkpoint metadata"""
        checkpoint = await self.get_checkpoint(db, checkpoint_id)
        if not checkpoint:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(checkpoint, key, value)

        await db.commit()
        await db.refresh(checkpoint)

        return checkpoint

    async def toggle_active(
        self,
        db: AsyncSession,
        checkpoint_id: int
    ) -> Optional[Checkpoint]:
        """Toggle checkpoint active status"""
        checkpoint = await self.get_checkpoint(db, checkpoint_id)
        if not checkpoint:
            return None

        checkpoint.is_active = not checkpoint.is_active
        await db.commit()
        await db.refresh(checkpoint)

        return checkpoint

    async def delete_checkpoint(
        self,
        db: AsyncSession,
        checkpoint_id: int
    ) -> bool:
        """Delete a checkpoint"""
        checkpoint = await self.get_checkpoint(db, checkpoint_id)
        if not checkpoint:
            return False

        await db.delete(checkpoint)
        await db.commit()

        return True

    async def batch_delete_checkpoints(
        self,
        db: AsyncSession,
        checkpoint_ids: List[int]
    ) -> int:
        """Batch delete checkpoints"""
        from sqlalchemy import delete

        stmt = delete(Checkpoint).where(Checkpoint.id.in_(checkpoint_ids))
        result = await db.execute(stmt)
        await db.commit()

        return result.rowcount

    async def get_active_count(self, db: AsyncSession) -> int:
        """Get count of active checkpoints"""
        result = await db.execute(
            select(func.count(Checkpoint.id)).where(Checkpoint.is_active == True)
        )
        return result.scalar()

    async def batch_update_status(
        self,
        db: AsyncSession,
        checkpoint_ids: List[int],
        is_active: bool
    ) -> int:
        """Batch update is_active status for multiple checkpoints"""
        stmt = update(Checkpoint).where(Checkpoint.id.in_(checkpoint_ids)).values(is_active=is_active)
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount


# Singleton instance
checkpoint_service = CheckpointService()
