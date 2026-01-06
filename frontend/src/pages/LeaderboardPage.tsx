import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { leaderboardApi } from '../services/api';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { Trophy, TrendingUp, Swords } from 'lucide-react';
import type { LeaderboardEntry, ELOHistoryResponse } from '../types';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

export function LeaderboardPage() {
  const { t } = useTranslation();
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [history, setHistory] = useState<ELOHistoryResponse | null>(null);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [minBattles, setMinBattles] = useState(0);

  useEffect(() => {
    loadLeaderboard();
  }, [minBattles]);

  useEffect(() => {
    if (selectedId) {
      loadHistory(selectedId);
    }
  }, [selectedId]);

  const loadLeaderboard = async () => {
    try {
      setLoading(true);
      const data = await leaderboardApi.get(minBattles);
      setLeaderboard(data.items);
    } catch (err: any) {
      setError(err.message || 'Failed to load leaderboard');
    } finally {
      setLoading(false);
    }
  };

  const loadHistory = async (id: number) => {
    try {
      setHistoryLoading(true);
      const data = await leaderboardApi.getHistory(id);
      setHistory(data);
    } catch (err) {
      console.error('Failed to load history:', err);
    } finally {
      setHistoryLoading(false);
    }
  };

  const getRankBadge = (rank: number) => {
    if (rank === 1) return <Trophy className="w-5 h-5 text-yellow-400" />;
    if (rank === 2) return <Trophy className="w-5 h-5 text-gray-400" />;
    if (rank === 3) return <Trophy className="w-5 h-5 text-amber-600" />;
    return <span className="text-zinc-500">{rank}</span>;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <LoadingSpinner size="lg" text={t('leaderboard.loadingLeaderboard')} />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-red-500">{error}</div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white flex items-center gap-3">
            <Trophy className="w-8 h-8 text-yellow-400" />
            {t('leaderboard.title')}
          </h1>
          <p className="text-zinc-400 mt-1">{t('leaderboard.subtitle')}</p>
        </div>

        <div className="flex items-center gap-2">
          <label className="text-zinc-400 text-sm">{t('leaderboard.minBattles')}</label>
          <input
            type="number"
            value={minBattles}
            onChange={(e) => setMinBattles(Math.max(0, parseInt(e.target.value) || 0))}
            className="w-20 px-3 py-1 bg-zinc-800 border border-zinc-700 rounded-lg text-white"
            min="0"
          />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Leaderboard Table */}
        <div className="lg:col-span-2">
          <div className="bg-zinc-900 rounded-lg overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="bg-zinc-800">
                  <th className="px-4 py-3 text-left text-zinc-400 font-medium">{t('leaderboard.rank')}</th>
                  <th className="px-4 py-3 text-left text-zinc-400 font-medium">{t('leaderboard.name')}</th>
                  <th className="px-4 py-3 text-right text-zinc-400 font-medium">{t('leaderboard.elo')}</th>
                  <th className="px-4 py-3 text-right text-zinc-400 font-medium">{t('leaderboard.battles')}</th>
                  <th className="px-4 py-3 text-right text-zinc-400 font-medium">{t('leaderboard.winRate')}</th>
                </tr>
              </thead>
              <tbody>
                {leaderboard.map((entry) => (
                  <tr
                    key={entry.checkpoint_id}
                    onClick={() => setSelectedId(entry.checkpoint_id)}
                    className={`border-t border-zinc-800 cursor-pointer transition-colors ${
                      selectedId === entry.checkpoint_id
                        ? 'bg-emerald-900/30'
                        : 'hover:bg-zinc-800'
                    }`}
                  >
                    <td className="px-4 py-3 w-12">{getRankBadge(entry.rank)}</td>
                    <td className="px-4 py-3">
                      <div className="font-medium text-white">{entry.name}</div>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span className="text-emerald-400 font-bold">
                        {entry.elo_rating.toFixed(0)}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right text-zinc-400">
                      {entry.total_battles}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span className={entry.win_rate >= 0.5 ? 'text-green-400' : 'text-zinc-400'}>
                        {(entry.win_rate * 100).toFixed(1)}%
                      </span>
                    </td>
                  </tr>
                ))}
                {leaderboard.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-4 py-8 text-center text-zinc-500">
                      {t('leaderboard.noCheckpoints')}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Details Panel */}
        <div className="lg:col-span-1">
          {selectedId && history ? (
            <div className="bg-zinc-900 rounded-lg p-4">
              <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-emerald-400" />
                {history.checkpoint_name}
              </h3>

              {historyLoading ? (
                <div className="h-48 flex items-center justify-center">
                  <LoadingSpinner size="sm" />
                </div>
              ) : history.history.length > 1 ? (
                <div className="h-48">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={history.history}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                      <XAxis
                        dataKey="recorded_at"
                        tick={{ fill: '#888', fontSize: 10 }}
                        tickFormatter={(value) => new Date(value).toLocaleDateString()}
                      />
                      <YAxis
                        domain={['dataMin - 50', 'dataMax + 50']}
                        tick={{ fill: '#888', fontSize: 10 }}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#1a1a1a',
                          border: '1px solid #333',
                          borderRadius: '8px',
                        }}
                        labelFormatter={(value) => new Date(value).toLocaleString()}
                      />
                      <Line
                        type="monotone"
                        dataKey="elo_rating"
                        stroke="#10b981"
                        strokeWidth={2}
                        dot={false}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="h-48 flex items-center justify-center text-zinc-500">
                  {t('leaderboard.notEnoughData')}
                </div>
              )}

              {/* Stats */}
              <div className="grid grid-cols-2 gap-4 mt-4">
                {leaderboard.find(e => e.checkpoint_id === selectedId) && (
                  <>
                    <div className="bg-zinc-800 rounded-lg p-3">
                      <div className="text-zinc-400 text-sm">{t('leaderboard.wins')}</div>
                      <div className="text-green-400 text-xl font-bold">
                        {leaderboard.find(e => e.checkpoint_id === selectedId)!.wins}
                      </div>
                    </div>
                    <div className="bg-zinc-800 rounded-lg p-3">
                      <div className="text-zinc-400 text-sm">{t('leaderboard.losses')}</div>
                      <div className="text-red-400 text-xl font-bold">
                        {leaderboard.find(e => e.checkpoint_id === selectedId)!.losses}
                      </div>
                    </div>
                    <div className="bg-zinc-800 rounded-lg p-3">
                      <div className="text-zinc-400 text-sm">{t('leaderboard.ties')}</div>
                      <div className="text-zinc-300 text-xl font-bold">
                        {leaderboard.find(e => e.checkpoint_id === selectedId)!.ties}
                      </div>
                    </div>
                    <div className="bg-zinc-800 rounded-lg p-3">
                      <div className="text-zinc-400 text-sm">{t('leaderboard.total')}</div>
                      <div className="text-white text-xl font-bold">
                        {leaderboard.find(e => e.checkpoint_id === selectedId)!.total_battles}
                      </div>
                    </div>
                  </>
                )}
              </div>
            </div>
          ) : (
            <div className="bg-zinc-900 rounded-lg p-8 flex flex-col items-center justify-center text-zinc-500">
              <Swords className="w-12 h-12 mb-4" />
              <p>{t('leaderboard.selectCheckpoint')}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
