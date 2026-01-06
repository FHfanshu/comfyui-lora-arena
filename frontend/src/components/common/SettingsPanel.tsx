import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { configApi } from '../../services/api';
import { X, Settings, Save } from 'lucide-react';
import type { Config, ComfyUIModels } from '../../types';

interface SettingsPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

export function SettingsPanel({ isOpen, onClose }: SettingsPanelProps) {
  const { t } = useTranslation();
  const [models, setModels] = useState<ComfyUIModels | null>(null);
  const [formData, setFormData] = useState<Partial<Config>>({});
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  useEffect(() => {
    if (isOpen) {
      loadData();
    }
  }, [isOpen]);

  const loadData = async () => {
    try {
      const [configData, modelsData] = await Promise.all([
        configApi.get(),
        configApi.getComfyUIModels().catch(() => null),
      ]);
      setFormData(configData);
      setModels(modelsData);
    } catch (err) {
      console.error('Failed to load settings:', err);
    }
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      await configApi.update(formData);
      setMessage({ type: 'success', text: t('settings.savedSuccess') });
      setTimeout(() => setMessage(null), 2000);
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message });
    } finally {
      setSaving(false);
    }
  };

  const updateField = (field: keyof Config, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 z-40"
        onClick={onClose}
      />

      {/* Panel */}
      <div className="fixed right-0 top-0 h-full w-96 bg-zinc-900 z-50 shadow-xl overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-zinc-900 border-b border-zinc-800 p-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Settings className="w-5 h-5 text-emerald-400" />
            <h2 className="text-lg font-bold text-white">{t('settings.title')}</h2>
          </div>
          <button onClick={onClose} className="p-1 hover:bg-zinc-800 rounded">
            <X className="w-5 h-5 text-zinc-400" />
          </button>
        </div>

        {/* Message */}
        {message && (
          <div className={`mx-4 mt-4 p-3 rounded-lg text-sm ${
            message.type === 'success' ? 'bg-green-900/50 text-green-400' : 'bg-red-900/50 text-red-400'
          }`}>
            {message.text}
          </div>
        )}

        {/* Content */}
        <div className="p-4 space-y-4">
          {/* LoRA Directory */}
          <Section title={t('settings.loraDirectory')}>
            <Input
              label={t('settings.loraDirectoryPath')}
              value={formData.lora_directory || ''}
              onChange={(v) => updateField('lora_directory', v)}
              placeholder="styles/748cm"
            />
          </Section>

          {/* Base Model */}
          <Section title={t('settings.baseModel')}>
            {models?.checkpoints?.length ? (
              <Select
                value={formData.base_model || ''}
                onChange={(v) => updateField('base_model', v)}
                options={models.checkpoints}
              />
            ) : (
              <Input
                value={formData.base_model || ''}
                onChange={(v) => updateField('base_model', v)}
                placeholder="sd_xl_base_1.0.safetensors"
              />
            )}
          </Section>

          {/* Generation Params */}
          <Section title={t('settings.generationParams')}>
            <div className="grid grid-cols-2 gap-3">
              <Input
                label={t('settings.steps')}
                type="number"
                value={formData.steps || 20}
                onChange={(v) => updateField('steps', parseInt(v))}
              />
              <Input
                label={t('settings.cfgScale')}
                type="number"
                value={formData.cfg_scale || 7}
                onChange={(v) => updateField('cfg_scale', parseFloat(v))}
              />
              <Input
                label={t('settings.width')}
                type="number"
                value={formData.width || 1024}
                onChange={(v) => updateField('width', parseInt(v))}
              />
              <Input
                label={t('settings.height')}
                type="number"
                value={formData.height || 1024}
                onChange={(v) => updateField('height', parseInt(v))}
              />
              <Input
                label={t('settings.loraStrength')}
                type="number"
                value={formData.lora_strength || 0.8}
                onChange={(v) => updateField('lora_strength', parseFloat(v))}
              />
            </div>
          </Section>

          {/* Save Button */}
          <button
            onClick={handleSave}
            disabled={saving}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 rounded-lg font-bold"
          >
            <Save className="w-4 h-4" />
            {saving ? t('settings.saving') : t('settings.saveSettings')}
          </button>
        </div>
      </div>
    </>
  );
}

// Helper components
function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-zinc-800/50 rounded-lg p-3">
      <h3 className="text-sm font-medium text-zinc-400 mb-3">{title}</h3>
      {children}
    </div>
  );
}

function Input({ label, value, onChange, type = 'text', placeholder = '' }: {
  label?: string;
  value: string | number;
  onChange: (v: string) => void;
  type?: string;
  placeholder?: string;
}) {
  return (
    <div>
      {label && <label className="block text-xs text-zinc-500 mb-1">{label}</label>}
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded text-sm text-white focus:outline-none focus:border-emerald-500"
      />
    </div>
  );
}

function Select({ value, onChange, options }: {
  value: string;
  onChange: (v: string) => void;
  options: string[];
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded text-sm text-white focus:outline-none focus:border-emerald-500"
    >
      {options.map((opt) => (
        <option key={opt} value={opt}>{opt}</option>
      ))}
    </select>
  );
}
