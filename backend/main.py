from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from pathlib import Path
import logging
import asyncio

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from db.session import init_db
from routers import battles, checkpoints, leaderboard, config as config_router, prompts
from services.battle_service import battle_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Initialize database
    await init_db()

    # Start background cache worker
    async def cache_worker():
        logger = logging.getLogger("cache_worker")
        logger.info("Cache worker started")
        while True:
            try:
                from config import get_config
                config = get_config()

                if not config.get("worker_enabled", True):
                    await asyncio.sleep(config.get("worker_interval", 10))
                    continue

                from db.session import AsyncSessionLocal
                async with AsyncSessionLocal() as db:
                    from sqlalchemy import select, func
                    from models.database import Battle, Checkpoint

                    # Count ready battles
                    stmt = select(func.count()).select_from(Battle).where(Battle.is_pregenerated == True).where(Battle.status == "completed").where(Battle.result.is_(None))
                    result = await db.execute(stmt)
                    ready_count = result.scalar()
                    target_cache = config.get("worker_target_cache", 5)

                    if ready_count < target_cache:
                        logger.info(f"Cache count ({ready_count}) < {target_cache}. Generating new battle...")
                        from models.schemas import NewBattleRequest

                        # Check for active checkpoints
                        stmt_count = select(func.count()).select_from(Checkpoint).where(Checkpoint.is_active == True)
                        res_count = await db.execute(stmt_count)
                        if res_count.scalar() < 2:
                            logger.warning("Not enough active checkpoints for pre-generation")
                            await asyncio.sleep(60)
                            continue

                        battle = await battle_service.initialize_battle(
                            db,
                            NewBattleRequest(
                                strategy="balanced",
                                use_training_tags=config.get("worker_use_training_tags", False)
                            )
                        )
                        battle.is_pregenerated = True
                        await db.commit()

                        logger.info(f"Processing generation for pre-generated battle {battle.id}")
                        await battle_service.process_battle_generation(battle.id)
                        logger.info(f"Battle {battle.id} generation completed")
                    else:
                        logger.debug(f"Cache count ({ready_count}) meets target ({target_cache})")

                await asyncio.sleep(config.get("worker_interval", 10))
            except Exception as e:
                logger.error(f"Cache worker error: {e}")
                await asyncio.sleep(30)

    asyncio.create_task(cache_worker())

    yield


app = FastAPI(
    title="LoRA Arena",
    description="ELO-based LoRA Checkpoint Evaluation System",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files for generated images
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Include routers
app.include_router(battles.router)
app.include_router(checkpoints.router)
app.include_router(leaderboard.router)
app.include_router(config_router.router)
app.include_router(prompts.router)


@app.get("/")
async def root():
    return {
        "name": "LoRA Arena",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
