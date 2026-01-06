"""
Training Data Service

Handles reading and sampling tags from LoRA training datasets.
"""

import os
import random
import logging
from pathlib import Path
from typing import List, Optional, Set
from functools import lru_cache

logger = logging.getLogger(__name__)


class TrainingDataService:
    """Service for managing LoRA training data tags"""

    # Supported image extensions
    IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}

    def __init__(self):
        # Cache for loaded tags: {training_path: [list of tag sets]}
        self._cache: dict[str, List[List[str]]] = {}

    def clear_cache(self, training_path: Optional[str] = None):
        """Clear cached tags for a path or all paths"""
        if training_path:
            self._cache.pop(training_path, None)
        else:
            self._cache.clear()

    def scan_training_tags(self, training_path: str) -> List[List[str]]:
        """
        Scan a training directory and return all tag sets.

        Each image's .txt file becomes one tag set (list of tags).
        Results are cached for performance.

        Args:
            training_path: Path to training data folder

        Returns:
            List of tag sets, where each tag set is a list of tags from one .txt file
        """
        if training_path in self._cache:
            return self._cache[training_path]

        tag_sets = []
        dir_path = Path(training_path)

        if not dir_path.exists() or not dir_path.is_dir():
            logger.warning(f"Training path does not exist: {training_path}")
            return []

        # Recursively find all .txt files
        for txt_file in dir_path.rglob("*.txt"):
            # Check if corresponding image exists
            has_image = False
            for ext in self.IMAGE_EXTENSIONS:
                if txt_file.with_suffix(ext).exists():
                    has_image = True
                    break

            if not has_image:
                # Also check for files like image.jpg.txt -> image.jpg
                stem = txt_file.stem
                for ext in self.IMAGE_EXTENSIONS:
                    if (txt_file.parent / f"{stem}{ext}").exists():
                        has_image = True
                        break

            if not has_image:
                continue

            try:
                with open(txt_file, "r", encoding="utf-8") as f:
                    content = f.read().strip()

                if not content:
                    continue

                # Parse tags (comma-separated)
                tags = [tag.strip() for tag in content.split(",") if tag.strip()]

                if tags:
                    tag_sets.append(tags)

            except Exception as e:
                logger.warning(f"Error reading {txt_file}: {e}")
                continue

        logger.info(f"Scanned {len(tag_sets)} tag files from {training_path}")
        self._cache[training_path] = tag_sets
        return tag_sets

    def get_random_tags(
        self,
        training_path: str,
        exclude_trigger_word: bool = True,
        min_tags: int = 3,
        max_tags: Optional[int] = None
    ) -> Optional[List[str]]:
        """
        Get a random tag set from training data.

        Args:
            training_path: Path to training data folder
            exclude_trigger_word: If True, removes the first tag (usually trigger word)
            min_tags: Minimum number of tags required
            max_tags: Maximum tags to return (None = all)

        Returns:
            List of tags or None if no valid data
        """
        tag_sets = self.scan_training_tags(training_path)

        if not tag_sets:
            return None

        # Filter sets with enough tags
        valid_sets = [ts for ts in tag_sets if len(ts) >= min_tags]

        if not valid_sets:
            valid_sets = tag_sets  # Fallback to all sets

        if not valid_sets:
            return None

        # Pick random set
        chosen = random.choice(valid_sets).copy()

        # Optionally remove trigger word (first tag)
        if exclude_trigger_word and len(chosen) > 1:
            chosen = chosen[1:]

        # Optionally limit tags
        if max_tags and len(chosen) > max_tags:
            chosen = chosen[:max_tags]

        return chosen

    def get_common_tags(
        self,
        training_paths: List[str],
        min_frequency: float = 0.1
    ) -> List[str]:
        """
        Get tags that appear commonly across multiple training sets.

        Args:
            training_paths: List of training data paths
            min_frequency: Minimum frequency (0-1) for a tag to be included

        Returns:
            List of common tags sorted by frequency
        """
        tag_counts: dict[str, int] = {}
        total_sets = 0

        for path in training_paths:
            tag_sets = self.scan_training_tags(path)
            for tags in tag_sets:
                total_sets += 1
                # Skip trigger word
                for tag in tags[1:] if len(tags) > 1 else tags:
                    tag_lower = tag.lower()
                    tag_counts[tag_lower] = tag_counts.get(tag_lower, 0) + 1

        if total_sets == 0:
            return []

        # Filter by frequency
        min_count = int(total_sets * min_frequency)
        common = [
            (tag, count)
            for tag, count in tag_counts.items()
            if count >= min_count
        ]

        # Sort by frequency descending
        common.sort(key=lambda x: x[1], reverse=True)

        return [tag for tag, _ in common]

    def get_stats(self, training_path: str) -> dict:
        """Get statistics about a training dataset"""
        tag_sets = self.scan_training_tags(training_path)

        if not tag_sets:
            return {
                "total_images": 0,
                "unique_tags": 0,
                "avg_tags_per_image": 0,
                "top_tags": []
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
            "top_tags": [{"tag": t, "count": c} for t, c in sorted_tags[:20]]
        }


# Singleton instance
training_data_service = TrainingDataService()
