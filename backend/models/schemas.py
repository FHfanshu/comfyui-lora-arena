from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime


# ============ Checkpoint Schemas ============

class CheckpointBase(BaseModel):
    name: str
    description: Optional[str] = None
    trigger_words: List[str] = []
    tags: List[str] = []


class CheckpointCreate(CheckpointBase):
    filename: str
    file_path: str


class CheckpointUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    trigger_words: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None
    training_data_path: Optional[str] = None


class CheckpointResponse(CheckpointBase):
    id: int
    filename: str
    file_path: str
    elo_rating: float
    total_battles: int
    wins: int
    losses: int
    ties: int
    win_rate: float
    is_active: bool
    training_data_path: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CheckpointListResponse(BaseModel):
    items: List[CheckpointResponse]
    total: int
    page: int
    limit: int


# ============ Battle Schemas ============

class NewBattleRequest(BaseModel):
    prompt: Optional[str] = None
    negative_prompt: Optional[str] = None
    strategy: Literal["random", "balanced", "exploration"] = "balanced"
    use_training_tags: bool = False  # If true, randomly sample tags from training data


class NewBattleResponse(BaseModel):
    battle_id: int
    status: str
    left_image_url: Optional[str] = None
    right_image_url: Optional[str] = None
    prompt: str
    negative_prompt: str
    seed: int
    width: int
    height: int
    steps: int
    cfg_scale: float
    error_message: Optional[str] = None


class VoteRequest(BaseModel):
    result: Literal["left", "right", "tie", "skip"]


class ELOChange(BaseModel):
    checkpoint_id: int
    name: str
    old_rating: float
    new_rating: float
    change: float


class VoteResponse(BaseModel):
    success: bool
    left_checkpoint: CheckpointResponse
    right_checkpoint: CheckpointResponse
    winner: Optional[str]  # "left", "right", "tie", or None for skip
    elo_changes: List[ELOChange]


class BattleHistoryItem(BaseModel):
    id: int
    left_checkpoint_name: str
    right_checkpoint_name: str
    result: Optional[str]
    prompt: str
    seed: int
    left_image_url: Optional[str]
    right_image_url: Optional[str]
    created_at: datetime
    voted_at: Optional[datetime]


class BattleHistoryResponse(BaseModel):
    items: List[BattleHistoryItem]
    total: int
    page: int
    limit: int


# ============ Leaderboard Schemas ============

class LeaderboardEntry(BaseModel):
    rank: int
    checkpoint_id: int
    name: str
    elo_rating: float
    total_battles: int
    wins: int
    losses: int
    ties: int
    win_rate: float


class LeaderboardResponse(BaseModel):
    items: List[LeaderboardEntry]
    total: int


class ELOHistoryPoint(BaseModel):
    elo_rating: float
    recorded_at: datetime
    battle_id: Optional[int] = None


class ELOHistoryResponse(BaseModel):
    checkpoint_id: int
    checkpoint_name: str
    history: List[ELOHistoryPoint]


# ============ Config Schemas ============

class ConfigResponse(BaseModel):
    comfyui_url: str
    lora_directory: str
    base_model: str
    steps: int
    cfg_scale: float
    sampler: str
    scheduler: str
    lora_strength: float
    width: int
    height: int
    tipo_tag_length: Literal["short", "long", "very_short", "very_long"] = "long"
    worker_enabled: bool = True
    worker_interval: int = 10
    worker_target_cache: int = 5
    worker_use_training_tags: bool = False
    parallel_generation: bool = True
    battle_royale_enabled: bool = False
    battle_royale_threshold: int = 10
    battle_royale_win_rate: float = 0.5
    remote_comfyui: bool = False
    training_data_directory: str = ""


class ConfigUpdate(BaseModel):
    comfyui_url: Optional[str] = None
    lora_directory: Optional[str] = None
    base_model: Optional[str] = None
    steps: Optional[int] = None
    cfg_scale: Optional[float] = None
    sampler: Optional[str] = None
    scheduler: Optional[str] = None
    lora_strength: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    tipo_tag_length: Optional[Literal["short", "long", "very_short", "very_long"]] = None
    worker_enabled: Optional[bool] = None
    worker_interval: Optional[int] = None
    worker_target_cache: Optional[int] = None
    worker_use_training_tags: Optional[bool] = None
    parallel_generation: Optional[bool] = None
    battle_royale_enabled: Optional[bool] = None
    battle_royale_threshold: Optional[int] = None
    battle_royale_win_rate: Optional[float] = None
    remote_comfyui: Optional[bool] = None
    training_data_directory: Optional[str] = None


class ComfyUIStatus(BaseModel):
    connected: bool
    url: str
    error: Optional[str] = None


class ComfyUIModelsResponse(BaseModel):
    checkpoints: List[str]
    loras: List[str]
    samplers: List[str]


# ============ Prompt Template Schemas ============

class PromptTemplateCreate(BaseModel):
    name: str
    category: Optional[str] = None
    positive_prompt: str
    negative_prompt: Optional[str] = ""


class PromptTemplateResponse(BaseModel):
    id: int
    name: str
    category: Optional[str]
    positive_prompt: str
    negative_prompt: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ============ Scan Schemas ============

class ScanRequest(BaseModel):
    directory: Optional[str] = None  # Use config directory if not specified


class ScanResponse(BaseModel):
    scanned: int
    imported: int
    skipped: int
    errors: List[str]


class BatchDeleteRequest(BaseModel):
    checkpoint_ids: List[int]


class BatchStatusRequest(BaseModel):
    checkpoint_ids: List[int]
    is_active: bool
