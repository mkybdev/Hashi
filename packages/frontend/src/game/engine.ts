export type Mode = 'endless' | 'marathon' | 'timeAttack';
export type Settings = {
  difficulty: 'easy' | 'normal' | 'hard';
  homophones: boolean;
  mode: Mode;
  timeLimit: number;
  targetCount: number;
};
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
export type State = {
  settings: Settings;
  target: Word | null;
  feedback: Feedback | null;
  history: Feedback[];
  loading: boolean;
  error: string;
  elapsed: number;
  finished: 'timeout' | 'completed' | 'stopped' | null;
};
export type Request = <T>(path: string, body: unknown, signal: AbortSignal) => Promise<T>;
export const defaults: Settings = {
  difficulty: 'easy',
  homophones: false,
  mode: 'endless',
  timeLimit: 60,
  targetCount: 10,
};

export class GameEngine {
  private listeners = new Set<() => void>();
  private generation = 0;
  private controller: AbortController | null = null;
  private started: number | null = null;
  private accumulated = 0;
  private state: State = {
    settings: defaults,
    target: null,
    feedback: null,
    history: [],
    loading: false,
    error: '',
    elapsed: 0,
    finished: null,
  };
  private request: Request;
  private now: () => number;
  constructor(request: Request, now = () => performance.now()) {
    this.request = request;
    this.now = now;
  }
  getSnapshot = () => this.state;
  subscribe = (listener: () => void) => {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  };
  private update(patch: Partial<State>) {
    this.state = { ...this.state, ...patch };
    for (const listener of this.listeners) listener();
  }
  private elapsed() {
    return this.accumulated + (this.started === null ? 0 : this.now() - this.started);
  }
  private pause() {
    this.accumulated = this.elapsed();
    this.started = null;
    this.update({ elapsed: this.accumulated });
  }
  private resume() {
    if (!this.state.finished && this.started === null) this.started = this.now();
  }
  private expired() {
    return (
      this.state.settings.mode === 'marathon' &&
      this.elapsed() >= this.state.settings.timeLimit * 1000
    );
  }
  tick = () => {
    if (this.started === null || this.state.finished) return;
    if (this.expired()) {
      this.pause();
      this.update({ elapsed: this.state.settings.timeLimit * 1000, finished: 'timeout' });
    } else this.update({ elapsed: this.elapsed() });
  };
  stop = () => {
    this.pause();
    this.generation++;
    this.controller?.abort();
    this.update({ loading: false, finished: this.state.finished || 'stopped' });
  };
  private recent() {
    const words = this.state.history.flatMap((r) => (r.correct && r.answer ? [r.answer.key] : []));
    return this.state.settings.mode === 'endless' ? words.slice(-30) : words;
  }
  start = async (settings: Settings) => {
    this.generation++;
    this.controller?.abort();
    this.started = null;
    this.accumulated = 0;
    this.update({
      settings: { ...settings },
      loading: false,
      target: null,
      feedback: null,
      history: [],
      error: '',
      elapsed: 0,
      finished: null,
    });
    await this.load();
  };
  load = async () => {
    if (this.state.loading || this.state.finished) return;
    if (this.expired()) {
      this.tick();
      return;
    }
    this.pause();
    const oldTarget = this.state.target;
    const recent = [...this.recent(), ...(oldTarget ? [oldTarget.key] : [])];
    const token = ++this.generation;
    this.controller = new AbortController();
    this.update({ loading: true, error: '', target: null, feedback: null });
    try {
      const target = await this.request<Word>(
        'target',
        { ...this.state.settings, recent },
        this.controller.signal,
      );
      if (token !== this.generation) return;
      this.update({ target, loading: false });
      this.resume();
    } catch (error) {
      if (token === this.generation)
        this.update({ loading: false, error: (error as Error).message });
    }
  };
  guess = async (text: string) => {
    if (
      this.state.loading ||
      this.state.finished ||
      !this.state.target ||
      this.state.feedback?.correct ||
      !text.trim()
    )
      return;
    // 描画更新の間隔に依存せず、送信した瞬間で期限を判断する。
    if (this.expired()) {
      this.tick();
      return;
    }
    this.pause();
    const token = ++this.generation;
    this.controller = new AbortController();
    this.update({ loading: true, error: '' });
    try {
      const result = await this.request<Feedback>(
        'guess',
        { ...this.state.settings, recent: this.recent(), target_id: this.state.target.id, text },
        this.controller.signal,
      );
      if (token !== this.generation) return;
      const history = [...this.state.history, result];
      const completed =
        this.state.settings.mode === 'timeAttack' &&
        history.filter((r) => r.correct).length >= this.state.settings.targetCount;
      this.update({
        feedback: result,
        history,
        loading: false,
        finished: completed ? 'completed' : null,
      });
      if (!result.correct) this.resume();
    } catch (error) {
      if (token === this.generation) {
        this.update({ loading: false, error: (error as Error).message });
        this.resume();
      }
    }
  };
}
