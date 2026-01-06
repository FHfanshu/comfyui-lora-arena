import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Navbar } from './components/common/Navbar';
import { ArenaPage } from './pages/ArenaPage';
import { LeaderboardPage } from './pages/LeaderboardPage';
import { CheckpointsPage } from './pages/CheckpointsPage';
import { BattleProvider } from './contexts/BattleContext';

function App() {
  return (
    <BrowserRouter>
      <BattleProvider>
        <div className="min-h-screen bg-zinc-950">
          <Navbar />
          <main>
            <Routes>
              <Route path="/" element={<ArenaPage />} />
              <Route path="/leaderboard" element={<LeaderboardPage />} />
              <Route path="/checkpoints" element={<CheckpointsPage />} />
            </Routes>
          </main>
        </div>
      </BattleProvider>
    </BrowserRouter>
  );
}

export default App;
