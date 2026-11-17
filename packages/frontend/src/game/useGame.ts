import { useRef, useState } from 'react';
export type Settings = { difficulty: 'easy' | 'normal' | 'hard'; homophones: boolean };
export type Word = {
  id: number;
  text: string;
  reading: string;
  key: string;
  accents: number[];
  pitch_patterns: number[][];
  accent_pattern: number[];
  source: string;
  estimated: boolean;
  mora_count: number;
};
export type Feedback = { correct: boolean; message: string; answer: Word | null; target: Word };
const base = import.meta.env.VITE_API_URL || '/api';
async function request<T>(path: string, body: unknown, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${base}/game/${path}`, {
    signal,
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
  const [settings, setSettings] = useState<Settings>({ difficulty: 'easy', homophones: false });
  const [target, setTarget] = useState<Word | null>(null);
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  const [history, setHistory] = useState<Feedback[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const busy = useRef(false);
  const generation = useRef(0);
  const controller = useRef<AbortController | null>(null);
  const recent = history.flatMap((r) => (r.correct && r.answer ? [r.answer.key] : [])).slice(-30);
  async function load(reset = false) {
    if (busy.current) return;
    busy.current = true;
    setLoading(true);
    setError('');
    const token = ++generation.current;
    controller.current = new AbortController();
    if (reset) {
      setTarget(null);
      setFeedback(null);
      setHistory([]);
    }
    try {
      const word = await request<Word>(
        'target',
        {
          ...settings,
          recent: reset ? [] : [...recent, ...(target ? [target.key] : [])],
        },
        controller.current?.signal,
      );
      if (token !== generation.current) return;
      setTarget(word);
      setFeedback(null);
      if (reset) setHistory([]);
    } catch (e) {
      if (token === generation.current) setError((e as Error).message);
    } finally {
      if (token === generation.current) {
        busy.current = false;
        setLoading(false);
      }
    }
  }
  async function guess(text: string) {
    if (busy.current || !target || feedback?.correct || !text.trim()) return;
    busy.current = true;
    setLoading(true);
    setError('');
    const token = generation.current;
    controller.current = new AbortController();
    try {
      const result = await request<Feedback>(
        'guess',
        {
          ...settings,
          recent,
          target_id: target.id,
          text,
        },
        controller.current?.signal,
      );
      if (token !== generation.current) return;
      setFeedback(result);
      setHistory((items) => [...items, result]);
    } catch (e) {
      if (token === generation.current) setError((e as Error).message);
    } finally {
      if (token === generation.current) {
        busy.current = false;
        setLoading(false);
      }
    }
  }
  function cancel() {
    generation.current++;
    controller.current?.abort();
    busy.current = false;
    setLoading(false);
  }
  return { settings, setSettings, target, feedback, history, loading, error, load, guess, cancel };
}
