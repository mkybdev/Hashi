import { useCallback, useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { analyzeText as apiAnalyzeText, fetchTargetWord } from './api';
import type { AnalyzeResponse } from './types';

function App() {
  const [targetWord, setTargetWord] = useState<string>('');
  const [targetAnalysis, setTargetAnalysis] = useState<AnalyzeResponse | null>(null);

  const [inputWord, setInputWord] = useState<string>('');
  const [inputAnalysis, setInputAnalysis] = useState<AnalyzeResponse | null>(null);

  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string>('');
  const [gameStatus, setGameStatus] = useState<'idle' | 'success' | 'failure'>('idle');

  const startNewGame = useCallback(async () => {
    setLoading(true);
    setGameStatus('idle');
    setMessage('');
    setInputWord('');
    setInputAnalysis(null);
    setTargetAnalysis(null);
    setTargetWord('');

    try {
      // Fetch target word from API
      // Default level: 2-8 morae
      const data = await fetchTargetWord(2, 8);
      setTargetWord(data.text);
      setTargetAnalysis(data);
    } catch (e) {
      console.error(e);
      setMessage('目標単語の読み込みに失敗しました。もう一度お試しください。');
    } finally {
      setLoading(false);
    }
  }, []);

  const handleGuess = async () => {
    if (!inputWord) return;
    if (loading) return;

    setLoading(true);
    setMessage('');

    try {
      const analysis = await apiAnalyzeText(inputWord);
      setInputAnalysis(analysis);

      // Compare accents
      // Check if patterns match exactly
      const targetPattern = targetAnalysis?.accent_pattern;
      const inputPattern = analysis.accent_pattern;

      if (!targetPattern || !inputPattern) {
        setMessage('アクセントの比較に失敗しました。');
        return;
      }

      if (JSON.stringify(targetPattern) === JSON.stringify(inputPattern)) {
        setGameStatus('success');
        setMessage('完璧！同じアクセントの言葉を見つけました！');
      } else {
        setGameStatus('failure');
        setMessage('惜しい！下のアクセントパターンを確認してください。');
      }
    } catch (_) {
      setMessage('入力の解析に失敗しました。');
    } finally {
      setLoading(false);
    }
  };

  // Visualization helper
  const renderAccent = (analysis: AnalyzeResponse) => {
    return (
      <div className="text-xl font-mono mt-2 p-2 border-2 border-slate-700 inline-block bg-slate-900 text-green-400">
        {analysis.accent_code}
        <div className="text-xs text-slate-500 mt-1">読み：{analysis.reading}</div>
        <div className="text-xs text-slate-500">
          パターン：{JSON.stringify(analysis.accent_pattern)}
        </div>
      </div>
    );
  };

  useEffect(() => {
    startNewGame();
  }, [startNewGame]);

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-4">
      <Card className="w-full max-w-md border-4 border-slate-800 rounded-none bg-slate-900 shadow-[8px_8px_0px_0px_rgba(30,41,59,1)]">
        <CardHeader>
          <CardTitle className="text-3xl text-center text-primary tracking-widest uppercase text-yellow-500 drop-shadow-md">
            アクセントマッチ
          </CardTitle>
          <CardDescription className="text-center font-mono text-slate-400">
            次の単語と同じアクセントの言葉を見つけよう：
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="text-center p-6 bg-slate-950 border-2 border-dashed border-slate-700">
            {loading && !targetWord ? (
              <span className="animate-pulse">読み込み中...</span>
            ) : (
              <h2 className="text-5xl font-bold text-white mb-2">{targetWord}</h2>
            )}

            {(gameStatus === 'success' || gameStatus === 'failure') && targetAnalysis && (
              <div className="mt-4">
                <div className="text-sm text-slate-400 mb-1">目標のアクセント：</div>
                {renderAccent(targetAnalysis)}
              </div>
            )}
          </div>

          <div className="space-y-4">
            <Input
              className="border-2 border-slate-700 bg-slate-950 text-white font-mono text-lg h-12 rounded-none focus:ring-0 focus:border-green-500"
              placeholder="日本語の単語を入力してください..."
              value={inputWord}
              onChange={(e) => setInputWord(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleGuess()}
              disabled={loading || gameStatus === 'success'}
            />

            <Button
              className="w-full h-12 text-lg font-bold uppercase tracking-wider rounded-none border-b-4 border-primary active:border-b-0 active:translate-y-1 transition-all"
              onClick={handleGuess}
              disabled={loading || !inputWord}
            >
              {loading ? '解析中...' : 'アクセントをチェック'}
            </Button>
          </div>

          {message && (
            <div
              className={`text-center font-bold p-2 ${gameStatus === 'success' ? 'text-green-500' : 'text-red-500'}`}
            >
              {message}
            </div>
          )}

          {inputAnalysis && (
            <div className="text-center mt-4 border-t-2 border-slate-800 pt-4">
              <div className="text-sm text-slate-400 mb-1">あなたの入力：</div>
              {renderAccent(inputAnalysis)}
            </div>
          )}

          {gameStatus !== 'idle' && (
            <Button
              variant="outline"
              className="w-full mt-4 border-2 rounded-none"
              onClick={startNewGame}
            >
              次の単語
            </Button>
          )}
        </CardContent>
      </Card>

      <footer className="mt-8 text-slate-600 font-mono text-xs">
        tdmelodic & Shadcn 8-bit を使用
      </footer>
    </div>
  );
}

export default App;
