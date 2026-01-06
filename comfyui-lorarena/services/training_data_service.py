"""
Training Data Service.
Handles reading and sampling tags from LoRA training datasets.
"""

from __future__ import annotations

import logging
import random
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


class TrainingDataService:
    """Service for managing LoRA training data tags."""

    IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}

    def __init__(self) -> None:
        self._cache: dict[str, List[List[str]]] = {}

    def clear_cache(self, training_path: Optional[str] = None) -> None:
        if training_path:
            self._cache.pop(training_path, None)
        else:
            self._cache.clear()

    def scan_training_tags(self, training_path: str) -> List[List[str]]:
        if training_path in self._cache:
            return self._cache[training_path]

        tag_sets: List[List[str]] = []
        dir_path = Path(training_path)

        if not dir_path.exists() or not dir_path.is_dir():
            logger.warning("Training path does not exist: %s", training_path)
            return []

        for txt_file in dir_path.rglob("*.txt"):
            has_image = False
            for ext in self.IMAGE_EXTENSIONS:
                if txt_file.with_suffix(ext).exists():
                    has_image = True
                    break

            if not has_image:
                stem = txt_file.stem
                for ext in self.IMAGE_EXTENSIONS:
                    if (txt_file.parent / f"{stem}{ext}").exists():
                        has_image = True
                        break

            if not has_image:
                continue

            try:
                content = txt_file.read_text(encoding="utf-8").strip()
                if not content:
                    continue
                tags = [tag.strip() for tag in content.split(",") if tag.strip()]
                if tags:
                    tag_sets.append(tags)
            except Exception as exc:
                logger.warning("Error reading %s: %s", txt_file, exc)

        logger.info("Scanned %d tag files from %s", len(tag_sets), training_path)
        self._cache[training_path] = tag_sets
        return tag_sets

    def get_random_tags(
        self,
        training_path: str,
        exclude_trigger_word: bool = True,
        min_tags: int = 3,
        max_tags: Optional[int] = None,
    ) -> Optional[List[str]]:
        tag_sets = self.scan_training_tags(training_path)
        if not tag_sets:
            return None

        valid_sets = [ts for ts in tag_sets if len(ts) >= min_tags]
        if not valid_sets:
            valid_sets = tag_sets

        if not valid_sets:
            return None

        chosen = random.choice(valid_sets).copy()
        if exclude_trigger_word and len(chosen) > 1:
            chosen = chosen[1:]
        if max_tags and len(chosen) > max_tags:
            chosen = chosen[:max_tags]

        return chosen

    def get_common_tags(
        self,
        training_paths: List[str],
        min_frequency: float = 0.1,
    ) -> List[str]:
        tag_counts: dict[str, int] = {}
        total_sets = 0

        for path in training_paths:
            tag_sets = self.scan_training_tags(path)
            for tags in tag_sets:
                total_sets += 1
                for tag in tags[1:] if len(tags) > 1 else tags:
                    tag_lower = tag.lower()
                    tag_counts[tag_lower] = tag_counts.get(tag_lower, 0) + 1

        if total_sets == 0:
            return []

        min_count = int(total_sets * min_frequency)
        common = [
            (tag, count) for tag, count in tag_counts.items() if count >= min_count
        ]
        common.sort(key=lambda x: x[1], reverse=True)
        return [tag for tag, _ in common]

    def get_stats(self, training_path: str) -> dict:
        tag_sets = self.scan_training_tags(training_path)
        if not tag_sets:
            return {
                "total_images": 0,
                "unique_tags": 0,
                "avg_tags_per_image": 0,
                "top_tags": [],
            }

        all_tags: dict[str, int] = {}
        for tags in tag_sets:
            for tag in tags:
                tag_lower = tag.lower()
                all_tags[tag_lower] = all_tags.get(tag_lower, 0) + 1

        sorted_tags = sorted(all_tags.items(), key=lambda x: x[1], reverse=True)
        return {
            "total_images": len(tag_sets),
            "unique_tags": len(all_tags),
            "avg_tags_per_image": sum(len(ts) for ts in tag_sets) / len(tag_sets),
            "top_tags": [{"tag": t, "count": c} for t, c in sorted_tags[:20]],
        }


training_data_service = TrainingDataService()
