import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { configApi } from '../services/api';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import {
  Settings,
  Server,
  CheckCircle,
  XCircle,
  Save,
  RefreshCw,
} from 'lucide-react';
import type { Config, ComfyUIStatus, ComfyUIModels } from '../types';

export function SettingsPage() {
  const { t } = useTranslation();
  const [config, setConfig] = useState<Config | null>(null);
  const [status, setStatus] = useState<ComfyUIStatus | null>(null);
  const [models, setModels] = useState<ComfyUIModels | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Form state
  const [formData, setFormData] = useState<Partial<Config>>({});

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [configData, statusData] = await Promise.all([
        configApi.get(),
        configApi.getComfyUIStatus(),
      ]);
      setConfig(configData);
      setFormData(configData);
      setStatus(statusData);

      if (statusData.connected) {
        try {
          const modelsData = await configApi.getComfyUIModels();
          setModels(modelsData);

          // If current base_model is not in the available list, update to first available
          if (modelsData.checkpoints && modelsData.checkpoints.length > 0) {
            const currentBaseModel = configData.base_model;
            if (!modelsData.checkpoints.includes(currentBaseModel)) {
              setFormData(prev => ({ ...prev, base_model: modelsData.checkpoints[0] }));
            }
          }
        } catch (err) {
          console.error('Failed to load models:', err);
        }
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load settings');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setError(null);
      setSuccess(null);
      const updated = await configApi.update(formData);
      setConfig(updated);
      setSuccess(t('settings.savedSuccess'));
      setTimeout(() => setSuccess(null), 3000);
    } catch (err: any) {
      setError(err.message || 'Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  const handleCheckConnection = async () => {
    try {
      // Update URL first if changed
      if (formData.comfyui_url !== config?.comfyui_url) {
        await configApi.update({ comfyui_url: formData.comfyui_url });
      }
      const statusData = await configApi.getComfyUIStatus();
      setStatus(statusData);

      if (statusData.connected) {
        const modelsData = await configApi.getComfyUIModels();
        setModels(modelsData);
      }
    } catch (err: any) {
      setStatus({ connected: false, url: formData.comfyui_url || '', error: err.message });
    }
  };

  const updateField = (field: keyof Config, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <LoadingSpinner size="lg" text={t('settings.loadingSettings')} />
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <div className="flex items-center gap-3 mb-8">
        <Settings className="w-8 h-8 text-emerald-400" />
        <h1 className="text-3xl font-bold text-white">{t('settings.title')}</h1>
      </div>

      {error && (
        <div className="bg-red-900/30 border border-red-700 rounded-lg p-4 mb-6">
          <div className="text-red-400">{error}</div>
        </div>
      )}

      {success && (
        <div className="bg-green-900/30 border border-green-700 rounded-lg p-4 mb-6">
          <div className="text-green-400">{success}</div>
        </div>
      )}

      <div className="space-y-6">
        {/* ComfyUI Connection */}
        <div className="bg-zinc-900 rounded-lg p-6">
          <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
            <Server className="w-5 h-5" />
            {t('settings.comfyuiConnection')}
          </h2>

          <div className="flex items-end gap-4 mb-4">
            <div className="flex-1">
              <label className="block text-zinc-400 text-sm mb-2">{t('settings.serverUrl')}</label>
              <input
                type="text"
                value={formData.comfyui_url || ''}
                onChange={(e) => updateField('comfyui_url', e.target.value)}
                placeholder="http://localhost:8188"
                className="w-full px-4 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white focus:outline-none focus:border-emerald-500"
              />
            </div>
            <button
              onClick={handleCheckConnection}
              className="flex items-center gap-2 px-4 py-2 bg-zinc-700 hover:bg-zinc-600 rounded-lg transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
              {t('common.test')}
            </button>
          </div>

          {status && (
            <div className={`flex items-center gap-2 ${status.connected ? 'text-green-400' : 'text-red-400'}`}>
              {status.connected ? (
                <>
                  <CheckCircle className="w-5 h-5" />
                  <span>{t('settings.connectedToComfyUI')}</span>
                </>
              ) : (
                <>
                  <XCircle className="w-5 h-5" />
                  <span>{status.error || t('settings.notConnected')}</span>
                </>
              )}
            </div>
          )}
        </div>

        {/* LoRA Directory */}
        <div className="bg-zinc-900 rounded-lg p-6">
          <h2 className="text-xl font-bold text-white mb-4">{t('settings.loraDirectory')}</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-zinc-400 text-sm mb-2">
                {t('settings.loraDirectoryPath')}
              </label>
              <input
                type="text"
                value={formData.lora_directory || ''}
                onChange={(e) => updateField('lora_directory', e.target.value)}
                placeholder={formData.remote_comfyui ? "other-styles/748cm/v03" : "/path/to/loras"}
                className="w-full px-4 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white focus:outline-none focus:border-emerald-500"
              />
              {formData.remote_comfyui && (
                <p className="text-zinc-500 text-xs mt-1">{t('settings.remoteComfyuiHint')}</p>
              )}
            </div>
            <div className="flex items-center justify-between">
              <div>
                <span className="text-white">{t('settings.remoteComfyui')}</span>
                <p className="text-zinc-500 text-sm">{t('settings.remoteComfyuiDesc')}</p>
              </div>
              <button
                type="button"
                onClick={() => updateField('remote_comfyui', !formData.remote_comfyui)}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  formData.remote_comfyui ? 'bg-emerald-600' : 'bg-zinc-700'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    formData.remote_comfyui ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>
          </div>
        </div>

        {/* Generation Parameters */}
        <div className="bg-zinc-900 rounded-lg p-6">
          <h2 className="text-xl font-bold text-white mb-4">{t('settings.generationParams')}</h2>

          <div className="grid grid-cols-2 gap-4">
            {/* Base Model */}
            <div className="col-span-2">
              <label className="block text-zinc-400 text-sm mb-2">{t('settings.baseModel')}</label>
              {models?.checkpoints && models.checkpoints.length > 0 ? (
                <select
                  value={formData.base_model || ''}
                  onChange={(e) => updateField('base_model', e.target.value)}
                  className="w-full px-4 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white focus:outline-none focus:border-emerald-500"
                >
                  {models.checkpoints.map((ckpt) => (
                    <option key={ckpt} value={ckpt}>
                      {ckpt}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  type="text"
                  value={formData.base_model || ''}
                  onChange={(e) => updateField('base_model', e.target.value)}
                  placeholder="sd_xl_base_1.0.safetensors"
                  className="w-full px-4 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white focus:outline-none focus:border-emerald-500"
                />
              )}
            </div>

            {/* Sampler */}
            <div>
              <label className="block text-zinc-400 text-sm mb-2">{t('settings.sampler')}</label>
              {models?.samplers && models.samplers.length > 0 ? (
                <select
                  value={formData.sampler || ''}
                  onChange={(e) => updateField('sampler', e.target.value)}
                  className="w-full px-4 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white focus:outline-none focus:border-emerald-500"
                >
                  {models.samplers.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  type="text"
                  value={formData.sampler || ''}
                  onChange={(e) => updateField('sampler', e.target.value)}
                  placeholder="euler_ancestral"
                  className="w-full px-4 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white focus:outline-none focus:border-emerald-500"
                />
              )}
            </div>

            {/* Scheduler */}
            <div>
              <label className="block text-zinc-400 text-sm mb-2">{t('settings.scheduler')}</label>
              <input
                type="text"
                value={formData.scheduler || ''}
                onChange={(e) => updateField('scheduler', e.target.value)}
                placeholder="normal"
                className="w-full px-4 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white focus:outline-none focus:border-emerald-500"
              />
            </div>

            {/* Steps */}
            <div>
              <label className="block text-zinc-400 text-sm mb-2">{t('settings.steps')}</label>
              <input
                type="number"
                value={formData.steps || 20}
                onChange={(e) => updateField('steps', parseInt(e.target.value))}
                min="1"
                max="100"
                className="w-full px-4 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white focus:outline-none focus:border-emerald-500"
              />
            </div>

            {/* CFG Scale */}
            <div>
              <label className="block text-zinc-400 text-sm mb-2">{t('settings.cfgScale')}</label>
              <input
                type="number"
                value={formData.cfg_scale || 7}
                onChange={(e) => updateField('cfg_scale', parseFloat(e.target.value))}
                min="1"
                max="20"
                step="0.5"
                className="w-full px-4 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white focus:outline-none focus:border-emerald-500"
              />
            </div>

            {/* LoRA Strength */}
            <div>
              <label className="block text-zinc-400 text-sm mb-2">{t('settings.loraStrength')}</label>
              <input
                type="number"
                value={formData.lora_strength || 0.8}
                onChange={(e) => updateField('lora_strength', parseFloat(e.target.value))}
                min="0"
                max="2"
                step="0.1"
                className="w-full px-4 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white focus:outline-none focus:border-emerald-500"
              />
            </div>

            {/* Width */}
            <div>
              <label className="block text-zinc-400 text-sm mb-2">{t('settings.width')}</label>
              <input
                type="number"
                value={formData.width || 1024}
                onChange={(e) => updateField('width', parseInt(e.target.value))}
                min="256"
                max="2048"
                step="64"
                className="w-full px-4 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white focus:outline-none focus:border-emerald-500"
              />
            </div>

            {/* Height */}
            <div>
              <label className="block text-zinc-400 text-sm mb-2">{t('settings.height')}</label>
              <input
                type="number"
                value={formData.height || 1024}
                onChange={(e) => updateField('height', parseInt(e.target.value))}
                min="256"
                max="2048"
                step="64"
                className="w-full px-4 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white focus:outline-none focus:border-emerald-500"
              />
            </div>
          </div>
        </div>

        {/* TIPO & Background Worker */}
        <div className="bg-zinc-900 rounded-lg p-6">
          <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
            <RefreshCw className="w-5 h-5" />
            {t('settings.tipoAndWorker')}
          </h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-zinc-400 text-sm mb-2">{t('settings.tipoTagLength')}</label>
              <select
                value={formData.tipo_tag_length || 'long'}
                onChange={(e) => updateField('tipo_tag_length', e.target.value as any)}
                className="w-full px-4 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white focus:outline-none focus:border-emerald-500"
              >
                <option value="very_short">{t('arena.veryShort')}</option>
                <option value="short">{t('arena.short')}</option>
                <option value="long">{t('arena.long')}</option>
                <option value="very_long">{t('arena.veryLong')}</option>
              </select>
            </div>
            <div>
              <label className="block text-zinc-400 text-sm mb-2">{t('settings.workerInterval')}</label>
              <input
                type="number"
                value={formData.worker_interval || 10}
                onChange={(e) => updateField('worker_interval', parseInt(e.target.value))}
                min="5"
                className="w-full px-4 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white focus:outline-none focus:border-emerald-500"
              />
            </div>
            <div>
              <label className="block text-zinc-400 text-sm mb-2">{t('settings.targetCache')}</label>
              <input
                type="number"
                value={formData.worker_target_cache || 5}
                onChange={(e) => updateField('worker_target_cache', parseInt(e.target.value))}
                min="1"
                className="w-full px-4 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white focus:outline-none focus:border-emerald-500"
              />
            </div>
            <div className="flex flex-col gap-2">
              <label className="block text-zinc-400 text-sm mb-2">{t('settings.workerUseTrainingTags')}</label>
              <button
                onClick={() => updateField('worker_use_training_tags', !formData.worker_use_training_tags)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors w-fit ${
                  formData.worker_use_training_tags
                    ? 'bg-emerald-600 text-white'
                    : 'bg-zinc-700 text-zinc-400'
                }`}
              >
                {formData.worker_use_training_tags ? <CheckCircle className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
                {formData.worker_use_training_tags ? t('common.enabled') : t('common.disabled')}
              </button>
            </div>
            <div className="col-span-2">
              <label className="block text-zinc-400 text-sm mb-2">{t('settings.parallelGeneration')}</label>
              <button
                onClick={() => updateField('parallel_generation', !formData.parallel_generation)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                  formData.parallel_generation
                    ? 'bg-emerald-600 text-white'
                    : 'bg-zinc-700 text-zinc-400'
                }`}
              >
                {formData.parallel_generation ? <CheckCircle className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
                {formData.parallel_generation ? t('common.enabled') : t('common.disabled')}
              </button>
            </div>
            <div className="col-span-2 flex items-center gap-2 mt-2">
              <button
                onClick={() => updateField('worker_enabled', !formData.worker_enabled)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                  formData.worker_enabled
                    ? 'bg-emerald-600 text-white'
                    : 'bg-zinc-700 text-zinc-400'
                }`}
              >
                {formData.worker_enabled ? <CheckCircle className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
                {t('settings.backgroundPregeneration')} {formData.worker_enabled ? t('common.enabled') : t('common.disabled')}
              </button>
            </div>
          </div>
        </div>

        {/* Battle Royale Mode */}
        <div className="bg-zinc-900 rounded-lg p-6">
          <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
            <RefreshCw className="w-5 h-5 text-orange-400" />
            {t('settings.battleRoyaleMode')}
          </h2>
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <button
                onClick={() => updateField('battle_royale_enabled', !formData.battle_royale_enabled)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                  formData.battle_royale_enabled
                    ? 'bg-orange-600 text-white'
                    : 'bg-zinc-700 text-zinc-400'
                }`}
              >
                {formData.battle_royale_enabled ? <CheckCircle className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
                {t('settings.battleRoyaleMode')} {formData.battle_royale_enabled ? t('common.enabled') : t('common.disabled')}
              </button>
              <p className="text-zinc-500 text-xs mt-2">
                {t('settings.battleRoyaleModeDesc')}
              </p>
            </div>

            <div>
              <label className="block text-zinc-400 text-sm mb-2">{t('settings.minBattlesForElimination')}</label>
              <input
                type="number"
                value={formData.battle_royale_threshold || 10}
                onChange={(e) => updateField('battle_royale_threshold', parseInt(e.target.value))}
                min="1"
                className="w-full px-4 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white focus:outline-none focus:border-emerald-500"
              />
            </div>

            <div>
              <label className="block text-zinc-400 text-sm mb-2">{t('settings.winRateThreshold')}</label>
              <input
                type="number"
                value={formData.battle_royale_win_rate || 0.5}
                onChange={(e) => updateField('battle_royale_win_rate', parseFloat(e.target.value))}
                min="0"
                max="1"
                step="0.05"
                className="w-full px-4 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white focus:outline-none focus:border-emerald-500"
              />
            </div>
          </div>
        </div>

        {/* Save Button */}
        <div className="flex justify-end">
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-2 px-6 py-3 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 rounded-lg font-bold transition-colors"
          >
            <Save className="w-5 h-5" />
            {saving ? t('settings.saving') : t('settings.saveSettings')}
          </button>
        </div>
      </div>
    </div>
  );
}
