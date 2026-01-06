import { useState, useCallback } from 'react';
import { battlesApi } from '../services/api';
import type { NewBattleResponse, VoteResponse } from '../types';

interface BattleState {
  status: 'idle' | 'loading' | 'ready' | 'voting' | 'voted' | 'error';
  battle: NewBattleResponse | null;
  result: VoteResponse | null;
  error: string | null;
}

export function useBattle() {
  const [state, setState] = useState<BattleState>({
    status: 'idle',
    battle: null,
    result: null,
    error: null,
  });

  const createBattle = useCallback(async (prompt?: string, strategy?: 'random' | 'balanced' | 'exploration') => {
    setState(prev => ({ ...prev, status: 'loading', error: null }));

    try {
      let battle = await battlesApi.createBattle({ prompt, strategy });

      // Polling logic if the battle is still pending/generating
      if (battle.status === 'pending' || battle.status === 'generating') {
        const pollStatus = async () => {
          try {
            const status = await battlesApi.getBattleStatus(battle.battle_id);
            if (status.status === 'completed') {
              setState({
                status: 'ready',
                battle: status,
                result: null,
                error: null,
              });
            } else if (status.status === 'failed') {
              setState({
                status: 'error',
                battle: null,
                result: null,
                error: status.error_message || 'Image generation failed',
              });
            } else {
              // Continue polling
              setTimeout(pollStatus, 2000);
            }
          } catch (err: any) {
            setState({
              status: 'error',
              battle: null,
              result: null,
              error: 'Failed to check battle status',
            });
          }
        };
        setTimeout(pollStatus, 2000);

        // Return the pending battle object but the state remains 'loading'
        // until the poll finishes.
        setState(prev => ({ ...prev, battle }));
      } else if (battle.status === 'completed') {
        setState({
          status: 'ready',
          battle,
          result: null,
          error: null,
        });
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
      throw err;
    }
  }, []);

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
    setState({
      status: 'idle',
      battle: null,
      result: null,
      error: null,
    });
  }, []);

  return {
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
}
