import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useBattle } from '../contexts/BattleContext';
import { promptsApi, configApi, nodeApi, isEmbeddedMode } from '../services/api';
import type { NodeModelsStatus } from '../services/api';
import {
  ChevronLeft,
  ChevronRight,
  Equal,
  SkipForward,
  RefreshCw,
  TrendingUp,
  TrendingDown,
  Wand2,
  Settings,
  Skull,
  Loader2,
  Tags,
  FolderOpen,
  Check,
  X,
  AlertTriangle,
} from 'lucide-react';

export function ArenaPage() {
  const { t } = useTranslation();
  const {
    battle,
    result,
    error,
    createBattle,
    submitVote,
    isLoading,
    isVoting,
    isReady,
    isVoted,
  } = useBattle();

  const [strategy, setStrategy] = useState<'balanced' | 'random' | 'exploration'>(() => {
    const saved = localStorage.getItem('arena_strategy');
    return (saved as 'balanced' | 'random' | 'exploration') || 'balanced';
  });
  const [customPrompt, setCustomPrompt] = useState('');
  const [useTrainingTags, setUseTrainingTags] = useState(() => {
    return localStorage.getItem('arena_use_training_tags') === 'true';
  });
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [tagLength, setTagLength] = useState<'short' | 'long' | 'very_short' | 'very_long'>('long');
  const [showTipoOptions, setShowTipoOptions] = useState(false);
  const [workerEnabled, setWorkerEnabled] = useState(false);
  const [battleRoyaleEnabled, setBattleRoyaleEnabled] = useState(false);
  const [workerLoading, setWorkerLoading] = useState(true);
  const [showTrainingDataSettings, setShowTrainingDataSettings] = useState(false);
  const [trainingDataDirectory, setTrainingDataDirectory] = useState('');
  const [savingTrainingData, setSavingTrainingData] = useState(false);
  const [nodeModelsStatus, setNodeModelsStatus] = useState<NodeModelsStatus | null>(null);
  const [checkingModels, setCheckingModels] = useState(isEmbeddedMode);

  useEffect(() => {
    loadWorkerStatus();
    // Check model status if running in embedded mode
    if (isEmbeddedMode) {
      checkNodeModels();
    }
  }, []);

  // Persist user preferences to localStorage
  useEffect(() => {
    localStorage.setItem('arena_strategy', strategy);
  }, [strategy]);

  useEffect(() => {
    localStorage.setItem('arena_use_training_tags', String(useTrainingTags));
  }, [useTrainingTags]);

  const loadWorkerStatus = async () => {
    try {
      const config = await configApi.get();
      setWorkerEnabled(config.worker_enabled);
      setBattleRoyaleEnabled(config.battle_royale_enabled);
      setTrainingDataDirectory(config.training_data_directory || '');
      if (config.tipo_tag_length) {
        setTagLength(config.tipo_tag_length);
      }
    } catch (err) {
      console.error('Failed to load worker status:', err);
    } finally {
      setWorkerLoading(false);
    }
  };

  const checkNodeModels = async () => {
    try {
      setCheckingModels(true);
      const status = await nodeApi.getModelsStatus();
      setNodeModelsStatus(status);
    } catch (err) {
      console.error('Failed to check node models:', err);
      setNodeModelsStatus(null);
    } finally {
      setCheckingModels(false);
    }
  };

  const toggleWorker = async () => {
    if (workerLoading) return;
    try {
      setWorkerLoading(true);
      const updated = await configApi.update({ worker_enabled: !workerEnabled });
      setWorkerEnabled(updated.worker_enabled);
    } catch (err) {
      console.error('Failed to toggle worker:', err);
    } finally {
      setWorkerLoading(false);
    }
  };

  const handleVote = async (choice: 'left' | 'right' | 'tie' | 'skip') => {
    if (!isReady || !battle?.battle_id || !battle.left_image_url || !battle.right_image_url) {
      return;
    }
    try {
      await submitVote(choice);
    } catch (err) {
      console.error('Vote failed:', err);
    }
  };

  const handleNextBattle = () => {
    const prompt = customPrompt.trim();
    createBattle(prompt ? prompt : undefined, strategy, useTrainingTags);
  };

  const saveTrainingDataDirectory = async () => {
    setSavingTrainingData(true);
    try {
      await configApi.update({ training_data_directory: trainingDataDirectory });
      setShowTrainingDataSettings(false);
    } catch (err) {
      console.error('Failed to save training data directory:', err);
    } finally {
      setSavingTrainingData(false);
    }
  };

  const imageAspect = useMemo(() => {
    if (!battle?.width || !battle?.height) {
      return '1 / 1';
    }
    return `${battle.width} / ${battle.height}`;
  }, [battle?.width, battle?.height]);

  const canVote = Boolean(
    isReady &&
    battle?.battle_id &&
    battle.left_image_url &&
    battle.right_image_url &&
    !isVoting
  );

  const handleOptimize = async () => {
    if (!customPrompt) return;
    setIsOptimizing(true);
    try {
      const { optimized_prompt } = await promptsApi.optimize(customPrompt, tagLength);
      setCustomPrompt(optimized_prompt);
    } catch (err) {
      console.error('Optimization failed:', err);
    } finally {
      setIsOptimizing(false);
    }
  };

  const strategyLabels: Record<string, string> = {
    balanced: t('arena.balanced'),
    random: t('arena.random'),
    exploration: t('arena.exploration'),
  };

  const tagLengthLabels: Record<string, string> = {
    very_short: t('arena.veryShort'),
    short: t('arena.short'),
    long: t('arena.long'),
    very_long: t('arena.veryLong'),
  };

  // Determine what to show in image areas
  const showImages = isReady || isLoading || isVoting;
  const hasLeftImage = battle?.left_image_url;
  const hasRightImage = battle?.right_image_url;

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex-1">
          <h1 className="text-3xl font-bold text-white mb-2">{t('arena.title')}</h1>
          <p className="text-zinc-400 text-sm">{t('arena.subtitle')}</p>
        </div>
        <div className="flex items-center gap-3 bg-zinc-900/50 p-2 rounded-xl border border-zinc-800">
          <div className="flex flex-col items-end pr-2 border-r border-zinc-800">
            <span className="text-[10px] uppercase font-bold text-zinc-500 leading-none">{t('arena.backgroundTask')}</span>
            <span className={`text-xs font-bold ${workerEnabled ? 'text-emerald-400' : 'text-zinc-500'}`}>
              {workerEnabled ? t('common.running') : t('common.paused')}
            </span>
          </div>
          <button
            onClick={toggleWorker}
            disabled={workerLoading}
            className={`p-2 rounded-lg transition-all ${
              workerEnabled
                ? 'bg-red-500/10 text-red-400 hover:bg-red-500/20'
                : 'bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20'
            } ${workerLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
            title={workerEnabled ? t('arena.pauseBackground') : t('arena.startBackground')}
          >
            {workerEnabled ? (
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>
            ) : (
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
            )}
          </button>
        </div>
        {battleRoyaleEnabled && (
          <div className="flex items-center gap-2 bg-orange-500/10 text-orange-400 px-3 py-1.5 rounded-xl border border-orange-500/20">
            <Skull className="w-4 h-4" />
            <div className="flex flex-col">
              <span className="text-[10px] uppercase font-bold leading-none">{t('arena.battleRoyale')}</span>
              <span className="text-[10px] font-medium opacity-80">{t('common.active')}</span>
            </div>
          </div>
        )}
      </div>

      {/* Strategy Selector */}
      <div className="flex justify-center items-center gap-4 mb-6">
        <div className="flex gap-2">
          {(['balanced', 'random', 'exploration'] as const).map((s) => (
            <button
              key={s}
              onClick={() => setStrategy(s)}
              className={`px-3 py-1 rounded-full text-sm transition-colors ${
                strategy === s
                  ? 'bg-emerald-600 text-white'
                  : 'bg-zinc-800 text-zinc-400 hover:bg-zinc-700'
              }`}
            >
              {strategyLabels[s]}
            </button>
          ))}
        </div>
        <div className="h-6 w-px bg-zinc-700" />
        <div className="relative flex items-center gap-1">
          <button
            onClick={() => setUseTrainingTags(!useTrainingTags)}
            className={`flex items-center gap-2 px-3 py-1 rounded-l-full text-sm transition-colors ${
              useTrainingTags
                ? 'bg-purple-600 text-white'
                : 'bg-zinc-800 text-zinc-400 hover:bg-zinc-700'
            }`}
            title={t('arena.trainingTagsTooltip')}
          >
            <Tags className="w-4 h-4" />
            {t('arena.trainingTags')}
          </button>
          <button
            onClick={() => setShowTrainingDataSettings(!showTrainingDataSettings)}
            className={`px-2 py-1 rounded-r-full text-sm transition-colors ${
              showTrainingDataSettings
                ? 'bg-purple-700 text-white'
                : 'bg-zinc-800 text-zinc-400 hover:bg-zinc-700'
            }`}
            title={t('arena.trainingDataSettings')}
          >
            <FolderOpen className="w-4 h-4" />
          </button>
          {showTrainingDataSettings && (
            <div className="absolute top-full left-0 mt-2 p-3 bg-zinc-800 border border-zinc-700 rounded-lg z-10 shadow-xl min-w-[300px]">
              <label className="block text-zinc-400 text-xs mb-2 uppercase font-bold tracking-wider">
                {t('arena.trainingDataDirectory')}
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={trainingDataDirectory}
                  onChange={(e) => setTrainingDataDirectory(e.target.value)}
                  placeholder={t('arena.trainingDataPlaceholder')}
                  className="flex-1 px-3 py-1.5 bg-zinc-900 border border-zinc-600 rounded text-white text-sm"
                />
                <button
                  onClick={saveTrainingDataDirectory}
                  disabled={savingTrainingData}
                  className="px-2 py-1 bg-emerald-600 hover:bg-emerald-700 rounded text-white"
                >
                  <Check className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setShowTrainingDataSettings(false)}
                  className="px-2 py-1 bg-zinc-700 hover:bg-zinc-600 rounded text-white"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Prompt Input Section */}
      <div className="max-w-3xl mx-auto mb-8">
        <div className="flex gap-2">
          <div className="relative flex-1">
            <textarea
              value={customPrompt}
              onChange={(e) => setCustomPrompt(e.target.value)}
              placeholder={t('arena.customPromptPlaceholder')}
              className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-emerald-500 transition-colors resize-none h-24"
            />
            {showTipoOptions && (
              <div className="absolute top-full left-0 right-0 mt-2 p-3 bg-zinc-800 border border-zinc-700 rounded-lg z-10 shadow-xl">
                <label className="block text-zinc-400 text-xs mb-2 uppercase font-bold tracking-wider">{t('arena.tipoStrength')}</label>
                <div className="flex gap-2">
                  {(['very_short', 'short', 'long', 'very_long'] as const).map((l) => (
                    <button
                      key={l}
                      onClick={() => setTagLength(l)}
                      className={`flex-1 py-1 px-2 rounded text-xs transition-colors ${
                        tagLength === l ? 'bg-emerald-600 text-white' : 'bg-zinc-700 text-zinc-400 hover:bg-zinc-600'
                      }`}
                    >
                      {tagLengthLabels[l]}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
          <div className="flex flex-col gap-2">
            <div className="flex gap-1">
            <button
              onClick={handleOptimize}
              disabled={isOptimizing || !customPrompt}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-zinc-800 hover:bg-zinc-700 disabled:opacity-50 rounded-lg text-emerald-400 transition-colors border border-emerald-500/30"
              title="Optimize with TIPO"
            >
                {isOptimizing ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Wand2 className="w-4 h-4" />}
                TIPO
              </button>
              <button
                onClick={() => setShowTipoOptions(!showTipoOptions)}
                className={`px-2 py-2 rounded-lg transition-colors ${showTipoOptions ? 'bg-emerald-600/20 text-emerald-400' : 'bg-zinc-800 text-zinc-500'}`}
              >
                <Settings className="w-4 h-4" />
              </button>
            </div>
            <button
              onClick={handleNextBattle}
              disabled={isLoading}
              className="flex items-center justify-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 rounded-lg text-white transition-colors"
            >
              {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
              {t('arena.generate')}
            </button>
          </div>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="max-w-3xl mx-auto mb-6">
          <div className="bg-red-900/30 border border-red-700 rounded-lg p-4">
            <div className="text-red-400 text-center">{error}</div>
            {/settings|base model|lora|comfyui/i.test(error) && (
              <div className="text-center mt-2">
                <Link to="/settings" className="text-yellow-200 underline hover:text-yellow-100">
                  {t('arena.goToSettings')} &rarr;
                </Link>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Node Models Status - Show in embedded mode when models not ready */}
      {isEmbeddedMode && !checkingModels && nodeModelsStatus && !nodeModelsStatus.ready && (
        <div className="max-w-3xl mx-auto mb-6">
          <div className="bg-amber-900/30 border border-amber-700 rounded-lg p-4">
            <div className="flex items-center justify-center gap-3 text-amber-400">
              <AlertTriangle className="w-5 h-5" />
              <span>{nodeModelsStatus.message}</span>
            </div>
            <div className="text-center mt-2 text-sm text-amber-300/70">
              请将 Checkpoint Loader 连接到 LoRArena Panel 节点，然后点击 "Queue Prompt"
            </div>
            <div className="flex justify-center mt-3">
              <button
                onClick={checkNodeModels}
                className="flex items-center gap-2 px-4 py-2 bg-amber-600/20 hover:bg-amber-600/30 border border-amber-600/50 rounded-lg text-amber-300 text-sm transition-colors"
              >
                <RefreshCw className="w-4 h-4" />
                刷新状态
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Embedded Mode: Models Ready Indicator */}
      {isEmbeddedMode && !checkingModels && nodeModelsStatus?.ready && (
        <div className="max-w-3xl mx-auto mb-4">
          <div className="bg-emerald-900/20 border border-emerald-700/50 rounded-lg px-4 py-2 flex items-center justify-center gap-2 text-emerald-400 text-sm">
            <Check className="w-4 h-4" />
            <span>模型已就绪，可以开始对战</span>
          </div>
        </div>
      )}

      {/* Battle Info */}
      {battle && (
        <div className="bg-zinc-900 rounded-lg p-4 mb-6">
          <div className="flex flex-wrap gap-4 text-sm text-zinc-400">
            <span><strong>{t('arena.prompt')}:</strong> {battle.prompt}</span>
            <span><strong>{t('arena.seed')}:</strong> {battle.seed}</span>
            <span><strong>{t('arena.steps')}:</strong> {battle.steps}</span>
            <span><strong>{t('arena.cfg')}:</strong> {battle.cfg_scale}</span>
          </div>
        </div>
      )}

      {/* Empty State - Only show when no battle and not loading */}
      {!battle && !isLoading && !error && (
        <div className="bg-zinc-900/60 border border-zinc-800 rounded-2xl p-8 text-center mb-8">
          <h2 className="text-xl font-bold text-white mb-2">{t('arena.readyWhenYouAre')}</h2>
          <p className="text-zinc-400 mb-6">
            {t('arena.enterPromptOrGenerate')}
          </p>
          <button
            onClick={handleNextBattle}
            className="inline-flex items-center gap-2 px-6 py-3 bg-emerald-600 hover:bg-emerald-700 rounded-lg text-white font-bold transition-colors"
          >
            <RefreshCw className="w-5 h-5" />
            {t('arena.generateBattle')}
          </button>
        </div>
      )}

      {/* Images - Show during loading or when ready */}
      {(showImages || isVoted) && battle && (
        <>
          <div className="grid grid-cols-2 gap-4 mb-8">
            {/* Left Image */}
            <div
              onClick={() => canVote && handleVote('left')}
              className={`relative group ${canVote ? 'cursor-pointer' : isLoading ? 'cursor-wait' : 'cursor-not-allowed opacity-70'}`}
            >
              <div
                className={`bg-zinc-900 rounded-lg overflow-hidden border-2 transition-colors ${
                  canVote ? 'border-transparent hover:border-emerald-500' : 'border-transparent'
                } ${isVoted && result?.winner === 'left' ? 'ring-4 ring-green-500' : ''}`}
                style={{ aspectRatio: imageAspect }}
              >
                {hasLeftImage ? (
                  <img
                    src={battle.left_image_url || ''}
                    alt="Left"
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="w-full h-full flex flex-col items-center justify-center text-zinc-500 gap-3">
                    <Loader2 className="w-10 h-10 animate-spin text-emerald-500" />
                    <span>{t('arena.generatingLeft')}</span>
                  </div>
                )}
              </div>
              {canVote && hasLeftImage && (
                <div className="absolute inset-0 flex items-center justify-center bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity rounded-lg">
                  <span className="text-white text-2xl font-bold">A</span>
                </div>
              )}
              {isVoted && result?.winner === 'left' && (
                <div className="absolute top-4 left-4 bg-green-500 text-white px-3 py-1 rounded-full text-sm font-bold">
                  {t('arena.winner')}
                </div>
              )}
              {isVoted && result && !result.left_checkpoint.is_active && (
                <div className="absolute top-4 right-4 bg-red-600 text-white px-3 py-1 rounded-full text-sm font-bold flex items-center gap-1">
                  <Skull className="w-4 h-4" />
                  {t('arena.eliminated')}
                </div>
              )}
              {isVoted && result && (
                <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-4">
                  {/* Hover tooltip for generation details */}
                  <div className="text-xs space-y-1 mb-2 opacity-0 group-hover:opacity-100 transition-opacity">
                    <div>
                      <span className="text-emerald-400">{t('arena.prompt')}:</span>
                      <p className="text-white break-words line-clamp-3">{battle?.prompt}</p>
                    </div>
                    <div className="flex flex-wrap gap-3 text-zinc-200">
                      <span><span className="text-emerald-400">{t('arena.seed')}:</span> {battle?.seed}</span>
                      <span><span className="text-emerald-400">{t('arena.steps')}:</span> {battle?.steps}</span>
                      <span><span className="text-emerald-400">{t('arena.cfg')}:</span> {battle?.cfg_scale}</span>
                    </div>
                  </div>
                  <div className="text-white font-bold">{result.left_checkpoint.name}</div>
                  <div className="flex items-center gap-2 text-sm">
                    <span className="text-zinc-300">{t('arena.elo')}: {result.left_checkpoint.elo_rating.toFixed(0)}</span>
                    {result.elo_changes.find(c => c.checkpoint_id === result.left_checkpoint.id) && (
                      <span className={`flex items-center gap-1 ${
                        result.elo_changes.find(c => c.checkpoint_id === result.left_checkpoint.id)!.change >= 0
                          ? 'text-green-400'
                          : 'text-red-400'
                      }`}>
                        {result.elo_changes.find(c => c.checkpoint_id === result.left_checkpoint.id)!.change >= 0
                          ? <TrendingUp className="w-4 h-4" />
                          : <TrendingDown className="w-4 h-4" />
                        }
                        {result.elo_changes.find(c => c.checkpoint_id === result.left_checkpoint.id)!.change >= 0 ? '+' : ''}
                        {result.elo_changes.find(c => c.checkpoint_id === result.left_checkpoint.id)!.change.toFixed(1)}
                      </span>
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Right Image */}
            <div
              onClick={() => canVote && handleVote('right')}
              className={`relative group ${canVote ? 'cursor-pointer' : isLoading ? 'cursor-wait' : 'cursor-not-allowed opacity-70'}`}
            >
              <div
                className={`bg-zinc-900 rounded-lg overflow-hidden border-2 transition-colors ${
                  canVote ? 'border-transparent hover:border-emerald-500' : 'border-transparent'
                } ${isVoted && result?.winner === 'right' ? 'ring-4 ring-green-500' : ''}`}
                style={{ aspectRatio: imageAspect }}
              >
                {hasRightImage ? (
                  <img
                    src={battle.right_image_url || ''}
                    alt="Right"
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="w-full h-full flex flex-col items-center justify-center text-zinc-500 gap-3">
                    <Loader2 className="w-10 h-10 animate-spin text-emerald-500" />
                    <span>{t('arena.generatingRight')}</span>
                  </div>
                )}
              </div>
              {canVote && hasRightImage && (
                <div className="absolute inset-0 flex items-center justify-center bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity rounded-lg">
                  <span className="text-white text-2xl font-bold">B</span>
                </div>
              )}
              {isVoted && result?.winner === 'right' && (
                <div className="absolute top-4 right-4 bg-green-500 text-white px-3 py-1 rounded-full text-sm font-bold">
                  {t('arena.winner')}
                </div>
              )}
              {isVoted && result && !result.right_checkpoint.is_active && (
                <div className="absolute top-4 left-4 bg-red-600 text-white px-3 py-1 rounded-full text-sm font-bold flex items-center gap-1">
                  <Skull className="w-4 h-4" />
                  {t('arena.eliminated')}
                </div>
              )}
              {isVoted && result && (
                <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-4">
                  {/* Hover tooltip for generation details */}
                  <div className="text-xs space-y-1 mb-2 opacity-0 group-hover:opacity-100 transition-opacity">
                    <div>
                      <span className="text-emerald-400">{t('arena.prompt')}:</span>
                      <p className="text-white break-words line-clamp-3">{battle?.prompt}</p>
                    </div>
                    <div className="flex flex-wrap gap-3 text-zinc-200">
                      <span><span className="text-emerald-400">{t('arena.seed')}:</span> {battle?.seed}</span>
                      <span><span className="text-emerald-400">{t('arena.steps')}:</span> {battle?.steps}</span>
                      <span><span className="text-emerald-400">{t('arena.cfg')}:</span> {battle?.cfg_scale}</span>
                    </div>
                  </div>
                  <div className="text-white font-bold">{result.right_checkpoint.name}</div>
                  <div className="flex items-center gap-2 text-sm">
                    <span className="text-zinc-300">{t('arena.elo')}: {result.right_checkpoint.elo_rating.toFixed(0)}</span>
                    {result.elo_changes.find(c => c.checkpoint_id === result.right_checkpoint.id) && (
                      <span className={`flex items-center gap-1 ${
                        result.elo_changes.find(c => c.checkpoint_id === result.right_checkpoint.id)!.change >= 0
                          ? 'text-green-400'
                          : 'text-red-400'
                      }`}>
                        {result.elo_changes.find(c => c.checkpoint_id === result.right_checkpoint.id)!.change >= 0
                          ? <TrendingUp className="w-4 h-4" />
                          : <TrendingDown className="w-4 h-4" />
                        }
                        {result.elo_changes.find(c => c.checkpoint_id === result.right_checkpoint.id)!.change >= 0 ? '+' : ''}
                        {result.elo_changes.find(c => c.checkpoint_id === result.right_checkpoint.id)!.change.toFixed(1)}
                      </span>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Vote Buttons - Only show when both images are ready and not voted */}
          {isReady && !isVoted && (
            <div className="flex justify-center gap-4">
              <button
                onClick={() => handleVote('left')}
                disabled={!canVote}
                className="flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-lg transition-colors"
              >
                <ChevronLeft className="w-5 h-5" />
                {t('arena.aIsBetter')}
              </button>
              <button
                onClick={() => handleVote('tie')}
                disabled={!canVote}
                className="flex items-center gap-2 px-6 py-3 bg-zinc-700 hover:bg-zinc-600 disabled:opacity-50 rounded-lg transition-colors"
              >
                <Equal className="w-5 h-5" />
                {t('arena.tie')}
              </button>
              <button
                onClick={() => handleVote('right')}
                disabled={!canVote}
                className="flex items-center gap-2 px-6 py-3 bg-green-600 hover:bg-green-700 disabled:opacity-50 rounded-lg transition-colors"
              >
                {t('arena.bIsBetter')}
                <ChevronRight className="w-5 h-5" />
              </button>
              <button
                onClick={() => handleVote('skip')}
                disabled={!canVote}
                className="flex items-center gap-2 px-6 py-3 bg-zinc-800 hover:bg-zinc-700 disabled:opacity-50 rounded-lg transition-colors text-zinc-400"
              >
                <SkipForward className="w-5 h-5" />
                {t('arena.skip')}
              </button>
            </div>
          )}

          {/* Loading indicator for vote buttons area */}
          {isLoading && (!hasLeftImage || !hasRightImage) && (
            <div className="flex justify-center">
              <div className="bg-zinc-900/80 rounded-lg px-6 py-3 flex items-center gap-3 text-zinc-400">
                <Loader2 className="w-5 h-5 animate-spin text-emerald-500" />
                <span>{t('arena.waitingForImages')}</span>
              </div>
            </div>
          )}

          {/* Next Battle Button - Only show after voting */}
          {isVoted && (
            <div className="flex justify-center mt-8">
              <button
                onClick={handleNextBattle}
                className="flex items-center gap-2 px-8 py-4 bg-emerald-600 hover:bg-emerald-700 rounded-lg text-lg font-bold transition-colors"
              >
                <RefreshCw className="w-5 h-5" />
                {t('arena.nextBattle')}
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
