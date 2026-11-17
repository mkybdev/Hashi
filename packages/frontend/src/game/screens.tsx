import type { RefObject } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import type { useGame, Word } from './useGame';
export type Screen = 'home' | 'help' | 'settings' | 'play' | 'result' | 'ranking';
const levels = {
  easy: 'やさしい · 2〜3拍',
  normal: 'ふつう · 4〜5拍',
  hard: 'むずかしい · 6〜8拍',
};
function Accent({ word }: { word: Word }) {
  return (
    <div className="accent">
      <strong>{word.text}</strong>
      <span>
        {word.estimated
          ? '推定アクセント（tdmelodic）'
          : word.source === 'kanjium'
            ? 'Kanjium'
            : 'UniDic'}
      </span>
      <span>
        {word.reading} · {word.mora_count}拍
      </span>
      <span>
        高低：
        {word.pitch_patterns
          .map((pattern) => pattern.map((level) => (level === 2 ? '高' : '低')).join('・'))
          .join(' / ')}
      </span>
    </div>
  );
}

type ScreenProps = {
  game: ReturnType<typeof useGame>;
  setScreen: (screen: Screen) => void;
  start: () => Promise<void>;
  next: () => Promise<void>;
  leave: (screen: Screen) => void;
  correct: number;
  input: string;
  setInput: (input: string) => void;
  field: RefObject<HTMLInputElement | null>;
  composing: RefObject<boolean>;
};
export function HomeScreen({ setScreen }: Pick<ScreenProps, 'setScreen'>) {
  return (
    <section className="menu">
      <p>
        同じアクセントの、ちがうことば。
        <br />
        あなたはいくつ見つけられる？
      </p>
      <Button onClick={() => setScreen('settings')}>ゲーム開始</Button>
      <Button variant="outline" onClick={() => setScreen('help')}>
        遊び方
      </Button>
      <Button variant="outline" onClick={() => setScreen('ranking')}>
        ハイスコア一覧
      </Button>
    </section>
  );
}
export function HelpScreen({ setScreen }: Pick<ScreenProps, 'setScreen'>) {
  return (
    <section>
      <h2>遊び方</h2>
      <ol>
        <li>お題と同じ拍数・音の高低の並びの単語を考えます。</li>
        <li>漢字・ひらがな・カタカナで入力します。</li>
        <li>正解したら次のお題へ。時間制限はありません。</li>
      </ol>
      <p>
        「優位」と「周囲」はどちらも3拍・1型です。「橋」と「箸」は単語内の高低が似ていても、最後の音の後で下がるかどうかが異なります。
      </p>
      <p>
        お題そのもの・表記違い・直近30回の正解は使えません。回答は幅広く受け付け、お題はKanjiumの収録語のうち、使用頻度が高い語を中心に出題します。同音語を許可する場合は、漢字などで語を特定してください。
      </p>
      <Button onClick={() => setScreen('settings')}>やってみる</Button>
    </section>
  );
}
export function SettingsScreen({ game, start }: Pick<ScreenProps, 'game' | 'start'>) {
  return (
    <section className="menu">
      <h2>ゲーム設定</h2>
      <p className="badge">エンドレス · 時間制限なし</p>
      <label htmlFor="difficulty">難易度</label>
      <select
        id="difficulty"
        value={game.settings.difficulty}
        onChange={(e) =>
          game.setSettings({
            ...game.settings,
            difficulty: e.target.value as keyof typeof levels,
          })
        }
      >
        {Object.entries(levels).map(([value, label]) => (
          <option key={value} value={value}>
            {label}
          </option>
        ))}
      </select>
      <label className="check">
        <input
          type="checkbox"
          checked={game.settings.homophones}
          onChange={(e) => game.setSettings({ ...game.settings, homophones: e.target.checked })}
        />
        同音異義語を正解に含める
      </label>
      <Button disabled={game.loading} onClick={start}>
        スタート
      </Button>
    </section>
  );
}
export function PlayScreen({
  game,
  next,
  leave,
  correct,
  input,
  setInput,
  field,
  composing,
}: Pick<
  ScreenProps,
  'game' | 'next' | 'leave' | 'correct' | 'input' | 'setInput' | 'field' | 'composing'
>) {
  return (
    <section className="menu">
      <div className="stats">
        <span>ENDLESS</span>
        <span>{correct} 正解</span>
      </div>
      <p>{levels[game.settings.difficulty]}</p>
      <div className="target">
        <span>お題</span>
        <h2>{game.target?.text || 'お題を準備中'}</h2>
        {game.target && (
          <span>
            {game.target.reading} · {game.target.mora_count}拍
          </span>
        )}
      </div>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (!composing.current) void game.guess(input);
        }}
      >
        <label htmlFor="answer">同じアクセントのことば</label>
        <Input
          ref={field}
          id="answer"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onCompositionStart={() => {
            composing.current = true;
          }}
          onCompositionEnd={() => {
            composing.current = false;
          }}
          onKeyDown={(e) => {
            if (
              e.key === 'Enter' &&
              (e.nativeEvent.isComposing || composing.current || e.keyCode === 229)
            )
              e.preventDefault();
          }}
          disabled={game.loading || game.feedback?.correct || !game.target}
          autoComplete="off"
          placeholder="例：周囲 / しゅうい"
        />
        <Button
          disabled={game.loading || !input.trim() || game.feedback?.correct || !game.target}
          type="submit"
        >
          {game.loading ? '確認中…' : '回答する'}
        </Button>
      </form>
      {game.feedback && (
        <div aria-live="polite">
          <p className={game.feedback.correct ? 'success' : 'failure'}>{game.feedback.message}</p>
          <Accent word={game.feedback.target} />
          {game.feedback.answer && <Accent word={game.feedback.answer} />}
        </div>
      )}
      <Button variant="outline" disabled={game.loading} onClick={next}>
        {game.feedback?.correct ? '次のお題へ' : 'スキップ'}
      </Button>
      <button className="text-button" type="button" onClick={() => leave('result')}>
        ここまでの結果を見る
      </button>
    </section>
  );
}
export function ResultScreen({
  game,
  setScreen,
  start,
  correct,
}: Pick<ScreenProps, 'game' | 'setScreen' | 'start' | 'correct'>) {
  return (
    <section className="menu">
      <h2>おつかれさま！</h2>
      <p className="score">
        {correct}
        <small> 正解</small>
      </p>
      <p>
        {game.history.length}回の回答 · {levels[game.settings.difficulty]}
      </p>
      <ul className="history">
        {game.history.map((r, i) => (
          <li key={`${i}-${r.target.id}`}>
            {r.correct ? '○' : '×'} {r.target.text} → {r.answer?.text || '使用不可'}
          </li>
        ))}
      </ul>
      <Button disabled={game.loading} onClick={start}>
        もう一度遊ぶ
      </Button>
      <Button variant="outline" onClick={() => setScreen('settings')}>
        設定を変える
      </Button>
    </section>
  );
}
export function RankingScreen({ setScreen }: Pick<ScreenProps, 'setScreen'>) {
  return (
    <section>
      <h2>ハイスコア一覧</h2>
      <p>
        共有ランキングは準備中です。現在のエンドレスモードは練習用で、ランキングには登録されません。
      </p>
      <Button onClick={() => setScreen('settings')}>練習をはじめる</Button>
    </section>
  );
}
