import axios from 'axios';
import type {
  NewBattleRequest,
  NewBattleResponse,
  BattleStatusResponse,
  VoteResponse,
  CheckpointListResponse,
  Checkpoint,
  LeaderboardResponse,
  ELOHistoryResponse,
  Config,
  ComfyUIStatus,
  ComfyUIModels,
  ScanResponse,
  BattleHistoryResponse,
} from '../types';

// Detect if running inside ComfyUI (embedded mode) or standalone
const isEmbedded = window.location.pathname.startsWith('/lorarena');
const baseURL = isEmbedded ? '/lorarena/api' : '/api';

const api = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Battles API
export const battlesApi = {
  createBattle: async (request: NewBattleRequest = {}): Promise<NewBattleResponse> => {
    const { data } = await api.post<NewBattleResponse>('/battles/new', request);
    return data;
  },

  submitVote: async (battleId: number, result: 'left' | 'right' | 'tie' | 'skip'): Promise<VoteResponse> => {
    const { data } = await api.post<VoteResponse>(`/battles/${battleId}/vote`, { result });
    return data;
  },

  getHistory: async (page = 1, limit = 20, checkpointId?: number): Promise<BattleHistoryResponse> => {
    const params = { page, limit, checkpoint_id: checkpointId };
    const { data } = await api.get<BattleHistoryResponse>('/battles/history/list', { params });
    return data;
  },

  getBattleStatus: async (battleId: number): Promise<BattleStatusResponse> => {
    const { data } = await api.get<BattleStatusResponse>(`/battles/${battleId}`);
    return data;
  },
};

// Prompts API
export const promptsApi = {
  optimize: async (
    prompt: string,
    tagLength?: 'short' | 'long' | 'very_short' | 'very_long'
  ): Promise<{ optimized_prompt: string }> => {
    const payload = tagLength ? { prompt, tag_length: tagLength } : { prompt };
    const { data } = await api.post<{ optimized_prompt: string }>('/prompts/optimize', payload);
    return data;
  },
};

// Checkpoints API
export const checkpointsApi = {
  list: async (page = 1, limit = 50, sortBy = 'elo_rating', activeOnly = false): Promise<CheckpointListResponse> => {
    const { data } = await api.get<CheckpointListResponse>('/checkpoints', {
      params: { page, limit, sort_by: sortBy, active_only: activeOnly },
    });
    return data;
  },

  get: async (id: number): Promise<Checkpoint> => {
    const { data } = await api.get<Checkpoint>(`/checkpoints/${id}`);
    return data;
  },

  update: async (id: number, updates: Partial<Checkpoint>): Promise<Checkpoint> => {
    const { data } = await api.put<Checkpoint>(`/checkpoints/${id}`, updates);
    return data;
  },

  toggleActive: async (id: number): Promise<Checkpoint> => {
    const { data } = await api.patch<Checkpoint>(`/checkpoints/${id}/toggle`);
    return data;
  },

  scan: async (directory?: string): Promise<ScanResponse> => {
    const { data } = await api.post<ScanResponse>('/checkpoints/scan', { directory });
    return data;
  },

  delete: async (id: number): Promise<void> => {
    await api.delete(`/checkpoints/${id}`);
  },

  batchDelete: async (ids: number[]): Promise<void> => {
    await api.post('/checkpoints/batch-delete', { checkpoint_ids: ids });
  },

  batchUpdateStatus: async (ids: number[], isActive: boolean): Promise<void> => {
    await api.post('/checkpoints/batch-status', { checkpoint_ids: ids, is_active: isActive });
  },
};

// Leaderboard API
export const leaderboardApi = {
  get: async (minBattles = 0, limit = 100): Promise<LeaderboardResponse> => {
    const { data } = await api.get<LeaderboardResponse>('/leaderboard', {
      params: { min_battles: minBattles, limit },
    });
    return data;
  },

  getHistory: async (checkpointId: number, limit = 100): Promise<ELOHistoryResponse> => {
    const { data } = await api.get<ELOHistoryResponse>(`/leaderboard/${checkpointId}/history`, {
      params: { limit },
    });
    return data;
  },
};

// Config API
export const configApi = {
  get: async (): Promise<Config> => {
    const { data } = await api.get<Config>('/config');
    return data;
  },

  update: async (updates: Partial<Config>): Promise<Config> => {
    const { data } = await api.put<Config>('/config', updates);
    return data;
  },

  getComfyUIStatus: async (): Promise<ComfyUIStatus> => {
    const { data } = await api.get<ComfyUIStatus>('/config/comfyui/status');
    return data;
  },

  getComfyUIModels: async (): Promise<ComfyUIModels> => {
    const { data } = await api.get<ComfyUIModels>('/config/comfyui/models');
    return data;
  },
};

// Node state API (for Panel Node integration)
export interface NodeModelsStatus {
  ready: boolean;
  model_loaded: boolean;
  clip_loaded: boolean;
  vae_loaded: boolean;
  message: string;
}

export const nodeApi = {
  getModelsStatus: async (): Promise<NodeModelsStatus> => {
    const { data } = await api.get<NodeModelsStatus>('/node/models-ready');
    return data;
  },

  clearModels: async (): Promise<void> => {
    await api.post('/node/clear-models');
  },
};

// Helper to check if running in embedded mode
export const isEmbeddedMode = isEmbedded;
