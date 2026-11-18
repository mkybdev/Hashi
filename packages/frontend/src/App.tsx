import { useEffect, useRef, useState } from 'react';
import { Button } from '@/components/ui/button';
import {
  HelpScreen,
  HomeScreen,
  PlayScreen,
  RankingScreen,
  ResultScreen,
  type Screen,
  SettingsScreen,
} from './game/screens';
import { useGame } from './game/useGame';
import './App.css';

function App() {
  const [screen, setScreen] = useState<Screen>('home');
  const [input, setInput] = useState('');
  const game = useGame();
  const field = useRef<HTMLInputElement>(null);
  const composing = useRef(false);
  useEffect(() => {
    if (screen === 'play' && !game.loading) field.current?.focus();
  }, [screen, game.loading]);
  useEffect(() => {
    if (screen === 'play' && (game.finished === 'timeout' || game.finished === 'stopped')) {
      setScreen('result');
    }
  }, [screen, game.finished]);
  const correct = game.history.filter((r) => r.correct).length;
  function leave(next: Screen) {
    game.cancel();
    setScreen(next);
  }
  async function start() {
    setInput('');
    setScreen('play');
    await game.load(true);
  }
  async function next() {
    setInput('');
    await game.load();
  }
  return (
    <main className="shell">
      <div className="frame">
        <header>
          <span className="eyebrow">ことばでつなぐ、音のかたち</span>
          <h1>
            Hashi<span>はし</span>
          </h1>
        </header>
        {screen === 'home' && <HomeScreen setScreen={setScreen} />}
        {screen === 'help' && <HelpScreen setScreen={setScreen} />}
        {screen === 'settings' && <SettingsScreen game={game} start={start} />}
        {screen === 'play' && (
          <PlayScreen
            game={game}
            next={next}
            leave={leave}
            correct={correct}
            input={input}
            setInput={setInput}
            field={field}
            composing={composing}
          />
        )}
        {screen === 'result' && (
          <ResultScreen game={game} setScreen={setScreen} start={start} correct={correct} />
        )}
        {screen === 'ranking' && <RankingScreen setScreen={setScreen} />}
        {game.error && screen === 'play' && (
          <div role="alert">
            <p className="failure">{game.error}</p>
            <Button variant="outline" disabled={game.loading} onClick={next}>
              お題を再取得
            </Button>
          </div>
        )}
        {screen !== 'home' && (
          <button type="button" className="text-button back" onClick={() => leave('home')}>
            タイトルへ戻る
          </button>
        )}
        <footer>
          同じリズムで、ことばの橋を。
          <br />
          <a href="https://github.com/mifunetoshiro/kanjium" target="_blank" rel="noreferrer">
            アクセントデータ: Kanjium / Uros O.（CC BY-SA 4.0）
          </a>
        </footer>
      </div>
    </main>
  );
}
export default App;
