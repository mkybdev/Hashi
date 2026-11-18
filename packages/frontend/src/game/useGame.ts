import { useEffect, useState, useSyncExternalStore } from 'react';
import { defaults, GameEngine, type Settings } from './engine';

export type { Feedback, Settings, Word } from './engine';

const base = import.meta.env.VITE_API_URL || '/api';
async function request<T>(path: string, body: unknown, signal: AbortSignal): Promise<T> {
  const response = await fetch(`${base}/game/${path}`, {
    signal: AbortSignal.any([signal, AbortSignal.timeout(15000)]),
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const raw = await response.text();
  let data: unknown;
  try {
    data = JSON.parse(raw);
  } catch {
    throw new Error('解析サーバーでエラーが発生しました。もう一度お試しください。');
  }
  if (!response.ok)
    throw new Error(
      typeof data === 'object' &&
        data !== null &&
        'detail' in data &&
        typeof data.detail === 'string'
        ? data.detail
        : '通信に失敗しました。再度お試しください。',
    );
  return data as T;
}
export function useGame() {
  const [settings, setSettings] = useState<Settings>(defaults);
  const [engine] = useState(() => new GameEngine(request));
  const state = useSyncExternalStore(engine.subscribe, engine.getSnapshot);
  useEffect(() => {
    const interval = setInterval(engine.tick, 50);
    return () => {
      clearInterval(interval);
      engine.stop();
    };
  }, [engine]);
  return {
    ...state,
    settings,
    setSettings,
    load: (reset = false) => (reset ? engine.start(settings) : engine.load()),
    guess: engine.guess,
    cancel: engine.stop,
  };
}
