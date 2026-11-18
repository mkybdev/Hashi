import { describe, expect, test } from 'bun:test';
import { GameEngine, defaults, type Request, type Word, type Feedback, type Settings } from '../src/game/engine';
const word: Word = { id: 1, text: '優位', reading: 'ユウイ', key: '優位:ユウイ', accents: [1], pitch_patterns: [[2,1,1]], accent_pattern: [2,1,1], source: 'kanjium', estimated: false, mora_count: 3 };
const feedback = (correct: boolean): Feedback => ({ correct, message: '', target: word, answer: {...word, id: 2, key: '周囲:シュウイ'} });
function harness() {
  let now = 0;
  const calls: { path: string; body: unknown; signal: AbortSignal; resolve: (v: unknown) => void; reject: (e: Error) => void }[] = [];
  const request: Request = <T>(path: string, body: unknown, signal: AbortSignal) => new Promise<T>((resolve, reject) => { calls.push({ path, body, signal, resolve: (v) => resolve(v as T), reject }); });
  const engine = new GameEngine(request, () => now);
  const advance = (ms: number) => { now += ms; engine.tick(); };
  const start = async (options: Partial<Settings> = {}) => { const task = engine.start({ ...defaults, mode: 'marathon', ...options }); calls.at(-1)!.resolve(word); await task; };
  return { engine, calls, advance, start, elapse: (ms: number) => { now += ms; } };
}
describe('入力可能時間だけを計るゲーム進行', () => {
  test('初回のお題取得とスキップ待ちを計時しない', async () => {
    const h = harness(); const task = h.engine.start({...defaults, mode:'marathon'});
    h.advance(100000); expect(h.engine.getSnapshot().elapsed).toBe(0);
    h.calls[0].resolve(word); await task; h.advance(1000);
    const skip = h.engine.load(); h.advance(50000); expect(h.engine.getSnapshot().elapsed).toBe(1000);
    h.calls[1].resolve(word); await skip; h.advance(500); expect(h.engine.getSnapshot().elapsed).toBe(1500);
  });
  test('期限直前の送信は応答が遅れても採点し、連打しない', async () => {
    const h = harness(); await h.start(); h.advance(59999);
    const task = h.engine.guess('周囲'); await h.engine.guess('周囲'); expect(h.calls.length).toBe(2);
    h.advance(90000); h.calls[1].resolve(feedback(true)); await task;
    expect(h.engine.getSnapshot().history.length).toBe(1); expect(h.engine.getSnapshot().finished).toBeNull();
    h.advance(10000); expect(h.engine.getSnapshot().elapsed).toBe(59999);
    const next = h.engine.load(); h.calls[2].resolve(word); await next; h.advance(1);
    expect(h.engine.getSnapshot().finished).toBe('timeout');
  });
  test('時計の描画前でも期限後の回答を送らない', async () => {
    const h = harness(); await h.start({timeLimit:1}); h.elapse(1000);
    await h.engine.guess('周囲'); expect(h.calls.length).toBe(1); expect(h.engine.getSnapshot().finished).toBe('timeout');
  });
  test('不正解後は同じお題で計時再開', async () => {
    const h = harness(); await h.start(); h.advance(100);
    const task = h.engine.guess('違う'); h.advance(30000); h.calls[1].resolve(feedback(false)); await task;
    h.advance(500); expect(h.engine.getSnapshot().elapsed).toBe(600); expect(h.engine.getSnapshot().target?.id).toBe(1);
  });
  test('通信失敗では回答を加算せず再送できる', async () => {
    const h = harness(); await h.start(); h.advance(100);
    const task = h.engine.guess('周囲'); h.advance(30000); h.calls[1].reject(new Error('通信失敗')); await task;
    expect(h.engine.getSnapshot().history.length).toBe(0); h.advance(100); expect(h.engine.getSnapshot().elapsed).toBe(200);
    const retry = h.engine.guess('周囲'); h.calls[2].resolve(feedback(true)); await retry; expect(h.engine.getSnapshot().history.length).toBe(1);
  });
  test('初回の取得失敗から復帰でき、待ち時間は含めない', async () => {
    const h = harness(); const task = h.engine.start(defaults); h.calls[0].reject(new Error('取得失敗')); await task;
    h.advance(10000); expect(h.engine.getSnapshot().elapsed).toBe(0);
    const retry = h.engine.load(); h.calls[1].resolve(word); await retry; expect(h.engine.getSnapshot().target).toEqual(word);
  });
  test('終了後や再挑戦中に古い応答を反映しない', async () => {
    const h = harness(); await h.start(); const old = h.engine.guess('周囲'); h.engine.stop();
    expect(h.calls[1].signal.aborted).toBe(true); await h.start(); h.calls[1].resolve(feedback(true)); await old;
    expect(h.engine.getSnapshot().history).toEqual([]); expect(h.engine.getSnapshot().loading).toBe(false);
  });
  test('タイムアタックは指定正解数で終了し、その後の回答を無視する', async () => {
    const h = harness(); await h.start({mode:'timeAttack',targetCount:1}); h.advance(1234);
    const task = h.engine.guess('周囲'); h.advance(9999); h.calls[1].resolve(feedback(true)); await task;
    expect(h.engine.getSnapshot().finished).toBe('completed'); expect(h.engine.getSnapshot().elapsed).toBe(1234);
    await h.engine.guess('別の語'); expect(h.calls.length).toBe(2);
  });
  test('読込中に再開始しても新しいお題を読み込み、古い応答を無視する', async () => {
    const h = harness(); const old = h.engine.start(defaults);
    const fresh = h.engine.start({...defaults, mode:'timeAttack'});
    expect(h.calls.length).toBe(2); expect(h.calls[0].signal.aborted).toBe(true);
    h.calls[1].resolve({...word,id:99}); await fresh;
    h.calls[0].resolve(word); await old;
    expect(h.engine.getSnapshot().target?.id).toBe(99);
    expect(h.engine.getSnapshot().loading).toBe(false);
  });
  test('タイムアタックの途中の不正解と正解後待機を扱う', async () => {
    const h = harness(); await h.start({mode:'timeAttack',targetCount:2}); h.advance(100);
    const wrong = h.engine.guess('別の語'); h.calls.at(-1)!.resolve(feedback(false)); await wrong;
    expect(h.engine.getSnapshot().finished).toBeNull(); h.advance(200);
    const first = h.engine.guess('周囲'); h.calls.at(-1)!.resolve(feedback(true)); await first;
    h.advance(5000); expect(h.engine.getSnapshot().elapsed).toBe(300);
    expect(h.engine.getSnapshot().finished).toBeNull();
    const next = h.engine.load(); h.calls.at(-1)!.resolve({...word,id:2}); await next;
    h.advance(400); const second = h.engine.guess('別の正解'); h.calls.at(-1)!.resolve(feedback(true)); await second;
    expect(h.engine.getSnapshot().finished).toBe('completed'); expect(h.engine.getSnapshot().elapsed).toBe(700);
    expect(h.engine.getSnapshot().history.filter(r => r.correct).length).toBe(2);
  });
  test('最後の回答の詳細を保持し、結果の確認中も計時しない', async () => {
    const h = harness(); await h.start({mode:'timeAttack',targetCount:1}); h.advance(500);
    const task = h.engine.guess('周囲'); h.calls.at(-1)!.resolve(feedback(true)); await task;
    expect(h.engine.getSnapshot().feedback?.answer?.key).toBe('周囲:シュウイ');
    h.advance(10000); await h.engine.load();
    expect(h.calls.length).toBe(2);
    expect(h.engine.getSnapshot().elapsed).toBe(500);
    h.engine.stop();
    expect(h.engine.getSnapshot().finished).toBe('completed');
    expect(h.engine.getSnapshot().elapsed).toBe(500);
  });
  test('エンドレスには時間切れがない', async () => {
    const h = harness(); await h.start({mode:'endless'}); h.advance(1e7); expect(h.engine.getSnapshot().finished).toBeNull();
  });
});
