import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Swords, Trophy, FolderOpen, Settings } from 'lucide-react';
import { LanguageSwitcher } from './LanguageSwitcher';
import { SettingsPanel } from './SettingsPanel';

const navItems = [
  { path: '/', labelKey: 'nav.arena', icon: Swords },
  { path: '/leaderboard', labelKey: 'nav.leaderboard', icon: Trophy },
  { path: '/checkpoints', labelKey: 'nav.checkpoints', icon: FolderOpen },
];

export function Navbar() {
  const location = useLocation();
  const { t } = useTranslation();
  const [settingsOpen, setSettingsOpen] = useState(false);

  return (
    <>
      <nav className="bg-zinc-950/50 backdrop-blur-md border-b border-zinc-800 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-2">
              <Swords className="w-8 h-8 text-emerald-500" />
              <span className="text-xl font-bold text-white">{t('common.appName')}</span>
            </div>

            <div className="flex items-center gap-1">
              {navItems.map(({ path, labelKey, icon: Icon }) => {
                const isActive = location.pathname === path;
                return (
                  <Link
                    key={path}
                    to={path}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                      isActive
                        ? 'bg-emerald-600 text-white'
                        : 'text-zinc-400 hover:text-white hover:bg-zinc-800'
                    }`}
                  >
                    <Icon className="w-4 h-4" />
                    <span>{t(labelKey)}</span>
                  </Link>
                );
              })}

              {/* Settings Button */}
              <button
                onClick={() => setSettingsOpen(true)}
                className="flex items-center gap-2 px-4 py-2 rounded-lg text-zinc-400 hover:text-white hover:bg-zinc-800 transition-colors"
              >
                <Settings className="w-4 h-4" />
                <span>{t('nav.settings')}</span>
              </button>

              <div className="ml-2 pl-2 border-l border-zinc-800">
                <LanguageSwitcher />
              </div>
            </div>
          </div>
        </div>
      </nav>

      <SettingsPanel isOpen={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </>
  );
}
