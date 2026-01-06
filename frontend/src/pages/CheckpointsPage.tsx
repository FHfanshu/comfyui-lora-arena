import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { checkpointsApi } from '../services/api';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import {
  FolderOpen,
  RefreshCw,
  Search,
  ToggleLeft,
  ToggleRight,
  Trash2,
  Edit2,
  X,
  Check,
  Power,
  PowerOff,
} from 'lucide-react';
import type { Checkpoint, ScanResponse } from '../types';

export function CheckpointsPage() {
  const { t } = useTranslation();
  const [checkpoints, setCheckpoints] = useState<Checkpoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [scanResult, setScanResult] = useState<ScanResponse | null>(null);
  const [scanning, setScanning] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editName, setEditName] = useState('');
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());

  useEffect(() => {
    loadCheckpoints();
  }, []);

  const loadCheckpoints = async () => {
    try {
      setLoading(true);
      // Load all checkpoints (up to 1000)
      const data = await checkpointsApi.list(1, 1000, 'elo_rating');
      setCheckpoints(data.items);
    } catch (err: any) {
      setError(err.message || 'Failed to load checkpoints');
    } finally {
      setLoading(false);
    }
  };

  const handleScan = async () => {
    try {
      setScanning(true);
      setScanResult(null);
      const result = await checkpointsApi.scan();
      setScanResult(result);
      if (result.imported > 0) {
        await loadCheckpoints();
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Scan failed');
    } finally {
      setScanning(false);
    }
  };

  const handleToggleActive = async (id: number) => {
    try {
      const updated = await checkpointsApi.toggleActive(id);
      setCheckpoints(prev =>
        prev.map(c => (c.id === id ? updated : c))
      );
    } catch (err) {
      console.error('Toggle failed:', err);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm(t('checkpoints.deleteConfirm'))) {
      return;
    }

    try {
      await checkpointsApi.delete(id);
      setCheckpoints(prev => prev.filter(c => c.id !== id));
    } catch (err) {
      console.error('Delete failed:', err);
    }
  };

  const handleStartEdit = (checkpoint: Checkpoint) => {
    setEditingId(checkpoint.id);
    setEditName(checkpoint.name);
  };

  const handleSaveEdit = async () => {
    if (!editingId) return;

    try {
      const updated = await checkpointsApi.update(editingId, { name: editName });
      setCheckpoints(prev =>
        prev.map(c => (c.id === editingId ? updated : c))
      );
      setEditingId(null);
    } catch (err) {
      console.error('Update failed:', err);
    }
  };

  const handleCancelEdit = () => {
    setEditingId(null);
    setEditName('');
  };

  const handleToggleSelect = (id: number) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const handleSelectAll = () => {
    if (selectedIds.size === filteredCheckpoints.length && filteredCheckpoints.length > 0) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(filteredCheckpoints.map(c => c.id)));
    }
  };

  const handleBatchDelete = async () => {
    if (selectedIds.size === 0) return;
    if (!confirm(t('checkpoints.batchDeleteConfirm', { count: selectedIds.size }))) {
      return;
    }

    try {
      await checkpointsApi.batchDelete(Array.from(selectedIds));
      setCheckpoints(prev => prev.filter(c => !selectedIds.has(c.id)));
      setSelectedIds(new Set());
    } catch (err: any) {
      setError(err.message || 'Batch delete failed');
    }
  };

  const handleBatchEnable = async () => {
    if (selectedIds.size === 0) return;
    try {
      await checkpointsApi.batchUpdateStatus(Array.from(selectedIds), true);
      setCheckpoints(prev =>
        prev.map(c => (selectedIds.has(c.id) ? { ...c, is_active: true } : c))
      );
      setSelectedIds(new Set());
    } catch (err: any) {
      setError(err.message || 'Batch enable failed');
    }
  };

  const handleBatchDisable = async () => {
    if (selectedIds.size === 0) return;
    try {
      await checkpointsApi.batchUpdateStatus(Array.from(selectedIds), false);
      setCheckpoints(prev =>
        prev.map(c => (selectedIds.has(c.id) ? { ...c, is_active: false } : c))
      );
      setSelectedIds(new Set());
    } catch (err: any) {
      setError(err.message || 'Batch disable failed');
    }
  };

  const filteredCheckpoints = checkpoints.filter(c =>
    c.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    c.filename.toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <LoadingSpinner size="lg" text={t('checkpoints.loadingCheckpoints')} />
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white flex items-center gap-3">
            <FolderOpen className="w-8 h-8 text-emerald-400" />
            {t('checkpoints.title')}
          </h1>
          <p className="text-zinc-400 mt-1">
            {t('checkpoints.checkpointsCount', { count: checkpoints.length, active: checkpoints.filter(c => c.is_active).length })}
          </p>
        </div>

        <button
          onClick={handleScan}
          disabled={scanning}
          className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 rounded-lg transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${scanning ? 'animate-spin' : ''}`} />
          {scanning ? t('checkpoints.scanning') : t('checkpoints.scanDirectory')}
        </button>
      </div>

      {/* Scan Result */}
      {scanResult && (
        <div className="bg-zinc-900 rounded-lg p-4 mb-6">
          <div className="flex items-center gap-4 text-sm">
            <span className="text-zinc-400">{t('checkpoints.scanned')}: {scanResult.scanned}</span>
            <span className="text-green-400">{t('checkpoints.imported')}: {scanResult.imported}</span>
            <span className="text-yellow-400">{t('checkpoints.skipped')}: {scanResult.skipped}</span>
            {scanResult.errors.length > 0 && (
              <span className="text-red-400">{t('checkpoints.errors')}: {scanResult.errors.length}</span>
            )}
          </div>
          {scanResult.errors.length > 0 && (
            <div className="mt-2 text-red-400 text-sm">
              {scanResult.errors.map((err, i) => (
                <div key={i}>{err}</div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="bg-red-900/30 border border-red-700 rounded-lg p-4 mb-6">
          <div className="text-red-400">{error}</div>
        </div>
      )}

      {/* Search & Actions */}
      <div className="flex flex-col md:flex-row gap-4 mb-6">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-zinc-500" />
          <input
            type="text"
            placeholder={t('checkpoints.searchPlaceholder')}
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-zinc-900 border border-zinc-700 rounded-lg text-white placeholder-zinc-500 focus:outline-none focus:border-emerald-500"
          />
        </div>

        {selectedIds.size > 0 && (
          <div className="flex items-center gap-4 bg-zinc-900 border border-emerald-500/30 rounded-lg px-4 py-1">
            <span className="text-zinc-400 text-sm">
              {t('checkpoints.selectedCount', { count: selectedIds.size })}
            </span>
            <button
              onClick={handleBatchEnable}
              className="flex items-center gap-2 px-3 py-1 bg-green-600/20 hover:bg-green-600/30 text-green-400 rounded-md transition-colors text-sm"
            >
              <Power className="w-4 h-4" />
              {t('checkpoints.batchEnable')}
            </button>
            <button
              onClick={handleBatchDisable}
              className="flex items-center gap-2 px-3 py-1 bg-zinc-600/20 hover:bg-zinc-600/30 text-zinc-400 rounded-md transition-colors text-sm"
            >
              <PowerOff className="w-4 h-4" />
              {t('checkpoints.batchDisable')}
            </button>
            <button
              onClick={handleBatchDelete}
              className="flex items-center gap-2 px-3 py-1 bg-red-600/20 hover:bg-red-600/30 text-red-400 rounded-md transition-colors text-sm"
            >
              <Trash2 className="w-4 h-4" />
              {t('checkpoints.batchDelete')}
            </button>
            <button
              onClick={() => setSelectedIds(new Set())}
              className="text-zinc-500 hover:text-white"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>

      {/* Checkpoints List */}
      <div className="bg-zinc-900 rounded-lg overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="bg-zinc-800">
              <th className="px-4 py-3 text-center w-10">
                <input
                  type="checkbox"
                  checked={selectedIds.size === filteredCheckpoints.length && filteredCheckpoints.length > 0}
                  onChange={handleSelectAll}
                  className="rounded border-zinc-700 bg-zinc-800 text-emerald-500 focus:ring-emerald-500"
                />
              </th>
              <th className="px-4 py-3 text-left text-zinc-400 font-medium">{t('checkpoints.name')}</th>
              <th className="px-4 py-3 text-left text-zinc-400 font-medium">{t('checkpoints.filename')}</th>
              <th className="px-4 py-3 text-right text-zinc-400 font-medium">{t('checkpoints.elo')}</th>
              <th className="px-4 py-3 text-right text-zinc-400 font-medium">{t('checkpoints.battles')}</th>
              <th className="px-4 py-3 text-center text-zinc-400 font-medium">{t('checkpoints.active')}</th>
              <th className="px-4 py-3 text-center text-zinc-400 font-medium">{t('checkpoints.actions')}</th>
            </tr>
          </thead>
          <tbody>
            {filteredCheckpoints.map((checkpoint) => (
              <tr
                key={checkpoint.id}
                className={`border-t border-zinc-800 hover:bg-zinc-800/50 ${selectedIds.has(checkpoint.id) ? 'bg-emerald-500/5' : ''}`}
              >
                <td className="px-4 py-3 text-center">
                  <input
                    type="checkbox"
                    checked={selectedIds.has(checkpoint.id)}
                    onChange={() => handleToggleSelect(checkpoint.id)}
                    className="rounded border-zinc-700 bg-zinc-800 text-emerald-500 focus:ring-emerald-500"
                  />
                </td>
                <td className="px-4 py-3">
                  {editingId === checkpoint.id ? (
                    <div className="flex items-center gap-2">
                      <input
                        type="text"
                        value={editName}
                        onChange={(e) => setEditName(e.target.value)}
                        className="px-2 py-1 bg-zinc-700 border border-zinc-600 rounded text-white"
                        autoFocus
                      />
                      <button
                        onClick={handleSaveEdit}
                        className="p-1 text-green-400 hover:text-green-300"
                      >
                        <Check className="w-4 h-4" />
                      </button>
                      <button
                        onClick={handleCancelEdit}
                        className="p-1 text-zinc-400 hover:text-zinc-300"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  ) : (
                    <div className="font-medium text-white">{checkpoint.name}</div>
                  )}
                </td>
                <td className="px-4 py-3 text-zinc-400 text-sm font-mono">
                  {checkpoint.filename}
                </td>
                <td className="px-4 py-3 text-right">
                  <span className="text-emerald-400 font-bold">
                    {checkpoint.elo_rating.toFixed(0)}
                  </span>
                </td>
                <td className="px-4 py-3 text-right text-zinc-400">
                  {checkpoint.total_battles}
                </td>
                <td className="px-4 py-3 text-center">
                  <button
                    onClick={() => handleToggleActive(checkpoint.id)}
                    className="text-2xl"
                  >
                    {checkpoint.is_active ? (
                      <ToggleRight className="w-8 h-8 text-green-500" />
                    ) : (
                      <ToggleLeft className="w-8 h-8 text-zinc-600" />
                    )}
                  </button>
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center justify-center gap-2">
                    <button
                      onClick={() => handleStartEdit(checkpoint)}
                      className="p-1 text-zinc-400 hover:text-white transition-colors"
                    >
                      <Edit2 className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => handleDelete(checkpoint.id)}
                      className="p-1 text-zinc-400 hover:text-red-400 transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {filteredCheckpoints.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-zinc-500">
                  {checkpoints.length === 0
                    ? t('checkpoints.noCheckpoints')
                    : t('checkpoints.noMatchingCheckpoints')}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
