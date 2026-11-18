import type { RefObject } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import type { useGame, Word } from './useGame';
export type Screen = 'home' | 'help' | 'settings' | 'play' | 'result' | 'ranking';
export const modes = {
  endless: 'エンドレス',
  marathon: 'マラソン',
  timeAttack: 'タイムアタック',
};
const seconds = (ms: number) => (ms / 1000).toFixed(1);
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
        {false &&
          (word.estimated
            ? '推定アクセント（tdmelodic）'
            : word.source === 'kanjium'
              ? 'Kanjium'
              : 'UniDic')}
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
    <section className="menu" style={{ gap: '20px', textAlign: 'center' }}>
      <p>
        同じアクセントの、ちがうことば。
        <br />
        あなたはいくつ見つけられる？
      </p>
      <Button onClick={() => setScreen('settings')}>ゲーム開始</Button>
      <Button onClick={() => setScreen('help')}>遊び方</Button>
      <Button onClick={() => setScreen('ranking')}>ハイスコア一覧</Button>
    </section>
  );
}
export function HelpScreen() {
  return (
    <section>
      <h2>遊び方</h2>
      <ol>
        <li>お題と同じ拍数・音の高低の並びの単語を考えます。</li>
        <li>漢字・ひらがな・カタカナで入力します。</li>
        <li>
          正解したら次のお題へ。マラソンは時間内の正解数、タイムアタックは指定数を正解するまでの時間を競います。
        </li>
      </ol>
      <p>
        お題そのもの・表記違い・直近30回の正解は使えません。同音異義語を許可する場合は、漢字などで語を特定してください。
      </p>
    </section>
  );
}
export function SettingsScreen({ game, start }: Pick<ScreenProps, 'game' | 'start'>) {
  return (
    <section className="menu">
      <h2>ゲーム設定</h2>
      <label htmlFor="mode">ゲームモード</label>
      <select
        id="mode"
        value={game.settings.mode}
        onChange={(e) =>
          game.setSettings({
            ...game.settings,
            mode: e.target.value as keyof typeof modes,
          })
        }
      >
        {Object.entries(modes).map(([value, label]) => (
          <option key={value} value={value}>
            {label}
          </option>
        ))}
      </select>
      {game.settings.mode === 'marathon' && (
        <>
          <label htmlFor="time-limit">制限時間</label>
          <select
            id="time-limit"
            value={game.settings.timeLimit}
            onChange={(e) =>
              game.setSettings({
                ...game.settings,
                timeLimit: Number(e.target.value),
              })
            }
          >
            {[30, 60, 120].map((value) => (
              <option key={value} value={value}>
                {value}秒
              </option>
            ))}
          </select>
        </>
      )}
      {game.settings.mode === 'timeAttack' && (
        <>
          <label htmlFor="target-count">目標正解数</label>
          <select
            id="target-count"
            value={game.settings.targetCount}
            onChange={(e) =>
              game.setSettings({
                ...game.settings,
                targetCount: Number(e.target.value),
              })
            }
          >
            {[5, 10, 20].map((value) => (
              <option key={value} value={value}>
                {value}問
              </option>
            ))}
          </select>
        </>
      )}
      <p>不正解時は同じお題に再挑戦できます。スキップは正解数に含めません。</p>
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
      <Button style={{ marginTop: '12px' }} disabled={game.loading} onClick={start}>
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
      <div>
        <div className="stats">
          <span>{modes[game.settings.mode]}</span>
          <span>
            {'正解数: '}
            {correct}
            {game.settings.mode === 'timeAttack' ? ` / ${game.settings.targetCount}` : ''}
          </span>
        </div>
        <p>{levels[game.settings.difficulty]}</p>
      </div>
      {game.settings.mode !== 'endless' && (
        <div
          className="timer"
          role="timer"
          aria-label={game.settings.mode === 'marathon' ? '残り時間' : '経過時間'}
        >
          {game.settings.mode === 'marathon'
            ? `残り ${Math.max(0, Math.ceil(game.settings.timeLimit - game.elapsed / 1000))} 秒`
            : `${seconds(game.elapsed)} 秒`}
        </div>
      )}
      <div className="target">
        <h2>{game.target?.text || 'お題を準備中'}</h2>
        {game.target && (
          <span>
            {game.target.reading}
            {false && ` · ${game.target?.mora_count}拍`}
          </span>
        )}
      </div>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (!composing.current) void game.guess(input);
        }}
      >
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
          disabled={game.loading || !!game.finished || game.feedback?.correct || !game.target}
          autoComplete="off"
          placeholder="回答を入力"
        />
        <div style={{ display: 'flex', gap: '8px' }}>
          <Button
            disabled={game.loading || !input.trim() || game.feedback?.correct || !game.target}
            type="submit"
          >
            {game.loading ? '確認中…' : '回答する'}
          </Button>
          {game.finished === 'completed' ? (
            <Button type="button" variant="secondary" onClick={() => leave('result')}>
              結果を見る
            </Button>
          ) : (
            <Button type="button" variant="secondary" disabled={game.loading} onClick={next}>
              {game.feedback?.correct ? '次のお題へ' : 'スキップ'}
            </Button>
          )}
        </div>
        {game.feedback && (
          <div aria-live="polite">
            <p className={game.feedback.correct ? 'success' : 'failure'}>{game.feedback.message}</p>
            <Accent word={game.feedback.target} />
            {game.feedback.answer && <Accent word={game.feedback.answer} />}
          </div>
        )}
        {game.finished !== 'completed' && (
          <Button
            type="button"
            variant={'secondary'}
            style={{ marginTop: '8px' }}
            onClick={() => leave('result')}
          >
            リタイアして結果を見る
          </Button>
        )}
      </form>
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
      <h2>
        {game.finished === 'completed'
          ? '目標達成！'
          : game.finished === 'timeout'
            ? 'タイムアップ！'
            : 'おつかれさま！'}
      </h2>
      <p>
        {modes[game.settings.mode]}
        {game.finished === 'stopped' && game.settings.mode !== 'endless' ? ' · 途中終了' : ''}
      </p>
      {game.settings.mode !== 'endless' && (
        <p>
          {game.settings.mode === 'marathon'
            ? `制限時間 ${game.settings.timeLimit}秒`
            : `目標 ${game.settings.targetCount}問`}{' '}
          · 所要時間 {seconds(game.elapsed)}秒
        </p>
      )}
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
      <div style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
        <Button disabled={game.loading} onClick={start}>
          もう一度遊ぶ
        </Button>
        <Button variant="secondary" onClick={() => setScreen('settings')}>
          設定を変える
        </Button>
      </div>
    </section>
  );
}
export function RankingScreen() {
  return (
    <section>
      <h2>ハイスコア一覧</h2>
      <p>
        ランキングは準備中です。
        <br />
        現在のプレイ結果はランキングに登録されません。
      </p>
    </section>
  );
}
