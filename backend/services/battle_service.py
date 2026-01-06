"""
Battle Service

Handles battle creation, image generation, and voting.
"""

import asyncio
import random
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from models.database import Battle, Checkpoint, ELOHistory, PromptTemplate
from models.schemas import NewBattleRequest, VoteRequest, ELOChange
from services.elo_service import elo_service
from services.matchmaking_service import matchmaking_service
from services.training_data_service import training_data_service
from services.comfyui.client import ComfyUIClient
from services.comfyui.workflow_builder import workflow_builder
from config import get_config


class BattleService:
    """Service for managing battles"""

    def __init__(self):
        self.static_dir = Path(__file__).parent.parent / "static" / "battles"   
        self.static_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _normalize_lora_name(name: str) -> str:
        return name.replace("\\", "/").strip()

    async def initialize_battle(
        self,
        db: AsyncSession,
        request: NewBattleRequest,
    ) -> Battle:
        """
        Initialize a new battle record. Does not generate images.
        Check for pre-generated battles first.
        """
        config = get_config()

        # 1. Try to find a pre-generated battle for this strategy
        # For simplicity, we just look for any pre-generated battle that is 'completed'
        # but has no result yet.
        stmt = (
            select(Battle)
            .where(Battle.is_pregenerated == True)
            .where(Battle.status == "completed")
            .where(Battle.result.is_(None))
            .limit(1)
        )
        result = await db.execute(stmt)
        cached_battle = result.scalar_one_or_none()

        if cached_battle:
            # Mark it as active (not pre-generated anymore in terms of usage)
            cached_battle.is_pregenerated = False
            # If a custom prompt was provided, we might still want to use it,
            # but pre-generated battles use templates.
            # For now, if custom prompt is provided, we IGNORE cache and generate new.
            if not request.prompt:
                await db.commit()
                await db.refresh(cached_battle)
                return cached_battle

        # 2. Regular initialization (Async path)
        left_checkpoint, right_checkpoint = await matchmaking_service.select_matchup(
            db,
            strategy=request.strategy
        )

        seed = matchmaking_service.generate_seed()
        prompt = request.prompt
        negative_prompt = request.negative_prompt or ""

        # Handle training tags mode
        if request.use_training_tags:
            training_prompt = await self._get_training_tags_prompt(
                left_checkpoint, right_checkpoint
            )
            if training_prompt:
                prompt = training_prompt

        if not prompt:
            template = await self._get_random_prompt(db)
            if template:
                prompt = template.positive_prompt
                negative_prompt = template.negative_prompt or ""
            else:
                prompt = "masterpiece, best quality, 1girl"
                negative_prompt = "lowres, bad anatomy, bad hands"

        battle = Battle(
            left_checkpoint_id=left_checkpoint.id,
            right_checkpoint_id=right_checkpoint.id,
            prompt=prompt,
            negative_prompt=negative_prompt,
            seed=seed,
            width=config["width"],
            height=config["height"],
            steps=config["steps"],
            cfg_scale=config["cfg_scale"],
            sampler=config["sampler"],
            lora_strength=config["lora_strength"],
            base_model=config["base_model"],
            left_elo_before=left_checkpoint.elo_rating,
            right_elo_before=right_checkpoint.elo_rating,
            status="pending"
        )
        db.add(battle)
        await db.commit()
        await db.refresh(battle)
        return battle

    async def process_battle_generation(self, battle_id: int):
        """
        Background task to generate images for a battle.
        """
        from db.session import AsyncSessionLocal

        async with AsyncSessionLocal() as db:
            battle = await self.get_battle(db, battle_id)
            if not battle:
                return

            battle.status = "generating"
            await db.commit()

            try:
                config = get_config()

                # Get checkpoints to get filenames
                left = await db.execute(select(Checkpoint).where(Checkpoint.id == battle.left_checkpoint_id))
                left_checkpoint = left.scalar_one()
                right = await db.execute(select(Checkpoint).where(Checkpoint.id == battle.right_checkpoint_id))
                right_checkpoint = right.scalar_one()

                left_image, right_image = await self._generate_battle_images(
                    left_checkpoint.filename,
                    right_checkpoint.filename,
                    battle,
                    config
                )

                # Save images
                battle_dir = self.static_dir / str(battle.id)
                battle_dir.mkdir(exist_ok=True)

                left_path = battle_dir / "left.png"
                right_path = battle_dir / "right.png"

                left_path.write_bytes(left_image)
                right_path.write_bytes(right_image)

                battle.left_image_path = f"/static/battles/{battle.id}/left.png"
                battle.right_image_path = f"/static/battles/{battle.id}/right.png"
                battle.status = "completed"

                await db.commit()
            except Exception as e:
                battle.status = "failed"
                battle.error_message = str(e)
                await db.commit()

    async def create_battle(
        self,
        db: AsyncSession,
        request: NewBattleRequest,
    ) -> Battle:
        """
        Legacy method (Sync). Ideally replaced by initialize_battle + process_battle_generation.
        Keeping it for backward compatibility or direct calls.
        """
        battle = await self.initialize_battle(db, request)
        if battle.status == "completed": # If returned from cache
            return battle

        await self.process_battle_generation(battle.id)
        # Re-fetch because process_battle_generation uses a different session
        await db.refresh(battle)
        return battle

    async def _generate_battle_images(
        self,
        lora_left: str,
        lora_right: str,
        battle: Battle,
        config: dict
    ) -> Tuple[bytes, bytes]:
        """Generate two images for comparison using the same parameters"""
        client = ComfyUIClient(config["comfyui_url"])

        # Use dual-branch workflow for optimized generation (default: enabled)
        if config.get("use_dual_workflow", True):
            # Build a single workflow that generates both images
            workflow = workflow_builder.build_dual_lora(
                lora_name_left=lora_left,
                lora_name_right=lora_right,
                prompt=battle.prompt,
                negative_prompt=battle.negative_prompt,
                seed=battle.seed,
                width=battle.width,
                height=battle.height,
                steps=battle.steps,
                cfg_scale=battle.cfg_scale,
                sampler=battle.sampler,
                lora_strength=battle.lora_strength,
                base_model=config["base_model"],
                filename_prefix_left=f"arena_{battle.id}_left",
                filename_prefix_right=f"arena_{battle.id}_right"
            )
            return await client.generate_dual_images(workflow)

        # Fallback: Original two-workflow approach
        # Build workflows with identical parameters except LoRA
        workflow_left = workflow_builder.build(
            lora_name=lora_left,
            prompt=battle.prompt,
            negative_prompt=battle.negative_prompt,
            seed=battle.seed,
            width=battle.width,
            height=battle.height,
            steps=battle.steps,
            cfg_scale=battle.cfg_scale,
            sampler=battle.sampler,
            lora_strength=battle.lora_strength,
            base_model=config["base_model"],
            filename_prefix=f"arena_{battle.id}_left"
        )

        workflow_right = workflow_builder.build(
            lora_name=lora_right,
            prompt=battle.prompt,
            negative_prompt=battle.negative_prompt,
            seed=battle.seed,
            width=battle.width,
            height=battle.height,
            steps=battle.steps,
            cfg_scale=battle.cfg_scale,
            sampler=battle.sampler,
            lora_strength=battle.lora_strength,
            base_model=config["base_model"],
            filename_prefix=f"arena_{battle.id}_right"
        )

        if config.get("parallel_generation", True):
            # Generate both images in parallel for faster turnaround
            image_left, image_right = await asyncio.gather(
                client.generate_image(workflow_left),
                client.generate_image(workflow_right),
            )
        else:
            # Sequential fallback for lower VRAM
            image_left = await client.generate_image(workflow_left)
            image_right = await client.generate_image(workflow_right)

        return image_left, image_right

    async def submit_vote(
        self,
        db: AsyncSession,
        battle_id: int,
        vote: VoteRequest
    ) -> Tuple[Battle, List[ELOChange]]:
        """
        Submit a vote for a battle and update ELO ratings.

        Args:
            db: Database session
            battle_id: Battle ID
            vote: Vote request

        Returns:
            Tuple of (updated battle, ELO changes)
        """
        # Get battle with checkpoints
        result = await db.execute(
            select(Battle)
            .where(Battle.id == battle_id)
        )
        battle = result.scalar_one_or_none()

        if not battle:
            raise ValueError(f"Battle {battle_id} not found")

        if battle.result is not None:
            raise ValueError(f"Battle {battle_id} already has a result")

        # Get checkpoints
        left = await db.execute(
            select(Checkpoint).where(Checkpoint.id == battle.left_checkpoint_id)
        )
        left_checkpoint = left.scalar_one()

        right = await db.execute(
            select(Checkpoint).where(Checkpoint.id == battle.right_checkpoint_id)
        )
        right_checkpoint = right.scalar_one()

        # Update battle result
        battle.result = vote.result
        battle.voted_at = datetime.utcnow()

        elo_changes = []

        # Calculate ELO changes (skip if vote is "skip")
        if vote.result in ["left", "right", "tie"]:
            elo_update = elo_service.process_battle(
                rating_a=left_checkpoint.elo_rating,
                rating_b=right_checkpoint.elo_rating,
                result=vote.result,
                games_a=left_checkpoint.total_battles,
                games_b=right_checkpoint.total_battles
            )

            # Update left checkpoint
            left_checkpoint.elo_rating = elo_update.new_rating_a
            left_checkpoint.total_battles += 1
            if vote.result == "left":
                left_checkpoint.wins += 1
            elif vote.result == "right":
                left_checkpoint.losses += 1
            else:
                left_checkpoint.ties += 1

            # Update right checkpoint
            right_checkpoint.elo_rating = elo_update.new_rating_b
            right_checkpoint.total_battles += 1
            if vote.result == "right":
                right_checkpoint.wins += 1
            elif vote.result == "left":
                right_checkpoint.losses += 1
            else:
                right_checkpoint.ties += 1

            # Record ELO history
            left_history = ELOHistory(
                checkpoint_id=left_checkpoint.id,
                elo_rating=elo_update.new_rating_a,
                battle_id=battle.id
            )
            right_history = ELOHistory(
                checkpoint_id=right_checkpoint.id,
                elo_rating=elo_update.new_rating_b,
                battle_id=battle.id
            )
            db.add(left_history)
            db.add(right_history)

            # Update battle ELO records
            battle.left_elo_after = elo_update.new_rating_a
            battle.right_elo_after = elo_update.new_rating_b

            elo_changes = [
                ELOChange(
                    checkpoint_id=left_checkpoint.id,
                    name=left_checkpoint.name,
                    old_rating=elo_update.old_rating_a,
                    new_rating=elo_update.new_rating_a,
                    change=elo_update.change_a
                ),
                ELOChange(
                    checkpoint_id=right_checkpoint.id,
                    name=right_checkpoint.name,
                    old_rating=elo_update.old_rating_b,
                    new_rating=elo_update.new_rating_b,
                    change=elo_update.change_b
                )
            ]

            # Check for Battle Royale elimination
            await self._check_battle_royale_elimination(left_checkpoint)
            await self._check_battle_royale_elimination(right_checkpoint)

        await db.commit()
        await db.refresh(battle)
        await db.refresh(left_checkpoint)
        await db.refresh(right_checkpoint)

        return battle, elo_changes

    async def _check_battle_royale_elimination(self, checkpoint: Checkpoint) -> bool:
        """
        Check and handle Battle Royale elimination for a checkpoint.
        Returns True if eliminated.
        """
        config = get_config()
        if not config.get("battle_royale_enabled", False):
            return False

        threshold = config.get("battle_royale_threshold", 10)
        win_rate_threshold = config.get("battle_royale_win_rate", 0.5)

        if checkpoint.total_battles >= threshold:
            # win_rate = (wins + ties * 0.5) / total_battles
            win_rate = (checkpoint.wins + checkpoint.ties * 0.5) / checkpoint.total_battles
            if win_rate < win_rate_threshold:
                checkpoint.is_active = False
                logging.info(
                    "Battle Royale: Checkpoint '%s' (ID: %d) ELIMINATED. "
                    "Battles: %d, Win Rate: %.2f%%",
                    checkpoint.name, checkpoint.id, checkpoint.total_battles, win_rate * 100
                )
                return True
        return False

    async def get_battle(
        self,
        db: AsyncSession,
        battle_id: int
    ) -> Optional[Battle]:
        """Get a battle by ID"""
        result = await db.execute(
            select(Battle).where(Battle.id == battle_id)
        )
        return result.scalar_one_or_none()

    async def get_battle_history(
        self,
        db: AsyncSession,
        page: int = 1,
        limit: int = 20,
        checkpoint_id: Optional[int] = None
    ) -> Tuple[List[Battle], int]:
        """Get paginated battle history"""
        query = select(Battle).where(Battle.result.isnot(None))
        count_query = select(func.count(Battle.id)).where(Battle.result.isnot(None))

        if checkpoint_id:
            query = query.where(
                (Battle.left_checkpoint_id == checkpoint_id) |
                (Battle.right_checkpoint_id == checkpoint_id)
            )
            count_query = count_query.where(
                (Battle.left_checkpoint_id == checkpoint_id) |
                (Battle.right_checkpoint_id == checkpoint_id)
            )

        # Get total count
        result = await db.execute(count_query)
        total = result.scalar()

        # Apply pagination
        query = query.order_by(desc(Battle.created_at))
        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit)

        result = await db.execute(query)
        battles = list(result.scalars().all())

        return battles, total

    async def _get_random_prompt(
        self,
        db: AsyncSession
    ) -> Optional[PromptTemplate]:
        """Get a random active prompt template"""
        result = await db.execute(
            select(PromptTemplate).where(PromptTemplate.is_active == True)
        )
        templates = list(result.scalars().all())

        if not templates:
            return None

        return random.choice(templates)

    async def _get_training_tags_prompt(
        self,
        left_checkpoint: Checkpoint,
        right_checkpoint: Checkpoint
    ) -> Optional[str]:
        """
        Get a prompt by sampling from training data tags.

        Strategy:
        - First check global training_data_directory config
        - If not set, fall back to checkpoint-specific training_data_path
        - Returns None if no training data available
        """
        from config import get_config
        config = get_config()

        # Priority 1: Use global training_data_directory if configured
        global_dir = config.get("training_data_directory", "")
        if global_dir:
            logging.info(f"Using global training_data_directory: {global_dir}")
            tags = training_data_service.get_random_tags(
                global_dir,
                exclude_trigger_word=True,
                min_tags=3
            )
            if tags:
                quality_tags = ["masterpiece", "best quality"]
                prompt = ", ".join(quality_tags + tags)
                logging.info(f"Generated training tags prompt from global dir: {prompt[:100]}...")
                return prompt
            else:
                logging.warning(f"No tags found in global training_data_directory: {global_dir}")

        # Priority 2: Fall back to checkpoint-specific paths
        candidates = []

        if left_checkpoint.training_data_path:
            candidates.append(left_checkpoint)
        if right_checkpoint.training_data_path:
            candidates.append(right_checkpoint)

        if not candidates:
            return None

        # Randomly pick one checkpoint's training data
        chosen = random.choice(candidates)

        tags = training_data_service.get_random_tags(
            chosen.training_data_path,
            exclude_trigger_word=True,  # Remove trigger word since LoRA handles it
            min_tags=3
        )

        if not tags:
            return None

        # Add quality tags at the beginning
        quality_tags = ["masterpiece", "best quality"]
        prompt = ", ".join(quality_tags + tags)

        logging.info(
            f"Generated training tags prompt from {chosen.name}: {prompt[:100]}..."
        )

        return prompt


# Singleton instance
battle_service = BattleService()
