import { createContext, useContext, useState, useCallback, useRef, useEffect, type ReactNode } from 'react';
import { battlesApi } from '../services/api';
import type { NewBattleResponse, VoteResponse } from '../types';

interface BattleState {
  status: 'idle' | 'loading' | 'ready' | 'voting' | 'voted' | 'error';
  battle: NewBattleResponse | null;
  result: VoteResponse | null;
  error: string | null;
}

interface BattleContextValue extends BattleState {
  createBattle: (prompt?: string, strategy?: 'random' | 'balanced' | 'exploration', useTrainingTags?: boolean) => Promise<NewBattleResponse | undefined>;
  submitVote: (choice: 'left' | 'right' | 'tie' | 'skip') => Promise<VoteResponse>;
  reset: () => void;
  isLoading: boolean;
  isVoting: boolean;
  isReady: boolean;
  isVoted: boolean;
  hasError: boolean;
}

const BattleContext = createContext<BattleContextValue | null>(null);

export function BattleProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<BattleState>({
    status: 'idle',
    battle: null,
    result: null,
    error: null,
  });

  const pollingRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const battleIdRef = useRef<number | null>(null);

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollingRef.current) {
        clearTimeout(pollingRef.current);
      }
    };
  }, []);

  const pollStatus = useCallback(async (battleId: number) => {
    try {
      const status = await battlesApi.getBattleStatus(battleId);
      if (status.status === 'completed') {
        setState({
          status: 'ready',
          battle: status,
          result: null,
          error: null,
        });
        battleIdRef.current = null;
      } else if (status.status === 'failed') {
        setState({
          status: 'error',
          battle: null,
          result: null,
          error: status.error_message || 'Image generation failed',
        });
        battleIdRef.current = null;
      } else {
        // Continue polling
        pollingRef.current = setTimeout(() => pollStatus(battleId), 2000);
      }
    } catch (err: any) {
      setState({
        status: 'error',
        battle: null,
        result: null,
        error: 'Failed to check battle status',
      });
      battleIdRef.current = null;
    }
  }, []);

  const createBattle = useCallback(async (prompt?: string, strategy?: 'random' | 'balanced' | 'exploration', useTrainingTags?: boolean) => {
    // Cancel any existing polling
    if (pollingRef.current) {
      clearTimeout(pollingRef.current);
      pollingRef.current = null;
    }

    setState(prev => ({ ...prev, status: 'loading', error: null, result: null }));

    try {
      const battle = await battlesApi.createBattle({ prompt, strategy, use_training_tags: useTrainingTags });
      battleIdRef.current = battle.battle_id;

      if (battle.status === 'pending' || battle.status === 'generating') {
        setState(prev => ({ ...prev, battle }));
        pollingRef.current = setTimeout(() => pollStatus(battle.battle_id), 2000);
      } else if (battle.status === 'completed') {
        setState({
          status: 'ready',
          battle,
          result: null,
          error: null,
        });
        battleIdRef.current = null;
      } else if (battle.status === 'failed') {
        throw new Error(battle.error_message || 'Generation failed');
      }

      return battle;
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to create battle';
      setState({
        status: 'error',
        battle: null,
        result: null,
        error: errorMessage,
      });
      battleIdRef.current = null;
      throw err;
    }
  }, [pollStatus]);

  const submitVote = useCallback(async (choice: 'left' | 'right' | 'tie' | 'skip') => {
    if (!state.battle) {
      throw new Error('No active battle');
    }

    setState(prev => ({ ...prev, status: 'voting' }));

    try {
      const result = await battlesApi.submitVote(state.battle.battle_id, choice);
      setState(prev => ({
        ...prev,
        status: 'voted',
        result,
      }));
      return result;
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to submit vote';
      setState(prev => ({
        ...prev,
        status: 'error',
        error: errorMessage,
      }));
      throw err;
    }
  }, [state.battle]);

  const reset = useCallback(() => {
    if (pollingRef.current) {
      clearTimeout(pollingRef.current);
      pollingRef.current = null;
    }
    battleIdRef.current = null;
    setState({
      status: 'idle',
      battle: null,
      result: null,
      error: null,
    });
  }, []);

  const value: BattleContextValue = {
    ...state,
    createBattle,
    submitVote,
    reset,
    isLoading: state.status === 'loading',
    isVoting: state.status === 'voting',
    isReady: state.status === 'ready',
    isVoted: state.status === 'voted',
    hasError: state.status === 'error',
  };

  return (
    <BattleContext.Provider value={value}>
      {children}
    </BattleContext.Provider>
  );
}

export function useBattle() {
  const context = useContext(BattleContext);
  if (!context) {
    throw new Error('useBattle must be used within a BattleProvider');
  }
  return context;
}
