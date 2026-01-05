import { useState, useEffect } from 'react'
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { fetchTargetWord, analyzeText as apiAnalyzeText } from './api'
import type { AnalyzeResponse } from './types'

function App() {
  const [targetWord, setTargetWord] = useState<string>("")
  const [targetAnalysis, setTargetAnalysis] = useState<AnalyzeResponse | null>(null)
  
  const [inputWord, setInputWord] = useState<string>("")
  const [inputAnalysis, setInputAnalysis] = useState<AnalyzeResponse | null>(null)
  
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState<string>("")
  const [gameStatus, setGameStatus] = useState<'idle' | 'success' | 'failure'>('idle')

  useEffect(() => {
    startNewGame()
  }, [])

  const startNewGame = async () => {
    setLoading(true)
    setGameStatus('idle')
    setMessage("")
    setInputWord("")
    setInputAnalysis(null)
    setTargetAnalysis(null)
    setTargetWord("")
    
    try {
      // Fetch target word from API
      // Default level: 2-8 morae
      const data = await fetchTargetWord(2, 8)
      setTargetWord(data.text)
      setTargetAnalysis(data)
    } catch (e) {
      console.error(e)
      setMessage("Error loading target word. Please try again.")
    } finally {
      setLoading(false)
    }
  }

  const handleGuess = async () => {
    if (!inputWord) return
    if (loading) return
    
    setLoading(true)
    setMessage("")
    
    try {
      const analysis = await apiAnalyzeText(inputWord)
      setInputAnalysis(analysis)
      
      // Compare accents
      // Check if patterns match exactly
      const targetPattern = targetAnalysis?.accent_pattern
      const inputPattern = analysis.accent_pattern
      
      if (!targetPattern || !inputPattern) {
        setMessage("Error comparing accents.")
        return
      }
      
      // Comparison logic: 
      // Strictly speaking, we should compare the pattern shape, not absolute length?
      // Or if the game is "Same accent class"?
      // "Same accent" usually means same pattern type (Heiban vs Atamadaka etc)
      // But tdmelodic returns raw pitch levels per mora (or transition).
      // Let's compare raw array for exact match first.
      
      // However, different words likely have different lengths.
      // E.g. "Hashi" (2 morae) vs "Sora" (2 morae) -> Can compare.
      // "Hashi" (2) vs "Sakana" (3).
      // If user inputs a word of DIFFERENT length, is it allowed?
      // "Think of a word with the SAME accent".
      // Usually implies same accent *type*?
      // Atamadaka: H L L...
      // Heiban: L H H...
      // Odaka: L H H... (Drop at particle) -> Wait, Heiban vs Odaka is hard to distinguish without particle.
      // Nakadaka: L H... L...
      
      // tdmelodic output `[2, 1]` for Hashi.
      // `[2, 1, 1]` for something else?
      
      // Simplest game: Match the PATTERN SHAPE.
      // We can normalize pattern?
      // Or just require same length for simplicity now?
      // Or check if abstract pattern matches?
      
      // Let's implement EXACT MATCH of the array sequence for now.
      // This implicitly requires same length and same pitch movement.
      
      if (JSON.stringify(targetPattern) === JSON.stringify(inputPattern)) {
        setGameStatus('success')
        setMessage("Perfect Match! You found a word with the exact same accent!")
      } else {
        setGameStatus('failure')
        setMessage("Not quite. Check the accent pattern below.")
      }
      
    } catch (e) {
      setMessage("Failed to analyze input.")
    } finally {
      setLoading(false)
    }
  }

  // Visualization helper
  const renderAccent = (analysis: AnalyzeResponse) => {
    // Array of levels: 0, 1, 2?
    // 2=High/Up, 1=Low/Down, 0=Keep?
    // Let's verify mapping again from my investigation.
    // [2, 1] for H-L.
    // Ideally we visualize pitch height.
    // Let's just output the `accent_code` string which has [ ]
    return (
      <div className="text-xl font-mono mt-2 p-2 border-2 border-slate-700 inline-block bg-slate-900 text-green-400">
        {analysis.accent_code}
        <div className="text-xs text-slate-500 mt-1">Reading: {analysis.reading}</div>
        <div className="text-xs text-slate-500">Pattern: {JSON.stringify(analysis.accent_pattern)}</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-4">
      <Card className="w-full max-w-md border-4 border-slate-800 rounded-none bg-slate-900 shadow-[8px_8px_0px_0px_rgba(30,41,59,1)]">
        <CardHeader>
          <CardTitle className="text-3xl text-center text-primary tracking-widest uppercase text-yellow-500 drop-shadow-md">
            Accent Match
          </CardTitle>
          <CardDescription className="text-center font-mono text-slate-400">
            Find a word with the same accent as:
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          
          <div className="text-center p-6 bg-slate-950 border-2 border-dashed border-slate-700">
            {loading && !targetWord ? (
              <span className="animate-pulse">Loading...</span>
            ) : (
              <h2 className="text-5xl font-bold text-white mb-2">{targetWord}</h2>
            )}
            
            {(gameStatus === 'success' || gameStatus === 'failure') && targetAnalysis && (
               <div className="mt-4">
                 <div className="text-sm text-slate-400 mb-1">Target Accent:</div>
                 {renderAccent(targetAnalysis)}
               </div>
            )}
          </div>

          <div className="space-y-4">
            <Input 
              className="border-2 border-slate-700 bg-slate-950 text-white font-mono text-lg h-12 rounded-none focus:ring-0 focus:border-green-500"
              placeholder="Enter a Japanese word..."
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
              {loading ? 'Analyzing...' : 'CHECK ACCENT'}
            </Button>
          </div>

          {message && (
            <div className={`text-center font-bold p-2 ${gameStatus === 'success' ? 'text-green-500' : 'text-red-500'}`}>
              {message}
            </div>
          )}

          {inputAnalysis && (
            <div className="text-center mt-4 border-t-2 border-slate-800 pt-4">
               <div className="text-sm text-slate-400 mb-1">Your Input:</div>
               {renderAccent(inputAnalysis)}
            </div>
          )}
          
          {gameStatus !== 'idle' && (
            <Button 
              variant="outline" 
              className="w-full mt-4 border-2 rounded-none"
              onClick={startNewGame}
            >
              NEXT WORD
            </Button>
          )}

        </CardContent>
      </Card>
      
      <footer className="mt-8 text-slate-600 font-mono text-xs">
        Powered by tdmelodic & Shadcn 8-bit
      </footer>
    </div>
  )
}

export default App
