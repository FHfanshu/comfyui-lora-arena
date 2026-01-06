from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class Checkpoint(Base):
    """LoRA Checkpoint model"""
    __tablename__ = "checkpoints"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Basic info
    name = Column(String(255), nullable=False)
    filename = Column(String(512), nullable=False, unique=True)
    file_path = Column(String(1024), nullable=False)

    # Metadata
    description = Column(Text, nullable=True)
    trigger_words = Column(JSON, default=list)
    base_model = Column(String(100), nullable=True)
    tags = Column(JSON, default=list)
    training_data_path = Column(String(1024), nullable=True)  # Path to training dataset folder

    # ELO rating
    elo_rating = Column(Float, default=1500.0, index=True)

    # Statistics
    total_battles = Column(Integer, default=0)
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    ties = Column(Integer, default=0)

    # Status
    is_active = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    battles_as_left = relationship("Battle", foreign_keys="Battle.left_checkpoint_id", back_populates="left_checkpoint")
    battles_as_right = relationship("Battle", foreign_keys="Battle.right_checkpoint_id", back_populates="right_checkpoint")
    elo_history = relationship("ELOHistory", back_populates="checkpoint")

    @property
    def win_rate(self) -> float:
        if self.total_battles == 0:
            return 0.0
        return (self.wins + self.ties * 0.5) / self.total_battles


class Battle(Base):
    """Battle record"""
    __tablename__ = "battles"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Participants
    left_checkpoint_id = Column(Integer, ForeignKey("checkpoints.id"), nullable=False)
    right_checkpoint_id = Column(Integer, ForeignKey("checkpoints.id"), nullable=False)

    # Generation parameters
    prompt = Column(Text, nullable=False)
    negative_prompt = Column(Text, nullable=True, default="")
    seed = Column(Integer, nullable=False)
    width = Column(Integer, default=1024)
    height = Column(Integer, default=1024)
    steps = Column(Integer, default=20)
    cfg_scale = Column(Float, default=7.0)
    sampler = Column(String(50), default="euler_ancestral")
    lora_strength = Column(Float, default=0.8)
    base_model = Column(String(255), nullable=True)

    # Generated images
    left_image_path = Column(String(1024), nullable=True)
    right_image_path = Column(String(1024), nullable=True)

    # Result: "left", "right", "tie", "skip", or None (pending)
    result = Column(String(20), nullable=True)

    # Status: "pending", "generating", "completed", "failed"
    status = Column(String(20), default="pending", index=True)
    is_pregenerated = Column(Boolean, default=False)
    error_message = Column(Text, nullable=True)

    # ELO changes
    left_elo_before = Column(Float, nullable=True)
    left_elo_after = Column(Float, nullable=True)
    right_elo_before = Column(Float, nullable=True)
    right_elo_after = Column(Float, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    voted_at = Column(DateTime, nullable=True)

    # Relationships
    left_checkpoint = relationship("Checkpoint", foreign_keys=[left_checkpoint_id], back_populates="battles_as_left")
    right_checkpoint = relationship("Checkpoint", foreign_keys=[right_checkpoint_id], back_populates="battles_as_right")


class ELOHistory(Base):
    """ELO rating history for tracking trends"""
    __tablename__ = "elo_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    checkpoint_id = Column(Integer, ForeignKey("checkpoints.id"), nullable=False, index=True)
    elo_rating = Column(Float, nullable=False)
    battle_id = Column(Integer, ForeignKey("battles.id"), nullable=True)
    recorded_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    checkpoint = relationship("Checkpoint", back_populates="elo_history")


class PromptTemplate(Base):
    """Prompt templates for battles"""
    __tablename__ = "prompt_templates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=True)
    positive_prompt = Column(Text, nullable=False)
    negative_prompt = Column(Text, nullable=True, default="")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
