// API Types

export interface Checkpoint {
  id: number;
  name: string;
  filename: string;
  file_path: string;
  description: string | null;
  trigger_words: string[];
  tags: string[];
  elo_rating: number;
  total_battles: number;
  wins: number;
  losses: number;
  ties: number;
  win_rate: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CheckpointListResponse {
  items: Checkpoint[];
  total: number;
  page: number;
  limit: number;
}

export interface NewBattleRequest {
  prompt?: string;
  negative_prompt?: string;
  strategy?: 'random' | 'balanced' | 'exploration';
  use_training_tags?: boolean;
}

export interface NewBattleResponse {
  battle_id: number;
  status: string;
  left_image_url: string | null;
  right_image_url: string | null;
  prompt: string;
  negative_prompt: string;
  seed: number;
  width: number;
  height: number;
  steps: number;
  cfg_scale: number;
  error_message?: string;
}

export interface BattleStatusResponse extends NewBattleResponse {}

export interface ELOChange {
  checkpoint_id: number;
  name: string;
  old_rating: number;
  new_rating: number;
  change: number;
}

export interface VoteResponse {
  success: boolean;
  left_checkpoint: Checkpoint;
  right_checkpoint: Checkpoint;
  winner: 'left' | 'right' | 'tie' | null;
  elo_changes: ELOChange[];
}

export interface LeaderboardEntry {
  rank: number;
  checkpoint_id: number;
  name: string;
  elo_rating: number;
  total_battles: number;
  wins: number;
  losses: number;
  ties: number;
  win_rate: number;
}

export interface LeaderboardResponse {
  items: LeaderboardEntry[];
  total: number;
}

export interface ELOHistoryPoint {
  elo_rating: number;
  recorded_at: string;
  battle_id: number | null;
}

export interface ELOHistoryResponse {
  checkpoint_id: number;
  checkpoint_name: string;
  history: ELOHistoryPoint[];
}

export interface Config {
  comfyui_url: string;
  lora_directory: string;
  base_model: string;
  steps: number;
  cfg_scale: number;
  sampler: string;
  scheduler: string;
  lora_strength: number;
  width: number;
  height: number;
  tipo_tag_length: 'short' | 'long' | 'very_short' | 'very_long';
  worker_enabled: boolean;
  worker_interval: number;
  worker_target_cache: number;
  worker_use_training_tags: boolean;
  parallel_generation: boolean;
  battle_royale_enabled: boolean;
  battle_royale_threshold: number;
  battle_royale_win_rate: number;
  remote_comfyui: boolean;
  training_data_directory: string;
}

export interface ComfyUIStatus {
  connected: boolean;
  url: string;
  error: string | null;
}

export interface ComfyUIModels {
  checkpoints: string[];
  loras: string[];
  samplers: string[];
}

export interface ScanResponse {
  scanned: number;
  imported: number;
  skipped: number;
  errors: string[];
}

export interface BattleHistoryItem {
  id: number;
  left_checkpoint_name: string;
  right_checkpoint_name: string;
  result: string | null;
  prompt: string;
  seed: number;
  left_image_url: string | null;
  right_image_url: string | null;
  created_at: string;
  voted_at: string | null;
}

export interface BattleHistoryResponse {
  items: BattleHistoryItem[];
  total: number;
  page: number;
  limit: number;
}
